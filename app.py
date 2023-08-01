from dotenv import load_dotenv
import datetime
import os, base64, logging, asyncio, json

from discord import Intents, DMChannel, utils
from discord.ext import commands, tasks

from google_api import get_credentials
from googleapiclient.discovery import build

import chatbot

load_dotenv()

def get_roles(ctx):
	roles = ['simple mortal', 'bots publics', 'privilegiat', 'alta taula', 'CREADOR']
	return {name:utils.get(ctx.guild.roles, name=name) for name in roles}

def get_deny_message(ctx):
	if ctx.author.id != int(os.environ['DISCORD_USER_ID']):
		return f'Ho sento {ctx.author.mention}, però no tens permís per fer això.'
	elif ctx.channel.id not in [int(os.environ['CHANNEL_ID_alta_taula']), int(os.environ['CHANNEL_ID_test_bots'])]:
		return f"Ho sento Creador, però aquests temes només els tractem a l'{bot.get_channel(int(os.environ['CHANNEL_ID_alta_taula'])).mention}"
	else:
		return None

def check_authority(ctx, level):
	# level 0: >= simple mortal
	# level 1: >= bots publics
	# level 2: >= privilegiat
	# level 3: >= alta taula
	# level 4: == CREADOR
	# level 5: == CREADOR (alta_taula or test_bots)
	roles = get_roles(ctx)
	author_role = ctx.author.top_role

	if level == 0 and author_role < roles['simple mortal']:
		return 0
	elif level == 1 and author_role < roles['bots publics']:
		return 0
	elif level == 2 and author_role < roles['privilegiat']:
		return 0
	elif level == 3 and author_role < roles['alta taula']:
		return 0
	elif level == 4 and author_role != roles['CREADOR']:
		return 0
	elif level == 5 and author_role != roles['CREADOR'] or ctx.channel.id not in [int(os.environ['CHANNEL_ID_alta_taula']), int(os.environ['CHANNEL_ID_test_bots'])]:
		return 0
	return 1

def get_greeting():
	now = datetime.datetime.now()
	current_hour = now.hour

	if current_hour < 6:
		return 'Bona nit'
	elif current_hour < 15:
		return 'Bon dia'
	elif current_hour < 21:
		return 'Bona tarda'
	else:
		return 'Bona nit'
	
def _read_from_file_sync(filename):
	with open(filename, 'r') as f:
		return f.read()

async def read_from_file(filename):
	loop = asyncio.get_event_loop()
	content = await loop.run_in_executor(None, _read_from_file_sync, filename)
	return content

def _write_to_file_sync(filename, content):
	with open(filename, 'w') as f:
		f.write(content)

async def write_to_file(filename, content):
	loop = asyncio.get_event_loop()
	await loop.run_in_executor(None, _write_to_file_sync, filename, content)


intents = Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix='%',
	description='Fidel majordom del Creador.\nExecuta `%help` per veure els comandaments disponibles.',
	intents=intents,
)

with open('/data/bot_data/bot_data.json', 'r') as f:
	bot.data = json.load(f)
	bot.warning_state = 0

logging.basicConfig(level=logging.INFO)

@bot.event
async def on_ready():
	logging.info(f'We have logged in as {bot.user}')
	keep_alive.start()
	gmail.start()

@bot.event
async def on_message(message):
	if message.author.bot:
		# ignore messages from other bots
		return

	if isinstance(message.channel, DMChannel) or message.guild is None:
		# ignore private messages and messages outside of a server
		await message.channel.send('Ho sento, però no pots conversar amb mi en privat.')
		return

	if message.content.startswith('\\'):
		# gererate answer with LLM model
		async with message.channel.typing():
			try:
				prompt = message.content[1:] # ignore the first character (\)
				response, conversation = await chatbot.generate(prompt, bot.data['conversation'], os.environ['CHATBOT_API_URL'], os.environ['CHATBOT_API_KEY'])
				if response is not None:
					logging.info('Response generated successfully. Updating bot conversation...')
					conversation_limit = json.loads(await read_from_file('/data/bot_data/bot_data.json'))['conversation_limit']
					conversation['past_user_inputs'] = conversation['past_user_inputs'][-conversation_limit:]
					conversation['generated_responses'] = conversation['generated_responses'][-conversation_limit:]
					bot.data['conversation'] = conversation
					await write_to_file('/data/bot_data/bot_data.json', json.dumps(bot.data))
					logging.info('Conversation updated')
					await message.channel.send(response)
				else:
					raise Exception('Response was None')
			except Exception as e:
				await message.channel.send('Ho sento, però algo ha fallat')
				logging.info(f'Response failed to send: {e}')
		return

	# process commands normally
	await bot.process_commands(message)


@bot.command()
async def test(ctx):
	logging.info(f'test at {datetime.datetime.utcnow()}')
	await ctx.send('Hello there!')
		
@tasks.loop(minutes=1.0)
async def gmail():
	logging.info('Checking gmail...')
	channel = await bot.fetch_channel(int(os.environ['CHANNEL_ID_alta_taula']))
	user = await bot.fetch_user(int(os.environ['DISCORD_USER_ID']))

	try:
		# call the Gmail API
		service = build('gmail', 'v1', credentials=get_credentials())
		# list all unread emails
		logging.info('Reading emails...')
		results = service.users().messages().list(userId='me', q='is:unread').execute()
		messages = results.get('messages', [])

		if messages:
			await channel.send(f'{get_greeting()} {user.mention}, tens {len(messages)} correu'+'s'*(len(messages) > 1) + ' nou'+'s'*(len(messages) > 1) + ':')
			logging.info('Processing emails...')
			for message in messages:
				msg = service.users().messages().get(userId='me', id=message['id']).execute()

				# get the subject and body of the message
				payload = msg['payload']
				headers = payload['headers']
				for d in headers:
					if d['name'] == 'Subject':
						subject = d['value']
						break
				if 'parts' in payload:
					body = payload['parts'][0]['body']['data']
				else:
					body = payload['body']['data']

				body = base64.urlsafe_b64decode(body).decode('utf-8')
				limit = 80
				# short body = until character `limit` without including the word that is cut and/or the last \n
				short_body = body[:min(len(body), limit)].rsplit(' ', 1)[0]
				if short_body[-1] == '\n':
					short_body = short_body[:-1]

				# send the subject and body of the message
				logging.info('Sending email content...')
				await channel.send(f':envelope: **{subject}**\n{short_body}{"..." if len(body) > len(short_body) else ""}')

				# mark the message as read
				logging.info('Marking email as read...')
				service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
		bot.warning_state = True
	except Exception as e:
		logging.error(e)
		if bot.warning_state == 0:
			bot.warning_state = 1
			await channel.send(f'Disculpa {user.mention}, hi ha hagut algun error al llegir els correus de gmail.\nIntentaré arreglar-ho...')
			os.remove('token.json')
			logging.info('Gmail token removed. Restarting gmail check...')
			gmail.restart()
		elif bot.warning_state == 1:
			bot.warning_state = 2
			await channel.send(f'Ho sento, no he pogut arreglar-ho.')
			logging.info('Gmail check failed. Checks will still be made every minute')
		elif bot.warning_state == 2:
			logging.info('Gmail check failed.')
	else:
		logging.info('Gmail checked successfully')

@gmail.before_loop
async def before_gmail():
	await bot.wait_until_ready()

@tasks.loop(minutes=1.0)
async def keep_alive():
	logging.info(f'Life signal at {datetime.datetime.utcnow()}')

@keep_alive.before_loop
async def before_keep_alive():
	await bot.wait_until_ready()

if __name__ == '__main__':
	bot.run(os.environ['DISCORD_TOKEN'])