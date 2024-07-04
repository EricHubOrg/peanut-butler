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
