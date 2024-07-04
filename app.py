from dotenv import load_dotenv
import datetime, dateparser, re
import os, base64, logging, asyncio, json, uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_REMOVED

import discord
from discord import Intents, DMChannel, utils, Embed
from discord.ext import commands, tasks

from google_api import _get_credentials_sync
from googleapiclient.discovery import build

import chatbot
from reminders import *
from utils import *

load_dotenv()
logging.basicConfig(level=logging.INFO)

def get_roles(ctx=None, guild=None):
	if ctx:
		guild = ctx.guild
	roles = ['simple mortal', 'bots publics', 'privilegiat', 'alta taula', 'CREADOR']
	return {name:utils.get(guild.roles, name=name) for name in roles}

def get_deny_message(ctx=None, author=None, channel=None):
	if ctx:
		author = ctx.author
		channel = ctx.channel
	if author.id != int(os.environ['DISCORD_USER_ID']):
		return f'Ho sento {author.mention}, però no tens permís per fer això.'
	elif channel.id not in [int(os.environ['CHANNEL_ID_alta_taula']), int(os.environ['CHANNEL_ID_test_bots'])]:
		return f"Ho sento Creador, però aquests temes només els tractem a l'{bot.get_channel(int(os.environ['CHANNEL_ID_alta_taula'])).mention}"
	else:
		return None

def check_authority(level, ctx=None, author=None, guild=None, channel=None):
	# level 0: >= simple mortal
	# level 1: >= bots publics
	# level 2: >= privilegiat
	# level 3: >= alta taula
	# level 4: == CREADOR
	# level 5: == CREADOR (alta_taula or test_bots)
	if ctx:
		author = ctx.author
		guild = ctx.guild
		channel = ctx.channel
	roles = get_roles(guild=guild)
	author_role = author.top_role

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
	elif level == 5 and author_role != roles['CREADOR'] or channel.id not in [int(os.environ['CHANNEL_ID_alta_taula']), int(os.environ['CHANNEL_ID_test_bots'])]:
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

async def get_credentials():
	credentials = await _get_credentials_sync()
	return credentials

async def on_job_removed(event):
	job = scheduler.get_job(event.job_id)
	if not job:
		return
	if 'reminder' in job.tags:
		# get reminder and remove it from file
		rem = await retrieve_reminder_from_file(event.job_id, remove=True)
		# warn user if reminder end_date passed before activation_date (bot was offline when the reminder ended)
		if rem:
			end_date = datetime.datetime.strptime(rem['end_date'], '%Y-%m-%d %H:%M:%S')
			activation_date = datetime.datetime.strptime(rem['activation_date'], '%Y-%m-%d %H:%M:%S')
			if end_date < activation_date:
				channel = bot.get_channel(rem['channel_id'])
				await channel.send(f'{rem["author_id"]}, el recordatori "{rem["message"]}" ha caducat mentres jo estava offline.')

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix='%',
	description='Fidel majordom del Creador.\nExecuta `%help` per veure els comandaments disponibles.',
	intents=intents,
)

scheduler = AsyncIOScheduler()
scheduler.add_listener(on_job_removed, EVENT_JOB_REMOVED)

# bot.data = json.loads(read_from_file_sync(f'{os.environ["DATA_PATH"]}/bot_data/bot_data.json'))
bot.warning_state = 0

# Remove the default help command
bot.remove_command('help')

# Create a new help command
@bot.command(
	brief='Mostra aquest missatge.',
	description='Mostra informació sobre els comandaments disponibles.',
	usage='%help [comandament]'
)
async def help(ctx, arg0=None):
	if arg0:
		# Give info about the command
		command = bot.get_command(arg0)
		if command:
			embed = Embed(title=command.name, description=command.description, color=int(bot.data['embed_color'], 16))
			embed.add_field(name='us', value=f'`{command.usage}`')
			await ctx.send(embed=embed)
		else:
			await ctx.send(f'No existeix cap comandament que es digui "{arg0}"')
	else:
		# List all commands
		file = discord.File(f'{os.environ["DATA_PATH"]}/bot_data/peanut_butler.png', filename='peanut_butler.png')
		embed = Embed(title='Peanut Butler', description=bot.description, color=int(bot.data['embed_color'], 16))
		embed.set_thumbnail(url='attachment://peanut_butler.png')
		embed.set_author(name='Eric Lopez', url='https://github.com/Pikurrot', icon_url='https://avatars.githubusercontent.com/u/90217719?v=4')
		for command in sorted(bot.commands, key=lambda command: command.name):
			if command.name != 'help':
				embed.add_field(name=command.name, value=command.brief, inline=False)
		await ctx.send(embed=embed, file=file) #rata

@bot.event
async def on_ready():
	logging.info(f'We have logged in as {bot.user}')
	keep_alive.start()
	# gmail.start()
	scheduler.start()
	await activate_saved_reminders(scheduler, bot)

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
					conversation_limit = json.loads(await read_from_file(F'{os.environ["DATA_PATH"]}/bot_data/bot_data.json'))['conversation_limit']
					conversation['past_user_inputs'] = conversation['past_user_inputs'][-conversation_limit:]
					conversation['generated_responses'] = conversation['generated_responses'][-conversation_limit:]
					bot.data['conversation'] = conversation
					await write_to_file(F'{os.environ["DATA_PATH"]}/bot_data/bot_data.json', json.dumps(bot.data))
					logging.info('Conversation updated')
					await message.channel.send(response)
				else:
					raise Exception('Response was None')
			except Exception as e:
				await message.channel.send('Ho sento, però algo ha fallat')
				logging.info(f'Response failed to send: {e}')
		return
	
	if message.reference:
		# message is a reply
		referenced_message_id = message.reference.message_id
		referenced_message = await message.channel.fetch_message(referenced_message_id)
		if referenced_message.author == bot.user:
			# check if reaction is from an open reminder
			open_rem, data = await retrieve_reminder_from_file(referenced_message_id, key='q_message_id', type='open_reminders', return_data=True)
			if open_rem:
				# check if message is from the user who set the reminder
				if message.author.id == open_rem['author_id']:
					await complete_open_reminder(bot, open_rem['id'], user_input=message.content, rem=open_rem, data=data)

	# process commands normally
	await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
	if user.bot:
		# ignore reactions from other bots
		return

	# check if reaction is from an open reminder
	open_rem, data = await retrieve_reminder_from_file(reaction.message.id, key='q_message_id', type='open_reminders', return_data=True)
	if open_rem:
		# check if reaction is from the user who set the reminder
		if user.id == open_rem['author_id']:
			await complete_open_reminder(bot, open_rem['id'], emoji=reaction.emoji, rem=open_rem, data=data)

	if reaction.emoji == '⏰':
		if not isinstance(reaction.message.channel, discord.threads.Thread):
			# reaction is not in a thread
			await reminder(user=user, reaction=reaction)

@bot.command(
		brief='Set a reminder.',
		description='Set a reminder of a message. Also works by reacting to a message with :⏰_clock:.',
		usage='In a channel: %reminder [message]\nIn a thread: %reminder'
)
async def reminder(ctx=None, *args, **kwargs):
	if ctx:
		# command is called by user (channel or thread)
		try:
			thread = ctx.channel.thread
		except AttributeError:
			thread = None
		author = ctx.author
		if thread:
			message = thread.first_message
			message_text = message.content
		else:
			message = ctx.message
			message_text = ' '.join(args)
		guild = ctx.guild
		channel = ctx.channel
		by_reaction = False
	else:
		# command is called by reaction (channel)
		thread = None
		author = kwargs['user']
		message = kwargs['reaction'].message
		message_text = message.content
		guild = message.guild
		channel = message.channel
		by_reaction = True
		
	if check_authority(2, author=author, guild=guild, channel=channel):
		if thread:
			# command is called by user in a thread
			if thread.archived:
				# the thread is closed
				await thread.send('Ho sento, però el fil està tancat.')
				return
			else:
				# react to the message
				await message.add_reaction('⏰')
				q_message_mention = True
		else:
			# command is triggered in the channel (reaction or message)
			q_message_mention = False
			thread = await channel.create_thread(name=message_text, message=message, auto_archive_duration=60)
			if by_reaction:
				# remove the reaction
				await kwargs['reaction'].remove(author)
			# react to the message
			await message.add_reaction('⏰')
	elif ctx:
		# user does not have authority
		await ctx.send('Ho sento, però no tens autoritat per fer això.')
		return
	else:
		return

	# send creation message
	start_with = (str(author.mention)+' ') if q_message_mention else ''
	creation_message = await thread.send(f'{start_with}Has creat un recordatori amb missatge **{message_text}**.\
Vols establir els paràmetres? *Sinó, el recordatori es cancel·larà en 1 hora*.')
	await creation_message.add_reaction('❔')
	await creation_message.add_reaction('✅')
	await creation_message.add_reaction('❌')

	# save the reminder as open
	rem_id = str(uuid.uuid4())
	f = await read_from_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json')
	data = json.loads(f)
	data['open_reminders'].append({
		'id': rem_id,
		'q_message_id': creation_message.id,
		'start_with': start_with,
		'author_id': author.id,
		'channel_id': channel.id,
		'thread_id': thread.id,
		'message': message.content,
		'step': 0
	})
	await write_to_file(f'{os.environ["DATA_PATH"]}/bot_data/roaming.json', json.dumps(data))

	# schedule the reminder to be cancelled
	scheduler.add_job(pop_open_reminder, trigger='date', run_date=datetime.datetime.now() + datetime.timedelta(hours=1), args=[rem_id], id=rem_id)

@bot.command(
		brief='Breu descripció del commandament `test`.',
		description='Descripció més llarga del commandament `test`.',
		usage='%test [arg0] (arg1)'
)
async def test(ctx, arg0, arg1=0):
	logging.info(f'test at {datetime.datetime.utcnow()}')
	await ctx.send(f'Hello there! {arg0} + {arg1} = {int(arg0) + int(arg1)}')

@tasks.loop(minutes=1.0)
async def gmail():
	logging.info('Checking gmail...')
	channel = await bot.fetch_channel(int(os.environ['CHANNEL_ID_alta_taula']))
	user = await bot.fetch_user(int(os.environ['DISCORD_USER_ID']))

	try:
		# call the Gmail API
		service = build('gmail', 'v1', credentials=await get_credentials())
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