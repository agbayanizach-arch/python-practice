import os
import discord
from discord.ext import commands

# Allows the bot to read server messages
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} and ready!")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong! 🏓")

# Securely reads your secret token from your free host's dashboard
bot.run(os.getenv("DISCORD_TOKEN"))