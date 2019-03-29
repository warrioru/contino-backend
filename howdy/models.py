from django.db import models

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
