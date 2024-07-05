import asyncio

def read_from_file_sync(filename):
	with open(filename, 'r') as f:
		return f.read()

async def read_from_file(filename):
	loop = asyncio.get_event_loop()
	content = await loop.run_in_executor(None, read_from_file_sync, filename)
	return content

def write_to_file_sync(filename, content):
	with open(filename, 'w') as f:
		f.write(content)

async def write_to_file(filename, content):
	loop = asyncio.get_event_loop()
	await loop.run_in_executor(None, write_to_file_sync, filename, content)

def reformat_lang_dict(lang_dict):
	# Reformat the language dictionary to have the language as first keys
	reformatted_dict = {}
	for message, translations in lang_dict.items():
		for lang, text in translations.items():
			if lang not in reformatted_dict:
				reformatted_dict[lang] = {}
			reformatted_dict[lang][message] = text
	return reformatted_dict
