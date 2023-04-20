from rest_framework import serializers

from .models import PingpongJob

class PingpongJobSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PingpongJob
        fields = ('jobId', 'width', 'height', 'iteration', 'data')