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
  port = int(os.environ.get('PORT', 8000))
  app.run(port=port)

def keep_alive():
  t = Thread(target=run)
  t.start()