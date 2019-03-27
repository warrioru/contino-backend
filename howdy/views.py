from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import PatchForm
from git import *
from github import Github
from pydriller import RepositoryMining
from api.models import Project
import pickle
import os
import errno
import urllib.request
import traceback

# Create your views here.
class HomePageView(TemplateView):
    patch = None
    url = None
    parentCommitId = None
    commitId = None
    parentBranch = None
    currentBranch = None
    userEmail = None

    def get(self, request, **kwargs):
        #printRepo(repo)
        return render(request, 'index.html', context=None)

    def post(self, request, **kwargs):
        #repo1 = pickle.loads(request.body) TODO:descomentar para usar con el cliente, este body contiene el objeto que necesitamos.
        self.patch = request.POST['patch']
        self.url = request.POST['remote_url']
        self.parentCommitId = request.POST['parent_commit_id']
        self.commitId = request.POST['commit_id']
        self.parentBranch = request.POST['parent_branch']
        self.currentBranch = request.POST['current_branch']
        self.userEmail = request.POST['username']

        if self.patch:
            message = applyPatchToLocalRepo(self) # la funcion deberia estar en esta clase, no deberia tener que pasarle el objeto
            return JsonResponse({'message': message})
        else:
            return JsonResponse({'message': 'Missing patch file'})

# Add this view
class AboutPageView(TemplateView):
    template_name = "about.html"


def printRepo(repo):
    for commit in repo.traverse_commits():
        print('Hash {}, author {}'.format(commit.hash, commit.author.name))

    return repo.branches

def applyPatchToLocalRepo(commit):
    #based on the name, get the local repo
    conflict = False
    #patch1 = patch.replace('\n','').replace('-', ' ')
    try:
        project = Project.objects.get(git_url = commit.url)
        #master_branch = project.master_branch
        project_dir = project.project_dir
        project_name = project.project_name #esto ya no se usa? de la linea 61 a la 64

        repo = Repo(project_dir) #TODO:use a new dir if project doesnt exist and init repo or clone avoid github
        try:
            repo.git.checkout(commit.userEmail + "/" + commit.currentBranch)
            print("checkout " + commit.userEmail + "/" + commit.currentBranch)
        except GitCommandError:
            #no branch found with that name, create branch
            repo.git.checkout(commit.parentBranch)
            repo.git.pull()
            repo.git.checkout(['-b', commit.userEmail + "/" + commit.currentBranch])
            print("new branch " + commit.currentBranch)
        #create a file with the patch TODO:esto debe ser otra funcion dentro de la clase de arriba en caso de que falle.
        handle_uploaded_file(commit.patch, project_name, commit.commitId)
        my_path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(my_path, "../patches/" + project_name + "/" + str(commit.commitId) + ".patch")

        print("using file: " + path)
        try:
            repo.git.apply(commit.patch)
            #repo.git.apply(['-3', path])
            print('No merge conflicts with ' + commit.parentBranch)
        except GitCommandError as e:
            #print(e)
            print('Merge conflict found' + str(e.stderr))
            conflict = True
            #messageToReturn = 'Merge conflict found' + str(e.stderr)

        return conflict

    except Exception as e:
        print(e)


def handle_uploaded_file(f, project_name, commitId):
    path = "patches/" + project_name + "/" + str(commitId) + ".patch"
    if not os.path.exists(os.path.dirname(path)):
        try:
            original_umask = os.umask(0)
            os.makedirs(os.path.dirname(path))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
        finally:
            os.umask(original_umask)

    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

def clean_git_repo(url):
    try:
        project = Project.objects.get(git_url = url)
        project_dir = project.project_dir
        repo = Repo(project_dir)
        repo.git.clean('-fdx')
        repo.git.reset('--hard')
        print('Cleaning repo')

    except GitCommandError as e:
        print(e)

def applyPatchToPullRequests(url, patch):
    messageToReturn = ''

    try:
        project = Project.objects.get(git_url = url)
        owner = project.owner
        project_name = project.project_name
        master_branch = project.master_branch

        #check for merge conflicts with master branch
        conflict = applyPatchToLocalRepo(project.git_url, patch, 0)
        if conflict:
            clean_git_repo(url)
            return "Merge conflict with " + master_branch
        else:
            messageToReturn += "No conflict with " + master_branch + " "
        clean_git_repo(url)

        g = Github()
        repo = g.get_repo(str(owner) + "/" + str(project_name))
        pulls = repo.get_pulls(state='open', sort='created', base=master_branch)
        prs_conflict_master = []
        counter = 1
        #check for merge conflicts with each pull request with status open
        for pr in pulls:
            #if pr are found, download the patch, apply, log
            #apply PR
            print("checking against PR #: " + str(pr.number))
            urllib.request.urlretrieve(pr.patch_url, "PR" + str(counter) + ".patch")
            conflict = applyPatchToLocalRepo(project.git_url, '', counter)
            if conflict:
                clean_git_repo(url)
                prs_conflict_master.append(counter)
                messageToReturn += "PR #: " + str(pr.number) + "in conflict with " + master_branch
            else:
                conflict = applyPatchToLocalRepo(project.git_url, patch, 0)
                if conflict:
                    messageToReturn += "Conflict with PR #: " + str(pr.number) + " "
                else:
                    messageToReturn += "No conflict with PR #: " + str(pr.number) + " "

                clean_git_repo(url)
                counter = counter + 1

        #check for all the PRs combined
        counter = 1
        skip = 0
        for pr in pulls:
            #apply PR but don't clean
            my_path = os.path.abspath(os.path.dirname(__file__))
            path = os.path.join(my_path, "../PR" + str(counter) + ".patch")

            #skip the PR if it has conflict with master
            jump_out = 0
            for number in prs_conflict_master:
                if (counter == number):
                    jump_out = 1
                    break
            if jump_out:
                print("Skipped PR #: " + str(counter))
                break

            conflict = applyPatchToLocalRepo(project.git_url, '', counter)
            if conflict:
                clean_git_repo(url)
                os.remove(path)
                skip = 1
                messageToReturn += "Couldn't merge all PR because of conflict PR #: " + str(pr.number)
                break
            else:
                os.remove(path)
                counter = counter + 1

        #run this code only if there are pull requests found
        if (counter > 1) and (not skip):
            conflict = applyPatchToLocalRepo(project.git_url, patch, 0)
            if conflict:
                messageToReturn += "Conflict with all PRs combined "
            else:
                messageToReturn += "No conflict with all PRs combined "

        clean_git_repo(url)

    except Exception as e:
        #print(e)
        print(traceback.format_exc())

    return messageToReturn