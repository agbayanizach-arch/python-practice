import os
import json
import asyncio
import random
import re
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- 1. SETUP KEEPALIVE WEB SERVER ---
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

keep_alive()

# --- 2. INTERACTIVE VIEWS ---
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entrants = set()

    @discord.ui.button(label="Join 🎉", style=discord.ButtonStyle.blurple, custom_id="join_giveaway_btn")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if user_id in self.entrants:
            self.entrants.remove(user_id)
            await interaction.response.send_message("👋 You left the giveaway.", ephemeral=True)
        else:
            self.entrants.add(user_id)
            await interaction.response.send_message("🎉 You have successfully entered the giveaway!", ephemeral=True)
        
        button.label = f"Join 🎉 ({len(self.entrants)})"
        await interaction.message.edit(view=self)

# --- 3. BOT ARCHITECTURE ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(GiveawayView())

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- 4. DURATION PARSER ---
def parse_duration(duration_str):
    match = re.match(r"^(\d+)([smhd])$", duration_str.lower())
    if not match:
        return None
    amount, unit = match.groups()
    amount = int(amount)
    if unit == 's': return amount
    if unit == 'm': return amount * 60
    if unit == 'h': return amount * 3600
    if unit == 'd': return amount * 86400
    return None

async def run_giveaway(channel, prize, duration, winners_count, embed_msg, view):
    await asyncio.sleep(duration)
    try:
        message = await channel.fetch_message(embed_msg.id)
    except discord.NotFound:
        return

    for btn in view.children:
        btn.disabled = True
    await message.edit(view=view)

    entrants_list = list(view.entrants)
    if not entrants_list:
        no_winner_embed = discord.Embed(
            title="🎁 GIVEAWAY ENDED 🎁",
            description=f"**Prize:** {prize}\n\n❌ No one entered the giveaway.",
            color=discord.Color.red()
        )
        await message.edit(embed=no_winner_embed)
        return

    actual_winners_count = min(winners_count, len(entrants_list))
    winners = random.sample(entrants_list, actual_winners_count)
    winner_mentions = ", ".join([f"<@{w_id}>" for w_id in winners])

    ended_embed = discord.Embed(
        title="🎁 GIVEAWAY ENDED 🎁",
        description=f"**Prize:** {prize}\n**Winners:** {winner_mentions}",
        color=discord.Color.gold()
    )
    await message.edit(embed=ended_embed)
    await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{prize}**!")

# --- 5. THE INSTANT SYNC COMMAND (PREFIX) ---
@bot.command()
@commands.has_permissions(administrator=True)
async def sync(ctx):
    await ctx.send("🔄 Force syncing slash commands to this server...")
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Success! Synced {len(synced)} commands instantly. Try your slash commands now!")

# --- 6. SLASH COMMAND DEFINITIONS ---

# 1. New Delete Ticket Slash Command
@bot.tree.command(name="delete-ticket", description="Permanently delete a support ticket channel.")
@app_commands.checks.has_permissions(manage_channels=True)
async def delete_ticket(interaction: discord.Interaction):
    channel = interaction.channel
    
    # Security check: Make sure this command is only used inside ticket channels
    if not channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ This command can only be used inside active ticket channels!", ephemeral=True)
        return

    # Acknowledge and display a clean countdown warning
    await interaction.response.send_message("🔒 **Ticket Closed.** This channel will be deleted in 5 seconds...")
    
    # Wait for the countdown to complete, then delete the channel
    await asyncio.sleep(5)
    await channel.delete()

# 2. Giveaway Slash Command
@bot.tree.command(name="giveaway", description="Start an interactive community giveaway event.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    prize="What are you giving away?",
    duration="When does it end? (e.g. 30s, 10m, 2h)",
    winners="How many random winners should be drawn?"
)
async def start_giveaway(interaction: discord.Interaction, prize: str, duration: str, winners: int):
    seconds = parse_duration(duration)
    if seconds is None:
        await interaction.response.send_message("❌ Use formats like `30s`, `10m`, `2h`.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎉 NEW GIVEAWAY 🎉",
        description=f"Click the button below to enter!\n\n🎁 **Prize:** {prize}\n⏱️ **Duration:** {duration}\n👥 **Winners:** {winners}",
        color=discord.Color.purple()
    )
    
    view = GiveawayView()
    await interaction.response.send_message("Starting giveaway...", ephemeral=True)
    embed_msg = await interaction.channel.send(embed=embed, view=view)
    asyncio.create_task(run_giveaway(interaction.channel, prize, seconds, winners, embed_msg, view))

# Run command
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)
