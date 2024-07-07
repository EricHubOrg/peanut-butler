FROM python:3.9-slim

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y openssh-client

COPY . .

RUN mkdir -p /root/.ssh
RUN echo "$SSH_PRIVATE_KEY" > /root/.ssh/id_rsa && chmod 600 /root/.ssh/id_rsa

CMD ["python", "app.py"]
