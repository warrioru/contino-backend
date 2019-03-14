from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import PatchForm
from git import *
from pydriller import RepositoryMining
from api.models import Project
import os

# Create your views here.
class HomePageView(TemplateView):
    def get(self, request, **kwargs):
        repo = Repo('/home/nicolas/Nicolas/UZH/HS19/master project/git repos/git-history')
        #printRepo(repo)
        return render(request, 'index.html', context=None)

    def post(self, request, **kwargs):
        patch = request.FILES['patch']
        name = request.POST['name']
        repo = Project.objects.get(name = name)
        branches = repo.branches
        message = applyPatchToLocalRepo(name, patch)
        #repo = RepositoryMining('/home/nicolas/Nicolas/UZH/HS19/master project/git repos/git-history')
        #branches = printRepo(repo)

        return render(request, 'index.html', {'name': name, 'message': message,
                                              'branches': branches})

# Add this view
class AboutPageView(TemplateView):
    template_name = "about.html"


def printRepo(repo):
    for commit in repo.traverse_commits():
        print('Hash {}, author {}'.format(commit.hash, commit.author.name))

    return repo.branches

def applyPatchToLocalRepo(name, patch):
    #based on the name, get the local repo
    messageToReturn = ''
    #patch1 = patch.replace('\n','').replace('-', ' ')
    project = Project.objects.get(name = name)
    master_branch = project.master_branch
    project_dir = project.project_dir
    print(master_branch)
    repo = Repo(project_dir)
    repo.git.checkout(str(master_branch))
    repo.git.pull()
    #create a file with the patch
    handle_uploaded_file(patch)
    my_path = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(my_path, "../temp.patch")

    try:
        repo.git.apply(['-3', path])

        print('No merge conflicts with ' + master_branch)
        messageToReturn = 'No merge conflicts with ' + master_branch
    except GitCommandError as e:
        #print(e)
        print('Merge conflict found' + str(e.stderr))
        messageToReturn = 'Merge conflict found' + str(e.stderr)

    repo.git.clean('-fdx')
    repo.git.reset('--hard')
    os.remove(path)
    return messageToReturn

def handle_uploaded_file(f):
    with open('temp.patch', 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)