import asyncio
import subprocess
from dotenv import load_dotenv
import os
import logging
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_REMOVED
from typing import Any, Optional

import discord
from discord import Intents, DMChannel, Embed, Color
from discord.ext import commands, tasks

from utils import load_commands, reformat_lang_dict, save_commands

load_dotenv()
LANGUAGE = os.environ.get("LANGUAGE", "en")
QUESTION_MARK = "❓"
DATA_PATH = "data"
STATIC_PATH = "static"
USERNAME = os.environ.get("USERNAME", "root")
HOST = os.environ.get("HOST", "localhost")
PORT = os.environ.get("PORT", "22")

# Load messages in the selected language
with open(os.path.join(STATIC_PATH, "lang.json"), "r") as f:
	lang_dict = json.load(f)
msg: dict[str, str] = reformat_lang_dict(lang_dict).get(LANGUAGE)

# Set up logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s %(levelname)s     %(message)s',
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
		user_id: int,
		question: str,
		info: Optional[str] = None,
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
		message_task = asyncio.create_task(bot.wait_for("message", check=check_response))
		reaction_task = asyncio.create_task(bot.wait_for("reaction_add", check=check_reaction))
		tasks = [message_task, reaction_task] if info else [message_task]
		done, pending = await asyncio.wait(
			tasks,
			return_when=asyncio.FIRST_COMPLETED
		)
		for task in pending:
			task.cancel()
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
		file = discord.File(os.path.join(STATIC_PATH, filename), filename=filename)
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
		usage="`%test [arg1] (arg2)`"
)
async def test(
	ctx: commands.Context,
	arg0: str,
	arg1: str=0
):
	logging.info(f"Test command executed by {ctx.author}")
	await ctx.send(msg.get("test_msg").format(arg0, arg1, arg0 + arg1))


@bot.group(
	brief=msg.get("monitor_brief"),
	description=msg.get("monitor_detail"),
	usage="`%monitor <add|remove|status>`"
)
async def monitor(ctx: commands.Context):
	"""
	Group of commands to monitor processes.
	"""
	if ctx.invoked_subcommand is None:
		await ctx.send("Invalid monitor command. Use `%monitor add` or `%monitor remove`.")


@monitor.command(
    brief=msg.get("monitor_add_brief"),
    description=msg.get("monitor_add_detail"),
	usage="`%monitor add`"
)
async def add(ctx: commands.Context):
	"""
	Set up a new command to monitor a process.
	"""
	# Create a thread from user's message
	thread = await ctx.message.create_thread(name=msg.get("monitor_add_thread_name"))

	await thread.send(msg.get("monitor_add_thread_intro"))

	# Ask the user for the monitoring details
	name = await ask_question_thread(thread, ctx.author.id, msg.get("monitor_add_q_name"))
	command = await ask_question_thread(thread, ctx.author.id, msg.get("monitor_add_q_command"), msg.get("monitor_add_info_command"))
	active_keyword = await ask_question_thread(thread, ctx.author.id, msg.get("monitor_add_q_active"), msg.get("monitor_add_info_active"))
	inactive_keyword = await ask_question_thread(thread, ctx.author.id, msg.get("monitor_add_q_inactive"), msg.get("monitor_add_info_inactive"))

	# Save the command details
	commands = load_commands()
	commands.append({
		"name": name,
		"command": command,
		"active_keyword": active_keyword,
		"inactive_keyword": inactive_keyword
	})
	save_commands(commands)

	await thread.send(msg.get("monitor_add_thread_success"))
	await thread.send(msg.get("monitor_add_thread_details"))
	await thread.send(msg.get("monitor_add_thread_command").format(command, active_keyword, inactive_keyword))

	# close the thread
	await thread.edit(archived=True)


@monitor.command(
    brief=msg.get("monitor_remove_brief"),
    description=msg.get("monitor_remove_detail"),
	usage="`%monitor remove [process_name]`"
)
async def remove(ctx: commands.Context, *args: str):
	"""
	Remove a command from the list of monitored processes.
	"""
	process_name = " ".join(args)
	commands = load_commands()
	# Remove the command from the list
	updated_commands = [cmd for cmd in commands if cmd.get("name") != process_name]

	if len(updated_commands) == len(commands):
		await ctx.send(msg.get("monitor_remove_not_found").format(process_name))
	else:
		save_commands(updated_commands)
		await ctx.send(msg.get("monitor_remove_success").format(process_name))


@monitor.command(
    brief=msg.get("monitor_status_brief"),
    description=msg.get("monitor_status_detail"),
	usage="`%monitor status`"
)
async def status(ctx: commands.Context):
	"""
	Check and print the status of monitored processes.
	"""
	logging.info(f"Status command executed by {ctx.author}")
	commands = load_commands()
	if not commands:
		await ctx.send(msg.get("monitor_status_empty"))
		return

	statuses = []
	for cmd in commands:
		# Ensure no missing fields
		for key in ["name", "command", "active_keyword", "inactive_keyword"]:
			if key not in cmd or not cmd[key]:
				status = ":warning:"
				process_name = cmd.get("name", "Unknown")
				process_name = f"{process_name} (missing {key})"
				break
		else:
			process_name = cmd["name"]
			command = cmd["command"]
			active_keyword = cmd["active_keyword"]
			inactive_keyword = cmd["inactive_keyword"]
			
			# Run the command
			ssh = f"ssh {USERNAME}@{HOST} -p {PORT}"
			result = subprocess.run(f"{ssh} {command}", shell=True, capture_output=True, text=True)
			output = result.stdout + result.stderr

			# Check the status in the output
			status = ""
			if (active_keyword.startswith("!") and active_keyword[1:] not in output)\
				or (active_keyword in output):
				# The process is active
				status = ":white_check_mark:"
			elif (inactive_keyword.startswith("!") and inactive_keyword[1:] not in output)\
				or (inactive_keyword in output):
				# The process is inactive
				if status:
					# Both active and inactive keywords are found
					status = ":warning:"
					process_name = f"{process_name} (both active and inactive)"
				else:
					status = ":x:"
			else:
				# The status is unknown
				status = ":grey_question:"
				logging.warning(f"Unknown status for {process_name}: {output}")

		statuses.append(f"{status} {process_name}")

	await ctx.send("\n".join(statuses))


if __name__ == "__main__":
	bot.run(os.environ.get("DISCORD_TOKEN"))
