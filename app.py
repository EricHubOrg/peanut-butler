from dotenv import load_dotenv
import os
import base64
import datetime

from discord import Intents, DMChannel, utils
from discord.ext import commands, tasks

from google_api import get_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

def get_roles(ctx):
	roles = ["simple mortal", "bots publics", "privilegiat", "alta taula", "CREADOR"]
	return {name:utils.get(ctx.guild.roles, name=name) for name in roles}

def get_deny_message(ctx):
	if ctx.author.id != int(os.environ['DISCORD_USER_ID']):
		return f'Ho sento {ctx.author.mention}, però no tens permís per fer això.'
	elif ctx.channel.id not in [int(os.environ['CHANNEL_ID_alta_taula']), int(os.environ['CHANNEL_ID_test_bots'])]:
		return f'Ho sento Creador, però aquests temes només els tractem a l\'{bot.get_channel(int(os.environ["CHANNEL_ID_alta_taula"])).mention}'
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

	if level == 0 and author_role < roles["simple mortal"]:
		return 0
	elif level == 1 and author_role < roles["bots publics"]:
		return 0
	elif level == 2 and author_role < roles["privilegiat"]:
		return 0
	elif level == 3 and author_role < roles["alta taula"]:
		return 0
	elif level == 4 and author_role != roles["CREADOR"]:
		return 0
	elif level == 5 and author_role != roles["CREADOR"] or ctx.channel.id not in [int(os.environ['CHANNEL_ID_alta_taula']), int(os.environ['CHANNEL_ID_test_bots'])]:
		return 0
	return 1

def get_greeting():
	now = datetime.datetime.now()
	current_hour = now.hour

	if current_hour < 6:
		return "Bona nit"
	elif current_hour < 15:
		return "Bon dia"
	elif current_hour < 21:
		return "Bona tarda"
	else:
		return "Bona nit"

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix='%',
	description='Fidel majordom del Creador.\nExecuta `%help` per veure els comandaments disponibles.',
	intents=intents,
)

bot.warning_state = 0

@bot.event
async def on_ready():
	print(f'We have logged in as {bot.user}')
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

	# process messages in the server normally
	await bot.process_commands(message)


@bot.command()
async def test(ctx):
	await ctx.send('Hello there!')
		
@tasks.loop(minutes=1.0)
async def gmail():
	channel = await bot.fetch_channel(int(os.environ['CHANNEL_ID_alta_taula']))
	user = await bot.fetch_user(int(os.environ['DISCORD_USER_ID']))

	try:
		# call the Gmail API
		service = build('gmail', 'v1', credentials=get_credentials())
		# list all unread emails
		results = service.users().messages().list(userId='me', q='is:unread').execute()
		messages = results.get('messages', [])

		if messages:
			await channel.send(f'{get_greeting()} {user.mention}, tens {len(messages)} correu'+'s'*(len(messages) > 1) + ' nou'+'s'*(len(messages) > 1) + ':')
			for message in messages:
				msg = service.users().messages().get(userId='me', id=message['id']).execute()

				# get the subject and body of the message
				payload = msg['payload']
				headers = payload['headers']
				for d in headers:
					if d['name'] == 'Subject':
						subject = d['value']
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

				# print the subject and body of the message
				await channel.send(f':envelope: **{subject}**\n{short_body}{"..." if len(body) > len(short_body) else ""}')

				# mark the message as read
				service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
		bot.warning_state = True

	except HttpError as error:
		if bot.warning_state == 0:
			bot.warning_state = 1
			await channel.send(f'Disculpa {user.mention}, hi ha hagut un error al llegir els correus de gmail: *{error}*.\nIntentaré arreglar-ho...')
			os.remove('token.json')
			gmail.restart()
		elif bot.warning_state == 1:
			bot.warning_state = 2
			await channel.send(f'Ho sento {user.mention}, no he pogut arreglar-ho.')

	except:
		if bot.warning_state == 0:
			bot.warning_state = 1
			await channel.send(f'Disculpa {user.mention}, hi ha hagut algun error al llegir els correus de gmail.\nIntentaré arreglar-ho...')
			os.remove('token.json')
			gmail.restart()
		elif bot.warning_state == 1:
			bot.warning_state = 2
			await channel.send(f'Ho sento {user.mention}, no he pogut arreglar-ho.')

@gmail.before_loop
async def before_gmail():
	await bot.wait_until_ready()

if __name__ == "__main__":
	bot.run(os.environ['DISCORD_TOKEN'])