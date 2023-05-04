import json
import struct
import threading
import time
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models.signals import post_save
from django.dispatch import receiver
from multiprocessing import shared_memory

from .models import PingpongJob

ROOM_GROUP_NAME = 'joblist'
CREATE_CALLBACK_NAME = 'joblist_create_callback'
CREATE_MESSAGE_TYPE = 'joblist_create'
UPDATE_CALLBACK_NAME = 'joblist_update_callback'
UPDATE_MESSAGE_TYPE = 'joblist_update'

def serializeCreateJob(job: PingpongJob):
    return json.dumps({
        'jobId': job.jobId,
        'width': job.width,
        'height': job.height,
        'iteration': job.iteration,
        'created': job.created.isoformat(),
    })

def serializeUpdateJob(job: PingpongJob, iteration):
    return json.dumps({
        'jobId': job.jobId,
        'iteration': iteration,
    })

class JobListConsumer(WebsocketConsumer):
    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
            ROOM_GROUP_NAME,
            self.channel_name
        )
        self.accept()
        # Return the last 10 jobs at connection opening
        jobs = PingpongJob.objects.order_by('-created')[:10]
        for job in reversed(list(jobs)):
            self.send(text_data=json.dumps({
                'type': CREATE_MESSAGE_TYPE,
                'message': serializeCreateJob(job)
            }))

    def joblist_create_callback(self, event):
        message = event['message']

        self.send(text_data=json.dumps({
            'type': CREATE_MESSAGE_TYPE,
            'message': message
        }))

    def joblist_update_callback(self, event):
        message = event['message']

        self.send(text_data=json.dumps({
            'type': UPDATE_MESSAGE_TYPE,
            'message': message
        }))

def monitoring_thread(jobId):
    # Retrieve the item
    monitor = True
    while monitor:
        # Update every 100 ms
        time.sleep(0.1)
        item = PingpongJob.objects.get(pk=jobId)
        iteration = None
        # Look into the SHM if still running
        try:
            shmStatus = shared_memory.SharedMemory(create=False, name=f"{item.jobId}-status", size=6)
            buf = shmStatus.buf
            # Lock the SHM to avoid being cleared
            buf[5] = 1
            iteration = struct.unpack('I', buf[0:4])[0]
            buf[5] = 0
            # Retrieve the current channel and broadcast to the group
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                ROOM_GROUP_NAME,
                {
                    'type': UPDATE_CALLBACK_NAME,
                    'message': serializeUpdateJob(item, iteration)
                })
        except:
            item = PingpongJob.objects.get(pk=jobId)
            monitor = False

    print('Exiting monitoring thread for', jobId)

# Subscribe to new job creation
@receiver(post_save, sender=PingpongJob)
def send_ws_update(sender, instance, created, **kwargs):
    # Retrieve the current channel and broadcast to the group
    channel_layer = get_channel_layer()
    if created:
        # Broadcast the creation
        async_to_sync(channel_layer.group_send)(
            ROOM_GROUP_NAME,
            {
                'type': CREATE_CALLBACK_NAME,
                'message': serializeCreateJob(instance)
            })
        # Run the monitoring thread
        thread = threading.Thread(target=monitoring_thread, args=(instance.jobId,))
        thread.start()
    else:
        # Broadcast the update
        async_to_sync(channel_layer.group_send)(
            ROOM_GROUP_NAME,
            {
                'type': UPDATE_CALLBACK_NAME,
                'message': serializeUpdateJob(instance, instance.iteration)
            })
