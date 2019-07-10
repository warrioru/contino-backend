from django.shortcuts import render
from rest_framework import generics
from .serializers import BucketlistSerializer, ProjectSerializer
from .models import Bucketlist, Project
from pydriller import *
from git import *
import re
import os


class CreateView(generics.ListCreateAPIView):
    """This class defines the create behavior of our rest api."""
    queryset = Bucketlist.objects.all()
    serializer_class = BucketlistSerializer

    def perform_create(self, serializer):
        """Save the post data when creating a new bucketlist."""
        serializer.save()

class DetailsView(generics.RetrieveUpdateDestroyAPIView):
    """This class handles the http GET, PUT and DELETE requests."""

    queryset = Bucketlist.objects.all()
    serializer_class = BucketlistSerializer

class CreateViewProject(generics.ListCreateAPIView):
    """This class defines the create behavior of our rest api."""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def perform_create(self, serializer):
        """Save the post data when creating a new project."""
        #print(serializer['git_url'].value)
        #serializer.validated_data['branches'] = branches
        serializer.save()
        branches = create_repo(serializer)



class DetailsViewProject(generics.RetrieveUpdateDestroyAPIView):
    """This class handles the http GET, PUT and DELETE requests."""

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

def create_repo(serializer):
    url = serializer['git_url'].value
    id = serializer['id'].value
    #print(temp_repo.remotes.origin.refs[2])



    try:
        result = re.search('github.com/(.*)/',url)
        owner = result.group(1)
        result = re.search(owner + '/(.*).git',url)
        name = result.group(1)
        if not os.path.exists('./gitProjects'):
            os.makedirs('./gitProjects')
        projectDir = './gitProjects/' + name + '/'
        originDir = './gitOrigins/' + name + '/'
        temp_repo = Repo.clone_from(url, projectDir)
        temp_repo_origin = Repo.clone_from(url, originDir)

        branches = []
        for branch in temp_repo.remotes.origin.refs:
            branches.append(branch)
        myString = ",".join([str(i) for i in branches])
        Project.objects.filter(git_url = url).update(owner=owner, project_name=name, branches=myString, project_dir=projectDir)
        return myString

        #return myString
    except Exception as e:
        Project.objects.filter(git_url = url).delete()
        print(e)
