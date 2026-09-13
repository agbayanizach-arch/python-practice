import os
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# --- 1. SETUP KEEPALIVE WEB SERVER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is active!"

def run():
    # Render automatically assigns a port via environment variables
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. START THE SERVER ---
keep_alive()

# --- 3. YOUR DISCORD BOT LOGIC ---
bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Load token from Render's environment variables safely
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)