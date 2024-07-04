from dotenv import load_dotenv
import datetime
import os, base64, logging, asyncio, json, uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_REMOVED

import discord
from discord import Intents, DMChannel, utils, Embed, Color
from discord.ext import commands, tasks

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

async def on_job_removed(event):
	job = scheduler.get_job(event.job_id)
	if not job:
		return

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix='%',
	description='Fidel majordom del Creador.\nExecuta `%help` per veure els comandaments disponibles.',
	intents=intents,
)

scheduler = AsyncIOScheduler()
scheduler.add_listener(on_job_removed, EVENT_JOB_REMOVED)

# to debug
for key in os.environ:
	logging.info(f'{key}={os.environ[key]}')

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
			embed = Embed(title=command.name, description=command.description, color=Color.blue())
			embed.add_field(name='us', value=f'`{command.usage}`')
			await ctx.send(embed=embed)
		else:
			await ctx.send(f'No existeix cap comandament que es digui "{arg0}"')
	else:
		# List all commands
		file = discord.File(f'{os.environ["DATA_PATH"]}/bot_data/peanut_butler.png', filename='peanut_butler.png')
		embed = Embed(title='Peanut Butler', description=bot.description, color=Color.blue())
		embed.set_thumbnail(url='attachment://peanut_butler.png')
		embed.set_author(name='Eric Lopez', url='https://github.com/Pikurrot', icon_url='https://avatars.githubusercontent.com/u/90217719?v=4')
		for command in sorted(bot.commands, key=lambda command: command.name):
			if command.name != 'help':
				embed.add_field(name=command.name, value=command.brief, inline=False)
		await ctx.send(embed=embed, file=file)

@bot.event
async def on_ready():
	logging.info(f'We have logged in as {bot.user}')
	keep_alive.start()
	scheduler.start()

@bot.event
async def on_message(message):
	if message.author.bot:
		# ignore messages from other bots
		return

	if isinstance(message.channel, DMChannel) or message.guild is None:
		# ignore private messages and messages outside of a server
		await message.channel.send('Ho sento, però no pots conversar amb mi en privat.')
		return

	# process commands normally
	await bot.process_commands(message)

@bot.command(
		brief='Breu descripció del commandament `test`.',
		description='Descripció més llarga del commandament `test`.',
		usage='%test [arg0] (arg1)'
)
async def test(ctx, arg0, arg1=0):
	logging.info(f'test at {datetime.datetime.now()}')
	await ctx.send(f'Hello there! {arg0} + {arg1} = {int(arg0) + int(arg1)}')

@tasks.loop(minutes=1.0)
async def keep_alive():
	logging.info(f'Life signal at {datetime.datetime.now()}')

@keep_alive.before_loop
async def before_keep_alive():
	await bot.wait_until_ready()

if __name__ == '__main__':
	bot.run(os.environ['DISCORD_TOKEN'])