from django.db import models

# Create your models here.
class PingpongJob(models.Model):
    jobId = models.TextField(primary_key=True)
    width = models.IntegerField()
    height = models.IntegerField()
    iteration = models.IntegerField()
    # Automatically create the start time at model creation
    created = models.DateTimeField(auto_now_add=True)
    # Last update will modify the end_time
    modified = models.DateTimeField(auto_now=True)
    data = models.TextField()

    def __str__(self):
        return f'{self.jobId}/{self.width}/{self.height}/{self.iteration}/{self.created}'