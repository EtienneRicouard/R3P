#!/usr/bin/env python
import pika
from random import seed
from random import randint
import requests
import os
import flatbuffers
import R3PImage
import time
import numpy as np

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

total_time = 0
total_time_publishing = 0
total_time_idle = 0
last_callback_time = 0
def callback(ch, method, properties, body):
    global total_time
    global total_time_idle
    global total_time_publishing
    global last_callback_time
    t1 = time.time()
    if last_callback_time != 0:
        total_time_idle += t1 - last_callback_time
    image = R3PImage.R3PImage.GetRootAs(body, 0)
    # Prepare the output image
    builder = flatbuffers.Builder(len(body) + 8)
    jobId = image.Jobid().decode()
    builderJobId = builder.CreateString(jobId)
    iteration = image.Iteration()
    newIteration = iteration + 1

    R3PImage.StartPositionsVector(builder, newIteration)
    positions = image.PositionsAsNumpy()
    positionSet = set(positions)
    # Find an available position
    while True:
        randomPosition = randint(0, image.Width()*image.Height() - 1)
        if not randomPosition in positionSet:
            break
    # Append the new position
    positions = np.append(positions, randomPosition)
    # Convert the np array to bytes and dump the content in the image
    positionsByte = positions.tobytes()
    builder.head = builder.head - len(positionsByte)
    builder.Bytes[builder.head : (builder.head + len(positionsByte))] = positionsByte
    positions = builder.EndVector()

    R3PImage.StartColorsVector(builder, newIteration)
    colors = image.ColorsAsNumpy()
    colorSet = set(colors)
    # Find an available color
    while True:
        randomColor = randint(0, 255*255*255 - 1)
        if not randomColor in colorSet:
            break
    # Append the new color
    colors = np.append(colors, randomColor)
    # Convert the np array to bytes and dump the content in the image
    colorsByte = colors.tobytes()
    builder.head = builder.head - len(colorsByte)
    builder.Bytes[builder.head : (builder.head + len(colorsByte))] = colorsByte
    colors = builder.EndVector()

    R3PImage.Start(builder)
    R3PImage.AddPositions(builder, positions)
    R3PImage.AddColors(builder, colors)
    R3PImage.AddJobid(builder, builderJobId)
    R3PImage.AddWidth(builder, image.Width())
    R3PImage.AddHeight(builder, image.Height())
    R3PImage.AddIteration(builder, newIteration)
    r3pImage = R3PImage.End(builder)
    builder.Finish(r3pImage)
    buf = builder.Output()
    t2 = time.time()
    total_time += t2 - t1
    # Update the api with the final data
    if newIteration == image.Width()*image.Height():
        url = f'http://{pongapihost}:8000/pingpong/update/{jobId}/'
        body = {'iteration': newIteration, 'data': '[]'}
        requests.post(url, json = body)
        print("Processing Time=%s Idle Time=%s, Publishing Time=%s" % (total_time, total_time_idle, total_time_publishing))
        return
    # Update iteration every 100 iterations
    elif newIteration%100 == 0:
        print("Iteration=%s Time=%s" % (newIteration, t2 - t1))
        url = f'http://{pongapihost}:8000/pingpong/update/{jobId}/'
        body = {'iteration': newIteration}
        requests.post(url, json = body)
    channel.basic_publish(
        exchange='pingpongtopic', routing_key=binding_key, body=buf)
    t3 = time.time()
    total_time_publishing += t3 - t2
    last_callback_time = t3

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()