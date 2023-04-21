#!/usr/bin/env python
import pika
import json
from random import seed
from random import randint
import requests
import os

seed(1)
host = os.getenv('RABBITMQ_HOST', 'localhost')
pongapihost = os.getenv('PONGAPI_HOST', 'localhost')

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=host))
channel = connection.channel()

channel.exchange_declare(exchange='pingpongtopic', exchange_type='topic')

channelName = 'pingpongagents'
result = channel.queue_declare(channelName)
queue_name = result.method.queue

binding_key = 'pingpong'
channel.queue_bind(
    exchange='pingpongtopic', queue=queue_name, routing_key=binding_key)

print(' [*] Waiting for logs. To exit press CTRL+C')


def callback(ch, method, properties, body):
    message = body.decode('ascii')
    image = json.loads(message)
    jobId = image['jobId']
    width = image['width']
    height = image['height']

    # positions = int(image['positions'])
    # colors = int(image['colors'])
    # # Use the bitmask for available positions in the image
    # while True:
    #     randomPosition = randint(0, width*height - 1)
    #     if not positions & 1 << randomPosition:
    #         positions = positions | 1 << randomPosition
    #         break
    # # Use the bitmask for available colors in the image
    # while True:
    #     randomColor = randint(0, 255*255*255 - 1)
    #     if not colors & 1 << randomColor:
    #         colors = colors | 1 << randomColor
    #         break

    pixelArray = json.loads(image['data'])
    positions = set([x[0] for x in pixelArray])
    while True:
        randomPosition = randint(0, width*height - 1)
        if not randomPosition in positions:
            break
    colors = set([x[1] for x in pixelArray])
    while True:
        randomColor = randint(0, 255*255*255 - 1)
        if not randomColor in colors:
            break
    # Append the new color at the available position
    pixelArray.append([randomPosition, randomColor])
    strPixelArray = json.dumps(pixelArray, separators=(',', ':'))
    print(len(pixelArray))
    # Update the api with the final data
    if len(pixelArray) == width*height:
        url = f'http://{pongapihost}:8000/pingpong/update/{jobId}/'
        body = {'iteration': len(pixelArray), 'data': strPixelArray}
        requests.post(url, json = body)
        return
    # Update iteration every 100 iterations
    elif len(pixelArray)%100 == 0:
        url = f'http://{pongapihost}:8000/pingpong/update/{jobId}/'
        body = {'iteration': len(pixelArray)}
        requests.post(url, json = body)
    job = {
        'width': image['width'],
        'height': image['height'],
        'jobId': jobId,
        'iteration': len(pixelArray),
        'data': strPixelArray,
        #'positions': positions,
        #'colors': colors,
    }
    channel.basic_publish(
        exchange='pingpongtopic', routing_key=binding_key, body=json.dumps(job, separators=(',', ':')))


channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()