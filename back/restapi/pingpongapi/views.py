import struct
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, HttpResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from .serializers import PingpongJobSerializer
from .models import PingpongJob
import pika
import uuid
import json
import math
from PIL import Image
import numpy
import os
from multiprocessing import resource_tracker, shared_memory

def remove_shm_from_resource_tracker():
    """Monkey-patch multiprocessing.resource_tracker so SharedMemory won't be tracked

    More details at: https://bugs.python.org/issue38119
    """

    def fix_register(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.register(self, name, rtype)
    resource_tracker.register = fix_register

    def fix_unregister(name, rtype):
        if rtype == "shared_memory":
            return
        return resource_tracker._resource_tracker.unregister(self, name, rtype)
    resource_tracker.unregister = fix_unregister

    if "shared_memory" in resource_tracker._CLEANUP_FUNCS:
        del resource_tracker._CLEANUP_FUNCS["shared_memory"]

@api_view(['GET'])
def ApiOverview(request):
  api_urls = {
    'Trigger a new render': '/pingpong/create/',
    'Update render': '/pingpong/update/pk/',
    'Render': '/pingpong/render/pk/',
  }

  return Response(api_urls)

@swagger_auto_schema(method='post', request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'width': openapi.Schema(type=openapi.TYPE_INTEGER, description='width'),
        'height': openapi.Schema(type=openapi.TYPE_INTEGER, description='height'),
    }
))
@api_view(['POST'])
def create_job(request):
  if not 'width' in request.data or not 'height' in request.data:
    return Response({"status": "fail", "message": "Missing width/height in request"}, status=status.HTTP_400_BAD_REQUEST)

  # Generate a random uid
  jobId = uuid.uuid4()
  height = int(request.data['height'])
  width = int(request.data['width'])

  # Have to patch the resource tracker to make shm work properly
  remove_shm_from_resource_tracker()
  bufferSize = height*width*4 #uint32
  shmPos = shared_memory.SharedMemory(create=True, name=f"{str(jobId)}-pos", size=bufferSize)
  posBuf = shmPos.buf
  for n in range(bufferSize):
    posBuf[n] = 0
  shmPos.close()

  shmCol = shared_memory.SharedMemory(create=True, name=f"{str(jobId)}-col", size=bufferSize)
  colBuf = shmCol.buf
  for n in range(bufferSize):
    colBuf[n] = 0
  shmCol.close()

  bitmaskSize = height*width
  shmPosMask = shared_memory.SharedMemory(create=True, name=f"{str(jobId)}-posMask", size=bitmaskSize)
  posMaskBuf = shmPosMask.buf
  for n in range(bitmaskSize):
    posMaskBuf[n] = 1
  shmPosMask.close()

  colmaskSize = 256*256*256
  shmColMask = shared_memory.SharedMemory(create=True, name=f"{str(jobId)}-colMask", size=colmaskSize)
  colMaskBuf = shmColMask.buf
  for n in range(colmaskSize):
    colMaskBuf[n] = 1
  shmColMask.close()

  # First 4 is the current iteration, 5th is the current status (ping/pong/finished), 6th is a lock for the update
  statusBufSize = 6
  shmStatus = shared_memory.SharedMemory(create=True, name=f"{str(jobId)}-status", size=statusBufSize)
  statusBuf = shmStatus.buf
  for n in range(statusBufSize):
    statusBuf[n] = 0
  shmStatus.close()

  job = {
    'jobId': str(jobId),
    'width': request.data['width'],
    'height': request.data['height'],
    'iteration': 0,
    'data': '[]',
  }
  serializer = PingpongJobSerializer(data=job)
  if serializer.is_valid():
    routing_key = 'pingpong'
    host = os.getenv('RABBITMQ_HOST', 'localhost')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.exchange_declare(exchange='pingpongtopic', exchange_type='topic')
    channel.basic_publish(
      exchange='pingpongtopic', routing_key=routing_key, body=json.dumps(job))
    connection.close()
    serializer.save()
    return Response({"status": "success", "message": serializer.data}, status=status.HTTP_201_CREATED)
  else:
    return Response({"status": "fail", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def status_job(request, pk):
  # Retrieve the item
  item = PingpongJob.objects.get(pk=pk)
  # Look into the SHM if still running
  try:
    shmStatus = shared_memory.SharedMemory(create=False, name=f"{item.jobId}-status", size=6)
    buf = shmStatus.buf
    # Lock the SHM to avoid being cleared
    buf[5] = 1
    iteration = struct.unpack('I', buf[0:4])[0]
    data = {}
    data['iteration'] = iteration
    serializer = PingpongJobSerializer(instance=item, data=data, partial=True)
    if serializer.is_valid():
      serializer.save()
      buf[5] = 0
      return Response(serializer.data, status=status.HTTP_200_OK)
  except:
    item = PingpongJob.objects.get(pk=pk)
    serializer = PingpongJobSerializer(instance=item)
    return Response(serializer.data, status=status.HTTP_200_OK)

@swagger_auto_schema(method='post', request_body=openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'iteration': openapi.Schema(type=openapi.TYPE_INTEGER, description='iteration'),
        'data': openapi.Schema(type=openapi.TYPE_INTEGER, description='data'),
    }
))
@api_view(['POST'])
def update_job(request, pk):
  if not 'iteration' in request.data and not 'data' in request.data:
    return Response({"status": "fail", "message": "You need to provided either iteration or data (or both)"}, status=status.HTTP_400_BAD_REQUEST)

  # Retrieve the item
  item = PingpongJob.objects.get(pk=pk)
  serializer = PingpongJobSerializer(instance=item, data=request.data, partial=True)
  if serializer.is_valid():
    serializer.save()
    return Response({"status": "success", "message": serializer.data}, status=status.HTTP_200_OK)
  else:
    return Response({"status": "fail", "message": f"Unable to update job {pk}"}, status=status.HTTP_404_NOT_FOUND)

@swagger_auto_schema(method='get', manual_parameters=[openapi.Parameter('iteration', openapi.IN_QUERY, required=False, description="optional iteration number", type=openapi.TYPE_INTEGER)])
@api_view(['GET'])
def render_job(request, pk):
  # Retrieve the item
  item = PingpongJob.objects.get(pk=pk)
  serializer = PingpongJobSerializer(instance=item)
  width = serializer.data['width']
  height = serializer.data['height']
  # Look into the SHM if still running
  try:
    shmStatus = shared_memory.SharedMemory(create=False, name=f"{item.jobId}-status", size=6)
    buf = shmStatus.buf
    # Lock the SHM to avoid being cleared
    buf[5] = 1
    iteration = struct.unpack('I', buf[0:4])[0]
    shmPos = shared_memory.SharedMemory(create=False, name=f"{item.jobId}-pos")
    posBuf = shmPos.buf
    shmCol = shared_memory.SharedMemory(create=False, name=f"{item.jobId}-col")
    colBuf = shmCol.buf
    positionList = struct.unpack(f'{width*height}I', posBuf)
    colorList = struct.unpack(f'{width*height}I', colBuf)
    coords = []
    for i in range(iteration):
      coords.append([positionList[i], colorList[i]])
    shmPos.close()
    shmCol.close()
    # Unlock the SHM
    buf[5] = 0
  # Retrieve the data from the DB if the SHM does not exist anymore
  except:
    item = PingpongJob.objects.get(pk=pk)
    serializer = PingpongJobSerializer(instance=item)
    coords = json.loads(serializer.data['data'])

  # Allocate the final image and fill it
  imarray = numpy.zeros((width, height, 3))
  for coord in coords:
    x = coord[0] % width
    y = math.floor(coord[0]/width)
    Blue =  coord[1] & 255
    Green = (coord[1] >> 8) & 255
    Red =   (coord[1] >> 16) & 255
    imarray[x, y, 0] = Red
    imarray[x, y, 1] = Green
    imarray[x, y, 2] = Blue
  im = Image.fromarray(imarray.astype('uint8')).convert('RGBA')
  response = HttpResponse(content_type='application/octet-stream')
  response.write(im.tobytes())
  return response

@api_view(['GET'])
def get_nebula(request, res, index):
  filename = f'nebula/nebula_{res}_{index}.jpg'
  try:
    with open(filename, "rb") as img:
      return HttpResponse(img.read(), content_type="image/jpeg")
  except:
    return Response({"status": "Unable to find image"}, status=status.HTTP_404_NOT_FOUND)
