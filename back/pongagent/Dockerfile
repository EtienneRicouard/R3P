FROM python:3.11-alpine
WORKDIR /usr/src/app

RUN pip install --no-cache-dir requests pika

COPY . .

CMD [ "python", "./agent.py" ]