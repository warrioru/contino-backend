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
import urllib.request
import traceback

# Create your views here.
class HomePageView(TemplateView):
    def get(self, request, **kwargs):
        repo = Repo('/home/nicolas/Nicolas/UZH/HS19/master project/git repos/git-history')
        #printRepo(repo)
        return render(request, 'index.html', context=None)

    def post(self, request, **kwargs):
        #repo1 = pickle.loads(request.body) TODO:descomentar para usar con el cliente, este body contiene el objeto que necesitamos.
        patch = request.FILES.get('patch', False)
        url = request.POST['git_url']
        if patch:
            message = applyPatchToPullRequests(url, patch)
            return JsonResponse({'message': message})
        else:
            return JsonResponse({'message': 'Missing patch file'})
        #message = applyPatchToLocalRepo(url, patch, 0)

        #repo = RepositoryMining('/home/nicolas/Nicolas/UZH/HS19/master project/git repos/git-history')
        #branches = printRepo(repo)

        #return render(request, 'index.html', {'name': name, 'message': message,
        #                                      'branches': branches})

# Add this view
class AboutPageView(TemplateView):
    template_name = "about.html"


def printRepo(repo):
    for commit in repo.traverse_commits():
        print('Hash {}, author {}'.format(commit.hash, commit.author.name))

    return repo.branches

def applyPatchToLocalRepo(url, patch, pullRequest):
    #based on the name, get the local repo
    conflict = 0
    #patch1 = patch.replace('\n','').replace('-', ' ')
    try:
        project = Project.objects.get(git_url = url)
        master_branch = project.master_branch
        project_dir = project.project_dir
        print(master_branch)
        repo = Repo(project_dir)
        repo.git.checkout(str(master_branch))
        repo.git.pull()
        #create a file with the patch
        if not pullRequest:
            handle_uploaded_file(patch)
            my_path = os.path.abspath(os.path.dirname(__file__))
            path = os.path.join(my_path, "../temp.patch")
        else:
            my_path = os.path.abspath(os.path.dirname(__file__))
            path = os.path.join(my_path, "../PR" + str(pullRequest) + ".patch")

        print("using file: " + path)
        try:
            repo.git.apply(['-3', path])

            print('No merge conflicts with ' + master_branch)
        except GitCommandError as e:
            #print(e)
            print('Merge conflict found' + str(e.stderr))
            conflict = 1
            #messageToReturn = 'Merge conflict found' + str(e.stderr)

        if not pullRequest:
            os.remove(path)

        return conflict

    except Exception as e:
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


def handle_uploaded_file(f):
    with open('temp.patch', 'wb+') as destination:
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