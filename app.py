from dotenv import load_dotenv
import os
# import base64

from discord import Intents, DMChannel, utils
from discord.ext import commands
# from flask import Flask
# from threading import Thread

# from google_api import get_credentials
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

load_dotenv()

# app = Flask(__name__)

# @app.route("/")
# def home():
# 	return "Hello. I am alive!"

# def run_app():
# 	app.run()

# def keep_alive():
# 	print('Starting app...')
# 	app_thread = Thread(target=run_app)
# 	app_thread.start()
# 	print('App started.')


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
		
intents = Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix='%',
	description='Fidel majordom del Creador.\nExecuta `%help` per veure els comandaments disponibles.',
	intents=intents,
)


@bot.event
async def on_ready():
	print(f'We have logged in as {bot.user}')

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
		
# @bot.command()
# async def gmail(ctx):
# 	# check if the user has the authority to use this command
# 	if not check_authority(ctx, 5):
# 		await ctx.send(get_deny_message(ctx))
# 		return
	
# 	try:
# 		# call the Gmail API
# 		service = build('gmail', 'v1', credentials=get_credentials())
# 		# list all unread emails
# 		results = service.users().messages().list(userId='me', q='is:unread').execute()
# 		messages = results.get('messages', [])

# 		if not messages:
# 			await ctx.send('No hi ha correus nous.')
# 		else:
# 			await ctx.send('Tens {} correus nous:'.format(len(messages)))
# 			for message in messages:
# 				msg = service.users().messages().get(userId='me', id=message['id']).execute()

# 				# get the subject and body of the message
# 				payload = msg['payload']
# 				headers = payload['headers']
# 				for d in headers:
# 					if d['name'] == 'Subject':
# 						subject = d['value']
# 				if 'parts' in payload:
# 					body = payload['parts'][0]['body']['data']
# 				else:
# 					body = payload['body']['data']

# 				body = base64.urlsafe_b64decode(body).decode('utf-8')
# 				limit = 80
# 				# short body = until character `limit` without including the word that is cut and/or the last \n
# 				short_body = body[:min(len(body), limit)].rsplit(' ', 1)[0]
# 				if short_body[-1] == '\n':
# 					short_body = short_body[:-1]

# 				# print the subject and body of the message
# 				await ctx.send(f':envelope: **{subject}**\n{short_body}{"..." if len(body) > limit else ""}')

# 				# mark the message as read
# 				service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()

# 	except HttpError as error:
# 		await ctx.send(f'An error occurred: {error}')
# 	except:
# 		await ctx.send('An error occurred: unknown')

if __name__ == "__main__":
	# keep_alive()
	bot.run(os.environ['DISCORD_TOKEN'])