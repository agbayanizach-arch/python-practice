import os
import json
import asyncio
import random
import re
import discord
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

# --- 5. FIXED PREFIX COMMAND DEFINITIONS ---

# 1. New !giveaway Prefix Command
@bot.command(name="giveaway")
@commands.has_permissions(manage_guild=True)
async def start_giveaway(ctx, duration: str, winners: int, *, prize: str):
    """
    Usage: !giveaway <duration> <winners> <prize>
    Example: !giveaway 10m 1 Discord Nitro Classic
    """
    seconds = parse_duration(duration)
    if seconds is None:
        await ctx.send("❌ Use formatting patterns like `30s`, `10m`, `2h`, or `1d` for the duration parameter.")
        return
    if winners < 1:
        await ctx.send("❌ You must choose at least 1 winner.")
        return

    embed = discord.Embed(
        title="🎉 NEW GIVEAWAY 🎉",
        description=f"Click the button below to enter!\n\n🎁 **Prize:** {prize}\n⏱️ **Duration:** {duration}\n👥 **Winners:** {winners}",
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Started by {ctx.author.name}")
    
    view = GiveawayView()
    embed_msg = await ctx.send(embed=embed, view=view)
    
    # Automatically delete the triggering instruction command message to keep chat clean
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    asyncio.create_task(run_giveaway(ctx.channel, prize, seconds, winners, embed_msg, view))

# Error Handler for missing permissions or incorrect typing inputs
@start_giveaway.error
async def giveaway_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ **Incorrect Usage!** Please use the command format exactly like this:\n`!giveaway <duration> <winners> <prize>`\n\n*Example:* `!giveaway 5m 1 Discord Nitro`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need the **Manage Server** permission to run giveaways.")

# Run command
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)