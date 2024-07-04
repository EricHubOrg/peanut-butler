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
		file = discord.File(f'data/bot_data/peanut_butler.png', filename='peanut_butler.png')
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