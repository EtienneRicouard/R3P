from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
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

@api_view(['GET'])
def ApiOverview(request):
  api_urls = {
    'Trigger a new render': '/pingpong/createjob',
    'Update render': '/pingpong/update/pk',
    'Render': '/pingpong/render/pk',
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
  job = {
    'width': request.data['width'],
    'height': request.data['height'],
    'jobId': str(jobId),
    'iteration': 0,
    'data': '[]',
    'positions': 0,
    'colors': 0,
  }
  serializer = PingpongJobSerializer(data=job)
  if serializer.is_valid():
    routing_key = 'pingpong'
    host = os.getenv('RABBITMQ_HOST', 'localhost')
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    channel = connection.channel()
    channel.exchange_declare(exchange='pingpongtopic', exchange_type='topic')
    channel.basic_publish(
      exchange='pingpongtopic', routing_key=routing_key, body=json.dumps(job, separators=(',', ':')))
    connection.close()
    serializer.save()
    return Response({"status": "success", "message": serializer.data}, status=status.HTTP_201_CREATED)
  else:
    return Response({"status": "fail", "message": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def status_job(request, pk):
  # Retrieve the item
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
  coords = json.loads(serializer.data['data'])
  imarray = numpy.zeros((serializer.data['height'], serializer.data['width'], 3))
  for coord in coords:
    x = coord[0] % serializer.data['width']
    y = math.floor(coord[0]/serializer.data['width'])
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