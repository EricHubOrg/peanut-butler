FROM python:3.9-slim

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y openssh-client
COPY /home/${SSH_KEY_PATH}/.ssh/id_rsa /root/.ssh/id_rsa
RUN chmod 600 /root/.ssh/id_rsa

COPY . .

CMD ["python", "app.py"]
