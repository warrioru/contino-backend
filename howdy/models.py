from django.db import models

class Project(models.Model):
    project_name = models.CharField(max_length=255)
    owner = models.CharField(max_length=255, default='')
    git_url = models.CharField(max_length=255, unique=True)
    project_dir = models.CharField(max_length=255)
    master_branch = models.CharField(max_length=255)
    branches = models.CharField(max_length=255, default='')

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{}".format(self.name)

class Commit(models.Model):
    commitId = models.CharField(max_length=255, unique=True, primary_key=True)
    branchName = models.CharField(max_length=255, default='')
    userEmail = models.CharField(max_length=255, default='')
    pathToPatch = models.CharField(max_length=255, default='')

class MergeConflicts(models.Model):
    commitId1 = models.ForeignKey(Commit, on_delete=models.CASCADE)
    commitId2 = models.CharField(max_length=255)
    status = models.BooleanField(default=False)
    mergeDiffPath = models.CharField(max_length=255, default='')
