FROM python:3.9-slim

ARG PORT
ARG HOST
ARG SSH_PRIVATE_KEY

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y openssh-client

COPY . .

# Add the keys and set permissions
RUN mkdir -p /root/.ssh
RUN echo ${SSH_PRIVATE_KEY} > /root/.ssh/id_rsa && chmod 600 /root/.ssh/id_rsa

# Add the host's key to known hosts
RUN export PORT=${PORT} HOST=${HOST} && ssh-keyscan -p $PORT $HOST > /root/.ssh/known_hosts

CMD ["python", "app.py"]
