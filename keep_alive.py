from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route("/")
def home():
	return "Hello. I am alive!"

def run():
	app.run()

# def keep_alive():
# 	t = Thread(target=run)
# 	t.start()