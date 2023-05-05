#!/usr/bin/env python
import json
from multiprocessing import resource_tracker, shared_memory
import struct
import pika
from random import seed
from random import randint
import requests
import os
import time
import sys

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

if len(sys.argv) < 2:
    print('Missing agent type')
    sys.exit(1)

seed(1)
host = os.getenv('RABBITMQ_HOST', 'localhost')
pongapihost = os.getenv('PONGAPI_HOST', 'localhost')
# Have to patch the resource tracker to make shm work properly
remove_shm_from_resource_tracker()

# Todo: do not disable heartbeat and run in a separate thread instead
connection = pika.BlockingConnection(
    pika.ConnectionParameters(heartbeat=0, host=host))
channel = connection.channel()

channel.exchange_declare(exchange='pingpongtopic', exchange_type='topic')

channelName = sys.argv[1]
result = channel.queue_declare(channelName)
queue_name = result.method.queue

binding_key = 'pingpong'
channel.queue_bind(
    exchange='pingpongtopic', queue=queue_name, routing_key=binding_key)

print(' [*] Waiting for jobs. To exit press CTRL+C')

def callback(ch, method, properties, body):
    t1 = time.time()
    # Retrieve parameters from message
    message = body.decode()
    image = json.loads(message)
    jobId = image['jobId']
    print('Starting job', jobId)
    width = image['width']
    height = image['height']

    # Retrieve status
    shmStatus = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-status", size=5)
    statusBuf = shmStatus.buf
    iteration = struct.unpack('I', statusBuf[0:4])[0]
    newIteration = iteration + 1

    # Retrieve position and associated masks from SHM
    bufferSize = height*width*4 #uint32
    shmPos = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-pos", size=bufferSize)
    posBuf = shmPos.buf
    bitmaskSize = height*width
    shmPosMask = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-posMask", size=bitmaskSize)
    posMaskBuf = shmPosMask.buf
    # Retrieve colors and associated masks from SHM
    shmCol = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-col", size=bufferSize)
    colBuf = shmCol.buf
    colmaskSize = 256*256*256
    shmColMask = shared_memory.SharedMemory(create=False, name=f"{str(jobId)}-colMask", size=colmaskSize)
    colMaskBuf = shmColMask.buf

    # Loop on the image
    statusCheck = 0 if sys.argv[1] == 'ping' else 1
    while newIteration < width*height:
        # Wait for this agent's turn
        while statusBuf[4] != statusCheck or statusBuf[4] == 2:
            # The other agent has finished the last iteration, we can clean up the shmstatus and exit the callback safely
            # Unless the buffer is locked externally
            if statusBuf[4] == 2 and statusBuf[5] != 1:
                shmPos.close()
                shmPosMask.close()
                shmPos.unlink()
                shmPosMask.unlink()
                shmCol.close()
                shmColMask.close()
                shmCol.unlink()
                shmColMask.unlink()
                shmStatus.close()
                shmStatus.unlink()
                t2 = time.time()
                print("Processing Time=%s" % (t2 - t1))
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            time.sleep(0.00001)
        iteration = struct.unpack('I', statusBuf[0:4])[0]
        newIteration = iteration + 1
        # Arbitrary criteria for now, let's say that for the last 0.001%, we are going to generate a correct position every single time
        # instead of randomly trying to land on an empty position
        if newIteration/(height*width) > 0.99999:
            randomPosition = randint(0, width*height - newIteration)
            availablePosCounter = 0
            for i in range(bitmaskSize):
                if posMaskBuf[i] and randomPosition == availablePosCounter:
                    randomPosition = i
                    break
                availablePosCounter += posMaskBuf[i]
        else:
            # Generate random positions until we find an available spot
            while True:
                randomPosition = randint(0, width*height - 1)
                # If the position is available
                if posMaskBuf[randomPosition]:
                    break
        # Mark the position as unavailable
        posMaskBuf[randomPosition] = 0
        # Fill the buffer with the new position
        posBuf[4*iteration:4*iteration+4] = struct.pack("I", randomPosition)

        # Arbitrary criteria for now, let's say that for the last 0.001%, we are going to generate a correct color every single time
        # instead of randomly trying to land on an empty position
        if newIteration/colmaskSize > 0.99999:
            randomColor = randint(0, 256*256*256 - newIteration)
            availableColCounter = 0
            for i in range(bitmaskSize):
                if colMaskBuf[i] and randomColor == availableColCounter:
                    randomColor = i
                    break
                availableColCounter += colMaskBuf[i]
        else:
            # Generate random colors until we find an available spot
            while True:
                randomColor = randint(0, 256*256*256 - 1)
                # If the color is available
                if colMaskBuf[randomColor] == 1:
                    break
        # Mark the color as unavailable
        colMaskBuf[randomColor] = 0
        # Fill the buffer with the new color
        colBuf[4*iteration:4*iteration+4] = struct.pack("I", randomColor)
        # Now update the iteration
        statusBuf[0:4] = struct.pack("I", newIteration)
        # Used for debug
        if newIteration%1000 == 0 or newIteration%1000 == 1:
            print(newIteration)
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
            # Last iteration, tag the status as 2 to stop the other worker
            statusBuf[4] = 2
            t2 = time.time()
            print("Processing Time=%s" % (t2 - t1))
            # Close the shm for this agent
            shmPos.close()
            shmPosMask.close()
            shmCol.close()
            shmColMask.close()
            shmStatus.close()
            # Don't unlink the shms, the other agent will do it when exiting
            # Acknowledge the message for this agent and exit
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return
        else:
            # Tag the status buffer for the other agent
            statusBuf[4] = 1 if sys.argv[1] == 'ping' else 0

channel.basic_consume(
    queue=queue_name, on_message_callback=callback)

channel.start_consuming()