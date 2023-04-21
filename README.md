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
- WIP: Right now performances for large renderings are fairly slow on my laptop (FYI: I have a intel i5 and 4Gb of RAM). This stack is running on a WSL with local OpenSuse 15.4 with docker installed.
- Quick measures at the moment:
  - Around 5 seconds for 56x56 rendering
  - Around 2 minutes for 128x128 rendering
I think the JSON encoding for the rabbitmq message is killing me, forcing to parse the data again and reencode it into JSON.

## TODO
- Rework code to transmit endpoints and ports using env variables for flexibility
- Rework docker-compose network to only expose the React and Restapi endpoints. Rabbitmq and the pong agents should be hidden
- Rework agent to acknowledge the message only after sending the next iteration to the queue. Right now it is auto-acknowledging and we might lose some messages if an agent crash.
- Create a websocket endpoint in the django restapi to stream the progress report instead of polling
- Implement a scrollbar to navigate in the final rendering based on iteration. Each modification will contact the render endpoint with the given iteration N (also need to take into account the iteration parameter in the render endpoint by applying only the first N values of the data array).
- Too much time is lost trying to deserializing the JSON data from the message. I need to rework the rabbitmq messages to optimise this, most likely a binary data stream with specific bits dedicated to imagesize, jobid, and the array at the end.