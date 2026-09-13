import os
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. START THE SERVER ---
keep_alive()

# --- 3. YOUR DISCORD BOT LOGIC ---
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- 4. TEXT COMMANDS ---
@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello, {ctx.author.mention}! Wither Cloud is officially active and responding 24/7! 🚀")

# Load token from Render safely
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)