# Ping-pong exercise

## Quickstart

```bash
# Setup the docker compose which will build and run 2 pong agents, a rabbitmq server, the pingpong restapi and the react frontend
docker-compose up
```

## Dev env
```bash
# Start the RabbitMQ docker
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3.11-management

# Open another console for React UI
cd ui/
npm install
npm run dev

# Open another console for Django RestAPI
cd back/restapi
# setup a python virtual environment (I'm using conda)
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver

# Open a last console for the pong agents
cd back/pongagent
# setup a python virtual environment (I'm using conda)
pip install requests pika
python agent.py
```

## Some remarks
- In order to make sure that the rendering was possible at all times (with potential intermediate renderings or going back in time), the choice was made to store the data as an array of array ```[[pos1, color1], [pos2, color2], ...]``` where pos1 is the flattened position on the image (```pos = y*width + x```) and color is an integer representing the RGB data.
- I decided to use rabbitmq queues for the pingpong mecanism with simple python workers taking the jobs. This will ensure that the agents are stateless and entirely based on the queue message that they receive. It also allows to scale them fairly easily by simply duplicating the agents. These workers are not a REST API as indicated by the exercice. Hopefully, that is okay. I felt like rabbitmq was more adapted to this kind of mecanism.
- Django comes with a swagger accessible at [http://localhost:8000/swagger/](http://localhost:8000/swagger/) if you want to have a quick look at the restapi.
- I'm not sure what the config endpoint was supposed to be and what it was supposed to be doing so I haven't implemented it.

## Benchmark
- Measures were performed on an Intel i7-9750H CPU @ 2.60GHz and 8Gb of RAM. This stack is running on a WSL with local OpenSuse 15.4 with docker installed.
- Quick measures for the first draft (firstdraft branch) with a JSON encoded message going through rabbitmq:
  - Around 5 seconds for 56x56 rendering
  - Around 2 minutes for 128x128 rendering
- By moving the encoding to flatbuffers (branch flatbuffers) in order to avoid having to encode/decode JSON
  - Around 5 seconds for 56x56 rendering
  - Around 45 seconds for 128x128 rendering
  - A quick benchmark of the pongagent indicates (128x128 rendering): Processing Time=16.306734323501587 Idle Time=12.352599859237671, Publishing Time=8.079994678497314 where Processing Time is the cumulated time to generate each iteration of the picture. The Idle time is the time spent waiting for a new message from rabbitmq to arrive and the publishing time is the time to publish the message in rabbitmq.
  - Another benchmark with a simple rabbitmq message (only jobId + iteration) going over the network. For a 128x128 rendering: Processing Time=1.4127583503723145 Idle Time=8.975091457366943, Publishing Time=6.413078784942627
- At this point, I see 3 potential ways to save time.
  - Technically, positions (if we limit to 4096x4096 images) and RGB colors are 24 bits. These are saved in uint32 so we could reduce the binary stream size by around 25%. I'm not expecting to have huge gains with this except on large images. Right now, the bottleneck is not here.
  - One is to start making assumptions on the system and assume that the restapi and the workers are on the same machine. By using shared memory to communicate between the workers, this will save the communication time and also allow us to add some caching system within the shared memory (analyzing the whole picture at every iteration to look for available positions/colors is killing the performance). Pong agents would still be stateless as the shared memory would be managed by the restapi, pong agents can still be instantiated on the fly if needed and generate new pixels on the image.
  - If we can't assume that all workers will be on the same machine and that communication needs to be over the network, the next step would be to remove rabbitmq to avoid the overhead of the messaging queue and have the 2 pongagents communicate with one another through websockets. That will make us lose the scalability and reliability that rabbitmq was providing to not miss a message in case an agent has an issue but it should be faster if the message is sent directly between the pong agents.


## TODO
- Rework code to transmit endpoints and ports using env variables for flexibility
- Rework docker-compose network to only expose the React and Restapi endpoints. Rabbitmq and the pong agents should be hidden
- Rework agent to acknowledge the message only after sending the next iteration to the queue. Right now it is auto-acknowledging and we might lose some messages if an agent crash.
- Create a websocket endpoint in the django restapi to stream the progress report instead of polling
- Implement a scrollbar to navigate in the final rendering based on iteration. Each modification will contact the render endpoint with the given iteration N (also need to take into account the iteration parameter in the render endpoint by applying only the first N values of the data array).
