from dotenv import load_dotenv
import os
import base64

from discord import Intents, DMChannel
from discord.ext import commands

from keep_alive import keep_alive

from google_api import get_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

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
		# Ignore messages from other bots
		return

	if isinstance(message.channel, DMChannel) or message.guild is None:
		# Ignore private messages and messages outside of a server
		await message.channel.send('Ho sento, però no pots conversar amb mi en privat.')
		return

	# Process messages in the server normally
	await bot.process_commands(message)


@bot.command()
async def test(ctx):
	await ctx.send('Hello there!')
		
@bot.command()
async def gmail(ctx):
	if ctx.author.id != int(os.environ['DISCORD_USER_ID']):
		await ctx.send('No tens permís per fer això.')
		return
	try:
		# Call the Gmail API
		service = build('gmail', 'v1', credentials=get_credentials())
		# List all unread emails
		results = service.users().messages().list(userId='me', q='is:unread').execute()
		messages = results.get('messages', [])

		if not messages:
			await ctx.send('No hi ha correus nous.')
		else:
			await ctx.send('Tens {} correus nous:'.format(len(messages)))
			for message in messages:
				msg = service.users().messages().get(userId='me', id=message['id']).execute()

				# Get the subject and body of the message
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

				# Print the subject and body of the message
				await ctx.send(f'{subject}\{body}')

				# Mark the message as read
				service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()

	except HttpError as error:
		await ctx.send(f'An error occurred: {error}')
	except:
		await ctx.send('An error occurred: unknown')

keep_alive()
bot.run(os.environ['DISCORD_TOKEN'])
