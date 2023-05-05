from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/pingpong/joblist/', consumers.JobListConsumer.as_asgi())
]