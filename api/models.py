from django.db import models

# Create your models here.
class Bucketlist(models.Model):
    """This class represents the bucketlist model."""
    name = models.CharField(max_length=255, blank=False, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{}".format(self.name)

class Project(models.Model):
    name = models.CharField(max_length=255, unique=True)
    git_url = models.CharField(max_length=255, unique=True)
    project_dir = models.CharField(max_length=255)
    master_branch = models.CharField(max_length=255)
    branches = models.CharField(max_length=255, default='')

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{}".format(self.name)