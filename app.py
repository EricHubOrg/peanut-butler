import asyncio
from dotenv import load_dotenv
import os
import logging
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_REMOVED
from typing import Any

import discord
from discord import Intents, DMChannel, Embed, Color
from discord.ext import commands, tasks

from utils import load_commands, reformat_lang_dict, save_commands

load_dotenv()
LANGUAGE = os.environ.get("LANGUAGE", "en")
print(LANGUAGE)
QUESTION_MARK = "❓"

# Load messages in the selected language
with open(os.path.join("data", "lang.json"), "r") as f:
	lang_dict = json.load(f)
msg: dict[str, str] = reformat_lang_dict(lang_dict).get(LANGUAGE)

# Set up logging
logging.basicConfig(
	level=logging.INFO,
	datefmt="%Y-%m-%d %H:%M:%S"
)

# Set up the bot
intents = Intents.default()
intents.message_content = True
intents.messages = True
intents.reactions = True
bot = commands.Bot(
	command_prefix="%",
	description=msg.get("bot_description"),
	intents=intents,
)

# Set up the scheduler
scheduler = AsyncIOScheduler()
async def on_job_removed(event: Any):
	"""
	Remove the job from the scheduler when it is removed.
	"""
	job = scheduler.get_job(event.job_id)
	if not job:
		return
scheduler.add_listener(on_job_removed, EVENT_JOB_REMOVED)


# ========= DISCORD EVENTS ==========

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
	"""
	Process messages sent by users.
	"""
	if message.author.bot:
		# ignore messages from other bots
		return

	if isinstance(message.channel, DMChannel) or message.guild is None:
		# ignore private messages and messages outside of a server
		await message.channel.send(msg.get("no_dm"))
		return

	# process commands normally
	await bot.process_commands(message)

async def ask_question_thread(
		thread: discord.Thread,
		question: str,
		info: str,
		user_id: int
) -> str:
	"""
	Ask a question in a thread and return the answer.
	"""
	message = await thread.send(question)
	await message.add_reaction(QUESTION_MARK)

	def check_response(m: discord.Message) -> bool:
		# Check if the message is from the user in the thread
		return m.channel == thread and m.author.id == user_id

	def check_reaction(reaction: discord.Reaction, user: discord.User) -> bool:
		# Check if the reaction is a question mark from the user in the thread
		return (
			user.id == user_id and
			reaction.message.id == message.id and
			str(reaction.emoji) == QUESTION_MARK
		)

	while True:
		# Wait for a response or a reaction
		done, pending = await asyncio.wait(
			[bot.wait_for("message", check=check_response),
				bot.wait_for("reaction_add", check=check_reaction)],
			return_when=asyncio.FIRST_COMPLETED
		)
		if done:
			# Get the result
			completed_task = done.pop()
			result = completed_task.result()
			if isinstance(result, discord.Message): # Message
				return result.content
			elif isinstance(result, tuple): # Reaction
				await thread.send(info)

@tasks.loop(minutes=1.0)
async def keep_alive():
	logging.info("Life signal")

@keep_alive.before_loop
async def before_keep_alive():
	await bot.wait_until_ready()


# ========= DISCORD COMMANDS ==========

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
	logging.info(f"Help command executed by {ctx.author}")
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

@bot.command(
	brief=msg.get("monitor_brief"),
	description=msg.get("monitor_detail"),
	usage=msg.get("monitor_usage")
)
async def monitor(ctx: commands.Context):
	"""
	Set up a new command to monitor a process.
	"""
	thread = await ctx.message.create_thread(name=msg.get("monitor_thread_name"))

	await thread.send(msg.get("monitor_thread_intro"))

	command = await ask_question_thread(thread, msg.get("monitor_q_command"), msg.get("monitor_info_command"), ctx.author.id)
	active_keyword = await ask_question_thread(thread, msg.get("monitor_q_active"), msg.get("monitor_info_active"), ctx.author.id)
	inactive_keyword = await ask_question_thread(thread, msg.get("monitor_q_inactive"), msg.get("monitor_info_inactive"), ctx.author.id)

	# Save the command details
	commands = load_commands()
	commands.append({
		"command": command,
		"active_keyword": active_keyword,
		"inactive_keyword": inactive_keyword
	})
	save_commands(commands)

	await thread.send(msg.get("monitor_thread_success"))
	await thread.send(msg.get("monitor_thread_details"))
	await thread.send(msg.get("monitor_thread_command").format(command, active_keyword, inactive_keyword))


if __name__ == "__main__":
	bot.run(os.environ.get("DISCORD_TOKEN"))
