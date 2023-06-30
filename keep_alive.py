from flask import Flask
from threading import Thread
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask("")

@app.route("/")
def home():
  return "Hello. I am alive!"

def run():
  port = int(os.getenv('PORT'))
  print(f'Listening on port {port}')
  app.run(host='0.0.0.0', port=port)

def keep_alive():
  t = Thread(target=run)
  t.start()