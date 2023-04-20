from django.db import models

# Create your models here.
class PingpongJob(models.Model):
    jobId = models.TextField(primary_key=True)
    width = models.IntegerField()
    height = models.IntegerField()
    iteration = models.IntegerField()
    data = models.TextField()

    def __str__(self):
        return self.jobId