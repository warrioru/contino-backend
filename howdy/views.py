from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Q
import json
from .forms import PatchForm
from git import Commit as CommitGit
from git import *
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
from graphviz import Digraph
import uuid
import xml.etree.ElementTree as ET
from xml.dom import minidom

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
        received_json_data = json.loads(request.body)
        if len(received_json_data) != 0:
            for data in received_json_data:
                commit = json.loads(data)

                #self.remoteRepo = pickle.loads(request.POST['repo'].encode()) # TODO:descomentar para usar con el cliente, este body contiene el objeto que necesitamos.
                #self.patch = request.FILES.get('patch', False)
                self.patch = commit['patch']
                self.url = commit['remote_url']
                if ".git" not in self.url:
                    self.url = self.url + ".git"
                self.parentCommitId = commit['parent_commit_id']
                self.commitId = commit['commit_id']
                #self.parentBranch = request.POST['parent_branch']
                self.parentBranch = 'master' #Asumo q viene el branch de master, esto hay q borrar
                self.currentBranch = commit['current_branch']
                self.userEmail = commit['email']
                self.username = commit['username']
                self.messageRaw = commit['message']
                self.time = str(commit['time'])
                self.offset = str(commit['offset'])

                self.createPatchFile()
                self.saveCommitInfo()
                message = self.applyPatchToLocalRepo()

        else:
            return JsonResponse({'message': 'Empty array received, try again'})

        return JsonResponse({'message': message})

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
            is_new_branch = False
            try:
                repo.git.checkout(user_branch)
                print("checkout " + user_branch)
            except GitCommandError:
                #no branch found with that name, create branch
                repo.git.checkout(self.parentCommitId)
                is_new_branch = True
                #repo.git.checkout(['-b', user_branch])
                print("new branch " + user_branch)

            print("using file: " + self.pathToPatch)
            try:
                repo.git.apply(["--ignore-space-change", "--ignore-whitespace", "--3way", self.pathToPatch])
                repo.git.add('*')
                author = Actor(self.username, self.userEmail)
                commitMessage = self.messageRaw

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
                if is_new_branch:
                    repo.git.checkout(['-b', user_branch])

                print('Commit ' + ew_commit.hexsha + ' added successfully')
            except GitCommandError as e:
                print(e)
                print('Error patching the branch' + str(e.stderr))
                repo.git.checkout("master")
                conflict = True
                #messageToReturn = 'Merge conflict found' + str(e.stderr)

            local_branches = repo.branches
            for branch in local_branches:
                if (branch.name == user_branch):
                    continue

                status = False
                repo.git.checkout(branch.name)
                repoTemp = Repo(self.projectDir)
                commitId2 = repoTemp.commit().hexsha
                mergeDiffPath = ''
                try:
                    repo.git.merge(user_branch)
                except GitCommandError as e:
                    print(e)
                    status = True
                    mergeDiffPath = repo.git.diff("--diff-filter", "U", "-U0")
                    #si hay error, hubo merge conflict
                    print('error')

                self.saveToMergeConflicts(commitId2, status, mergeDiffPath)

                #repo.git.clean('-fdx')
                repo.git.reset('--hard', commitId2)



            return conflict

        except Exception as e:
            repo.git.checkout("master")
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

class CommitCheckPageView(TemplateView):
    project = None
    projectDir = None
    projectName = None
    url = None
    commits = None
    pivotCommit = None

    def post(self, request, **kwargs):
        received_json_data = json.loads(request.body)
        self.commits = (received_json_data['commits'])
        if len(self.commits) != 0:
            self.url = received_json_data['url']
            if ".git" not in self.url:
                self.url = self.url + ".git"
            print(self.url)

            self.project = Project.objects.get(git_url = self.url)
            self.projectDir = self.project.project_dir
            self.projectName = self.project.project_name


            repo = Repo(self.projectDir)

            for commit in self.commits:
                try:
                    repo.git.branch('--contains', str(commit))
                    self.pivotCommit = str(commit)
                    break
                except GitCommandError:
                    print(str(commit) + ' not known')
                    continue


            if self.pivotCommit != None:
                print(self.pivotCommit + 'known commit')
                return JsonResponse({'pivot_commit':self.pivotCommit})
            else:
                return JsonResponse({'error': "could not find any commit"})

        else:
            return JsonResponse({'error':'no commits ids specified'})

class GetDiffPageView(TemplateView):
    def get(self, request, **kwargs):
        commitUser = request.GET.get('commitUser', None)
        commitTarget = request.GET.get('commitTarget', None)
        gitUrl = request.GET.get('gitUrl', None)
        project = Project.objects.get(git_url = gitUrl)
        projectDir = project.project_dir
        projectName = project.project_name
        repo = Repo(projectDir)
        try:
            diff = repo.git.diff(commitUser, commitTarget)
            return JsonResponse({'diff': diff}, status=200)
        except GitCommandError as e:
            return JsonResponse({'message': str(e.stderr)}, status=200)





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

    #with open(path, 'wb+') as destination:
    #    for chunk in f.chunks():
    #        destination.write(chunk)
    with open(path, 'w') as destination:
        destination.write(f)

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

class GetGraphPageView(TemplateView):

    def post(self, request, **kwargs):
        gitUrl = request.POST.get('gitUrl', '')
        if ".git" not in gitUrl:
            gitUrl = gitUrl + ".git"
        commitUser = request.POST.get('commitUser', '')
        url = graphTree(gitUrl, commitUser)
        return JsonResponse({'graphUrl': url})

def graphTree(gitUrl, commitUser):#
    uid = str(uuid.uuid4())
    filename = 'graphs/' + uid
    g = Digraph('G', filename = filename, strict = True)

    #get conflicts from db
    conflicts = MergeConflicts.objects.filter(
        Q(status = 1),
        Q(commitId1_id = commitUser) | Q(commitId2 = commitUser)
    )
    conflictsArray = []

    for conflict in conflicts:
        if conflict.commitId1_id == commitUser:
            conflictsArray.append(conflict.commitId2)
        else:
            conflictsArray.append(conflict.commitId1_id)


    #clientes
    clients = []
    project = Project.objects.get(git_url=gitUrl)
    projectDir = project.project_dir
    projectName = project.project_name
    repo = Repo(projectDir)
    branches = repo.branches
    for branch in branches:
        user_email = branch.name.split('/')[0]
        if "@" in user_email:
            if user_email not in clients:
                clients.append(user_email)
                #g.node(user_email, shape='square')
                for temp_branch in branches:
                    if user_email in temp_branch.name:
                        commits = list(repo.iter_commits(temp_branch.name))
                        commits.reverse()
                        #g.edge(user_email, temp_branch.name)
                        #g.edge(temp_branch.name, commits[0].hexsha)#
                        for i in range(len(commits)):
                            try:
                                if commits[i+1].hexsha in conflictsArray:
                                    g.node(commits[i+1].hexsha, style='filled', color='red')
                                    g.edge(commits[i].hexsha, commits[i+1].hexsha)
                                else:
                                    if commits[i+1].hexsha == commitUser:
                                        g.node(commits[i+1].hexsha, style='filled', color='cyan2')
                                        g.edge(commits[i].hexsha, commits[i+1].hexsha)


                                    else:
                                        g.edge(commits[i].hexsha, commits[i+1].hexsha)

                            except:
                                g.edge(commits[i].hexsha, temp_branch.name)
                                g.edge(temp_branch.name, user_email)
                                print('end of edge')


    g.render(view= False, cleanup = True, format = "svg")

    svgF = filename + ".svg"
    doc = minidom.parse(svgF)  # parseString also exists
    for path in doc.getElementsByTagName('polygon'):
        if path.attributes["stroke"].value == "transparent":
            path.attributes["stroke"].value = "#000000"

    with open(svgF,'w') as f:
        f.write(doc.toxml())

    doc.unlink()

    urlSVG = "http://localhost:8000/" + filename + ".svg"
    urlHTML = "http://localhost:8000/" + filename + ".html"

    f = open(filename + '.html','w+')

    message = """<html>
<head>
    <meta charset="utf-8">
    <title>Tree Overview</title>
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
    <link rel="stylesheet" href="http://ajax.googleapis.com/ajax/libs/jqueryui/1.8.10/themes/base/jquery-ui.css">
    <link rel="stylesheet" href="style.css"> 

</head>
<body>
<h1>Project tree overview</h1>
<h3 id='gitUrl'>""" + gitUrl + """</h3>
<object type="image/svg+xml" data='""" + urlSVG + """'></object>

<p>Commit user: </p><input type='text' id='commitUser' value='""" + commitUser + """'><br>
<p>Target commit: </p><input type='text' id='commitTarget'><br>
<input type='submit' value='Submit' id='submitButton'>

<div id='diffContainer'></div>


<script src="script.js" type="application/javascript"></script>
</body>
</html>"""


    f.write(message)
    f.close()

    return urlHTML
