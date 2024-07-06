import asyncio
import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()
LANG = os.environ.get("LANG", "en")
COMMANDS_FILE = os.path.join("data", "commands.json")

def reformat_lang_dict(lang_dict: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
	"""
	Reformat the language dictionary to have the language as first keys.
	"""
	reformatted_dict = {}
	for message, translations in lang_dict.items():
		for lang, text in translations.items():
			if lang not in reformatted_dict:
				reformatted_dict[lang] = {}
			reformatted_dict[lang][message] = text
	return reformatted_dict

# Load messages in the selected language
with open(os.path.join("data", "lang.json"), "r") as f:
	lang_dict = json.load(f)
msg: dict[str, str] = reformat_lang_dict(lang_dict).get(LANG, "en")

def read_from_file_sync(filename: str) -> str:
	with open(filename, "r") as f:
		return f.read()

async def read_from_file(filename: str) -> str:
	loop = asyncio.get_event_loop()
	content = await loop.run_in_executor(None, read_from_file_sync, filename)
	return content

def write_to_file_sync(filename, content):
	with open(filename, "w") as f:
		f.write(content)

async def write_to_file(filename, content):
	loop = asyncio.get_event_loop()
	await loop.run_in_executor(None, write_to_file_sync, filename, content)

def load_commands():
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, "r") as file:
            return json.load(file)
    return []

def save_commands(commands):
    with open(COMMANDS_FILE, "w") as file:
        json.dump(commands, file, indent=4)

def get_greeting() -> str:
	"""
	Returns a greeting based on the current time of day.
	"""
	now = datetime.datetime.now()
	current_hour = now.hour

	if current_hour < 5:
		return msg.get("greeting_night")
	elif current_hour < 15:
		return msg.get("greeting_morning")
	elif current_hour < 21:
		return msg.get("greeting_afternoon")
	else:
		return msg.get("greeting_night")
