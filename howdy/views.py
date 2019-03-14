from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from .forms import PatchForm
from git import *
from pydriller import RepositoryMining
from api.models import Project

# Create your views here.
class HomePageView(TemplateView):
    def get(self, request, **kwargs):
        repo = Repo('/home/nicolas/Nicolas/UZH/HS19/master project/git repos/git-history')
        #printRepo(repo)
        return render(request, 'index.html', context=None)

    def post(self, request, **kwargs):
        patch = request.FILES['patch'].read()
        print(patch)
        name = request.POST['name']
        repo = Project.objects.get(name = name)
        print(repo.branches)
        branches = repo.branches
        #repo = RepositoryMining('/home/nicolas/Nicolas/UZH/HS19/master project/git repos/git-history')
        #branches = printRepo(repo)

        return render(request, 'index.html', {'name': name, 'patch': patch,
                                              'branches': branches})

# Add this view
class AboutPageView(TemplateView):
    template_name = "about.html"


def printRepo(repo):
    for commit in repo.traverse_commits():
        print('Hash {}, author {}'.format(commit.hash, commit.author.name))

    return repo.branches