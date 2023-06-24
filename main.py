from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv
import os
from keep_alive import keep_alive

# bot
load_dotenv()

intents = Intents.default()
intents.message_content = True

bot = commands.Bot(
	command_prefix="$",
	description="Description from the program",
	intents=intents,
)

@bot.command()
async def test(ctx):
	await ctx.send("Hello there!")

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
