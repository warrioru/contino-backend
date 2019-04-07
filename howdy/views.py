from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import PatchForm
from git import Commit as CommitGit
from git import *
from github import Github
from pydriller import RepositoryMining
from api.models import Project
from howdy.models import Commit, MergeConflicts
import pickle
import os
import errno
import urllib.request
import traceback
from time import (time, altzone)
import datetime
from io import BytesIO
from gitdb import *

# Create your views here.
class HomePageView(TemplateView):
    patch = None
    url = None
    parentCommitId = None
    commitId = None
    parentBranch = None
    currentBranch = None
    userEmail = None
    username = None
    pathToPatch = None
    project = None
    projectDir = None
    projectName = None
    remoteRepo = None
    messageRaw = None
    time = None
    offset = None


    def get(self, request, **kwargs):
        #printRepo(repo)
        return render(request, 'index.html', context=None)

    def post(self, request, **kwargs):
        #self.remoteRepo = pickle.loads(request.POST['repo'].encode()) # TODO:descomentar para usar con el cliente, este body contiene el objeto que necesitamos.
        self.patch = request.FILES.get('patch', False)
        #self.patch = request.POST['patch']
        self.url = request.POST['remote_url']
        self.parentCommitId = request.POST['parent_commit_id']
        self.commitId = request.POST['commit_id']
        self.parentBranch = request.POST['parent_branch']
        self.currentBranch = request.POST['current_branch']
        self.userEmail = request.POST['email']
        self.username = request.POST['username']
        self.messageRaw = request.POST['message']
        self.time = str(request.POST['time'])
        self.offset = str(request.POST['offset'])

        if self.patch:
            self.createPatchFile()
            self.saveCommitInfo()
            message = self.applyPatchToLocalRepo() # la funcion deberia estar en esta clase, no deberia tener que pasarle el objeto
            return JsonResponse({'message': message})
        else:
            return JsonResponse({'message': 'Missing patch file'})

    def createPatchFile(self):
        #create a file with the patch TODO:esto debe ser otra funcion dentro de la clase de arriba en caso de que falle.
        self.project = Project.objects.get(git_url = self.url)
        self.projectDir = self.project.project_dir
        self.projectName = self.project.project_name

        handle_uploaded_file(self.patch, self.projectName, self.commitId)
        my_path = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(my_path, "../patches/" + self.projectName + "/" + str(self.commitId) + ".patch")
        self.pathToPatch = path

    def saveCommitInfo(self):
        commit = Commit(commitId = self.commitId, branchName = self.currentBranch, userEmail = self.userEmail, pathToPatch = self.pathToPatch)
        commit.save()


    def applyPatchToLocalRepo(self):
        #based on the name, get the local repo
        conflict = False
        #patch1 = patch.replace('\n','').replace('-', ' ')

        try:
            repo = Repo(self.projectDir)
            user_branch = self.userEmail + "/" + self.currentBranch
            try:
                repo.git.checkout(user_branch)
                print("checkout " + user_branch)
            except GitCommandError:
                #no branch found with that name, create branch
                repo.git.checkout(self.parentBranch)
                repo.git.checkout(['-b', user_branch])
                print("new branch " + user_branch)

            print("using file: " + self.pathToPatch)
            try:
                repo.git.apply(["--ignore-space-change", "--ignore-whitespace", self.pathToPatch])
                repo.git.add('*')
                author = Actor(self.username, self.userEmail)
                skip = b'\x0a'.decode("utf-8")
                commitMessage = self.messageRaw + skip

                tree = repo.index.write_tree()
                parents = [ repo.head.commit ]

                # Committer and Author
                cr = repo.config_reader()

                # Custom Date
                time = self.time
                offset = self.offset
                author_time, author_offset = time, offset
                committer_time, committer_offset = time, offset

                ew_commit = CommitGit.create_from_tree(repo, tree, commitMessage, parents, True, author,
                                                       author, author_time, committer_time, author_offset)

                print('No merge conflicts with ' + self.parentBranch)
            except GitCommandError as e:
                #print(e)
                print('Merge conflict found' + str(e.stderr))
                conflict = True
                #messageToReturn = 'Merge conflict found' + str(e.stderr)

            local_branches = repo.branches
            for branch in local_branches:
                status = False
                repo.git.checkout(branch.name)
                repoTemp = Repo(self.projectDir)
                commitId2 = repoTemp.commit().hexsha
                mergeDiffPath = ''
                try:
                    repo.git.merge(user_branch)
                except GitCommandError:
                    status = True
                    mergeDiffPath = ''
                    #si hay error, hubo merge conflict
                    print('error')

                self.saveToMergeConflicts(commitId2, status, mergeDiffPath)

                repo.git.clean('-fdx')
                repo.git.reset('--hard')



            return conflict

        except Exception as e:
            print(e)

    def saveToMergeConflicts(self, commitId2, status, mergeDiffPath):
        mergeConflict = MergeConflicts(commitId1_id = self.commitId, commitId2 = commitId2, status = status, mergeDiffPath = mergeDiffPath)
        mergeConflict.save()


# Add this view
class AboutPageView(TemplateView):
    template_name = "about.html"


def printRepo(repo):
    for commit in repo.traverse_commits():
        print('Hash {}, author {}'.format(commit.hash, commit.author.name))

    return repo.branches



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
    #with open(path, 'w') as destination:
    #    destination.write(f)

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