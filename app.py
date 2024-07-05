from dotenv import load_dotenv
import datetime
import os, base64, logging, asyncio, json, uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_REMOVED
from typing import Any

import discord
from discord import Intents, DMChannel, utils, Embed, Color
from discord.ext import commands, tasks

from utils import *

load_dotenv()
LANG = os.environ.get("LANG", "en")
# Load messages in the selected language
with open(os.path.join("data", "lang.json"), "r") as f:
	lang_dict = json.load(f)
msg: dict[str, str] = reformat_lang_dict(lang_dict).get(LANG, "en")

# Set up logging
logging.basicConfig(
	level=logging.INFO,
	datefmt="%Y-%m-%d %H:%M:%S"
)

def get_greeting() -> str:
	"""
	Returns a greeting based on the current time of day.
	"""
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

async def on_job_removed(event: Any):
	"""
	Remove the job from the scheduler when it is removed.
	"""
	job = scheduler.get_job(event.job_id)
	if not job:
		return

# Set up the bot
intents = Intents.default()
intents.message_content = True
bot = commands.Bot(
	command_prefix="%",
	description=msg.get("bot_description"),
	intents=intents,
)

# Set up the scheduler
scheduler = AsyncIOScheduler()
scheduler.add_listener(on_job_removed, EVENT_JOB_REMOVED)

# Create a new help command
bot.remove_command("help") # Remove the default
@bot.command(
	brief=msg.get("help_brief"),
	description=msg.get("help_detail"),
	usage=msg.get("help_usage")
)
async def help(
	ctx: commands.Context,
	arg0: str=None
):
	"""
	Displays information about the available commands.
	"""
	color = Color.blue()
	if arg0:
		# Give info about the command
		command = bot.get_command(arg0)
		if command:
			embed = Embed(title=command.name, description=command.description, color=color)
			embed.add_field(name="us", value=f"`{command.usage}`")
			await ctx.send(embed=embed)
		else:
			await ctx.send(msg.get("command_not_found").format(arg0))
	else:
		# List all commands
		filename = "peanut_butler.png"
		file = discord.File(os.path.join("data", "bot_data", filename), filename=filename)
		embed = Embed(title="Peanut Butler", description=bot.description, color=color)
		embed.set_thumbnail(url=f"attachment://{filename}")
		embed.set_author(name="Eric Lopez", url="https://github.com/Pikurrot", icon_url="https://avatars.githubusercontent.com/u/90217719?v=4")
		for command in sorted(bot.commands, key=lambda command: command.name):
			if command.name != "help":
				embed.add_field(name=command.name, value=command.brief, inline=False)
		await ctx.send(embed=embed, file=file)

@bot.event
async def on_ready():
	"""
	Start processes when the bot is ready.
	"""
	logging.info(f"We have logged in as {bot.user}")
	keep_alive.start()
	scheduler.start()

@bot.event
async def on_message(message: discord.Message):
	if message.author.bot:
		# ignore messages from other bots
		return

	if isinstance(message.channel, DMChannel) or message.guild is None:
		# ignore private messages and messages outside of a server
		await message.channel.send(msg.get("no_dm"))
		return

	# process commands normally
	await bot.process_commands(message)

@bot.command(
		brief=msg.get("test_brief"),
		description=msg.get("test_detail"),
		usage=msg.get("test_usage")
)
async def test(
	ctx: commands.Context,
	arg0: str,
	arg1: str=0
):
	logging.info(f"Test command executed by {ctx.author}")
	await ctx.send(msg.get("test_msg").format(arg0, arg1, arg0 + arg1))

@tasks.loop(minutes=1.0)
async def keep_alive():
	logging.info(f"Life signal")

@keep_alive.before_loop
async def before_keep_alive():
	await bot.wait_until_ready()

if __name__ == "__main__":
	bot.run(os.environ.get("DISCORD_TOKEN"))
