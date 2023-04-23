#!/usr/bin/env python
import json
from multiprocessing import resource_tracker, shared_memory
import struct
import pika
from random import seed
from random import randint
import requests
import os
import flatbuffers
import R3PImage
import time
import numpy as np


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

seed(1)
host = os.getenv('RABBITMQ_HOST', 'localhost')
pongapihost = os.getenv('PONGAPI_HOST', 'localhost')
# Have to patch the resource tracker to make shm work properly
remove_shm_from_resource_tracker()

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
    # Retrieve parameters from message
    image = R3PImage.R3PImage.GetRootAs(body, 0)
    width = image.Width()
    height = image.Height()
    jobId = image.Jobid().decode()
    iteration = image.Iteration()
    newIteration = iteration + 1

    # Retrieve position and associated masks from SHM
    bufferSize = height*width*4 #uint32
    shmPos = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-pos", size=bufferSize)
    posBuf = shmPos.buf

    bitmaskSize = height*width
    shmPosMask = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-posMask", size=bitmaskSize)
    posMaskBuf = shmPosMask.buf

    # Arbitrary criteria for now, let's say that for the last 0.1%, we are going to generate a correct position every single time
    # instead of randomly trying to land on an empty position
    # TODO: Optimise this value for large images based on empirical data
    if newIteration/(height*width) > 0.999:
        randomPosition = randint(0, width*height - newIteration)
        availablePosCounter = 0
        for i in range(bitmaskSize):
            if posMaskBuf[i] and randomPosition == availablePosCounter:
                randomPosition = i
                break
            availablePosCounter += posMaskBuf[i]
    else:
        while True:
            randomPosition = randint(0, width*height - 1)
            # If the position is available
            if posMaskBuf[randomPosition]:
                break
    # Mark the position as unavailable
    posMaskBuf[randomPosition] = 0
    # Fill the buffer with the new position
    posBuf[4*iteration:4*iteration+4] = struct.pack("I", randomPosition)

    # Retrieve colors and associated masks from SHM
    shmCol = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-col", size=bufferSize)
    colBuf = shmCol.buf
    colmaskSize = 256*256*256
    shmColMask = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-colMask", size=colmaskSize)
    colMaskBuf = shmColMask.buf

    # Arbitrary criteria for now, let's say that for the last 0.1%, we are going to generate a correct color every single time
    # instead of randomly trying to land on an empty position
    # TODO: Optimise this value for large images based on empirical data
    if newIteration/colmaskSize > 0.999:
        randomColor = randint(0, 256*256*256 - newIteration)
        availableColCounter = 0
        for i in range(bitmaskSize):
            if colMaskBuf[i] and randomColor == availableColCounter:
                randomColor = i
                break
            availableColCounter += colMaskBuf[i]
    else:
        while True:
            randomColor = randint(0, 256*256*256 - 1)
            # If the color is available
            if colMaskBuf[randomColor] == 1:
                break
    # Mark the color as unavailable
    colMaskBuf[randomColor] = 0
    # Fill the buffer with the new color
    colBuf[4*iteration:4*iteration+4] = struct.pack("I", randomColor)

    # Prepare the output image
    builder = flatbuffers.Builder(len(body))
    builderJobId = builder.CreateString(jobId)
    R3PImage.Start(builder)
    R3PImage.AddJobid(builder, builderJobId)
    R3PImage.AddWidth(builder, width)
    R3PImage.AddHeight(builder, height)
    R3PImage.AddIteration(builder, newIteration)
    r3pImage = R3PImage.End(builder)
    builder.Finish(r3pImage)
    buf = builder.Output()
    t2 = time.time()
    total_time += t2 - t1
    # Update the api with the final data
    if newIteration == width*height:
        positionList = struct.unpack(f'{width*height}I', posBuf)
        colorList = struct.unpack(f'{width*height}I', colBuf)
        data = []
        for i in range(len(positionList)):
            data.append([positionList[i], colorList[i]])
        url = f'http://{pongapihost}:8000/pingpong/update/{jobId}/'
        body = {'iteration': newIteration, 'data': json.dumps(data)}
        requests.post(url, json = body)
        print("Processing Time=%s Idle Time=%s, Publishing Time=%s" % (total_time, total_time_idle, total_time_publishing))
        # Close the shm for this iteration
        shmPos.close()
        shmPosMask.close()
        shmPos.unlink()
        shmPosMask.unlink()
        shmCol.close()
        shmColMask.close()
        shmCol.unlink()
        shmColMask.unlink()
        return
    # Update iteration every 100 iterations
    elif newIteration%100 == 0:
        print("Iteration=%s Time=%s" % (newIteration, t2 - t1))
        url = f'http://{pongapihost}:8000/pingpong/update/{jobId}/'
        body = {'iteration': newIteration}
        requests.post(url, json = body)
    channel.basic_publish(
        exchange='pingpongtopic', routing_key=binding_key, body=buf)
    # Close the shm for this iteration
    shmPos.close()
    shmPosMask.close()
    shmCol.close()
    shmColMask.close()
    t3 = time.time()
    total_time_publishing += t3 - t2
    last_callback_time = t3

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()