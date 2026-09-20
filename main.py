import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from checker import MaceChecker
from embed_builder import EmbedBuilder
import sys
import aiohttp
import io
import json
import os                    # <--- MAKE SURE THIS IS IMPORTED
from keep_alive import keep_alive  # <--- MAKE SURE THIS IS IMPORTED

# --- GRAB CREDENTIALS SECURELY FROM RENDER ---
TOKEN = os.environ.get("DISCORD_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# ... leave your MaceCloudBot class and check commands exactly as they are ...
