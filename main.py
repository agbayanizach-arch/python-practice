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

# --- 2. CONFIGURATION HELPER FUNCTIONS ---
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- 3. INTERACTIVE TICKET & GIVEAWAY COMPONENT UI ---
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket 🎫", style=discord.ButtonStyle.green, custom_id="open_ticket_btn")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
        if existing_channel:
            await interaction.response.send_message(f"❌ You already have an open ticket here: {existing_channel.mention}", ephemeral=True)
            return
        overrides = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(name=f"ticket-{member.name}", overwrites=overrides)
        close_view = TicketCloseControl()
        embed = discord.Embed(
            title="Ticket Created!",
            description=f"Welcome {member.mention},\n\nPlease describe your issue or inquiry here. Support staff will assist you shortly.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(embed=embed, view=close_view)
        await interaction.response.send_message(f"✅ Ticket created successfully! Go to {ticket_channel.mention}", ephemeral=True)

class TicketCloseControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🔒", style=discord.ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 This ticket will be deleted in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

# Giveaway Entry Button Handler
class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Keep working forever during the countdown
        self.entrants = set() # Store unique user IDs

    @discord.ui.button(label="Join 🎉", style=discord.ButtonStyle.blurple, custom_id="join_giveaway_btn")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if user_id in self.entrants:
            self.entrants.remove(user_id)
            await interaction.response.send_message("👋 You left the giveaway.", ephemeral=True)
        else:
            self.entrants.add(user_id)
            await interaction.response.send_message("🎉 You have successfully entered the giveaway!", ephemeral=True)
        
        # Dynamically update the join count button label
        button.label = f"Join 🎉 ({len(self.entrants)})"
        await interaction.message.edit(view=self)

# --- 4. CORE BOT INITIALIZATION ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(TicketControls())
        self.add_view(TicketCloseControl())
        self.add_view(GiveawayView()) # Registers the baseline components

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} application slash commands successfully!")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

# --- 5. AUTOMATIC WELCOME LISTENER ---
@bot.event
async def on_member_join(member):
    config = load_config()
    guild_id = str(member.guild.id)
    if guild_id not in config:
        return
    channel_id = config[guild_id].get("welcome_channel")
    welcome_text = config[guild_id].get("welcome_message", "Welcome {member} to the server!")
    if channel_id:
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            final_message = welcome_text.replace("{member}", member.mention)
            await channel.send(final_message)

# --- 6. PARSE DURATION HELPER FUNCTION ---
def parse_duration(duration_str):
    # Matches values like 10s, 5m, 2h, 1d
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

# --- 7. BACKGROUND GIVEAWAY TASK ---
async def run_giveaway(channel, prize, duration, winners_count, embed_msg, view):
    await asyncio.sleep(duration)
    
    # Re-fetch the message to make sure it exists
    try:
        message = await channel.fetch_message(embed_msg.id)
    except discord.NotFound:
        return

    # Disable the button when time expires
    for btn in view.children:
        btn.disabled = True
    await message.edit(view=view)

    entrants_list = list(view.entrants)
    
    if not entrants_list:
        no_winner_embed = discord.Embed(
            title="🎁 GIVEAWAY ENDED 🎁",
            description=f"**Prize:** {prize}\n\n❌ No one entered the giveaway, so no winner could be chosen.",
            color=discord.Color.red()
        )
        await message.edit(embed=no_winner_embed)
        await channel.send(f"📉 The giveaway for **{prize}** ended with no entries.")
        return

    # Choose random winners up to the specified amount
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

# --- 8. SLASH COMMAND DEFINITIONS ---

# New Interactive Giveaway Slash Command
@bot.tree.command(name="giveaway", description="Start an interactive community giveaway event with buttons.")
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    prize="What item, role, or perk are you giving away?",
    duration="When does it end? Use format: 10s, 5m, 2h, or 1d",
    winners="How many random winners should be drawn?"
)
async def start_giveaway(interaction: discord.Interaction, prize: str, duration: str, winners: int):
    seconds = parse_duration(duration)
    if seconds is None:
        await interaction.response.send_message("❌ Invalid duration format! Use formats like `30s`, `10m`, `2h`, or `1d`.", ephemeral=True)
        return
    if winners < 1:
        await interaction.response.send_message("❌ You must choose at least 1 winner.", ephemeral=True)
        return

    # Create the visual dashboard embed setup
    embed = discord.Embed(
        title="🎉 NEW GIVEAWAY 🎉",
        description=f"Click the button below to enter!\n\n🎁 **Prize:** {prize}\n⏱️ **Duration:** {duration}\n👥 **Winners:** {winners}",
        color=discord.Color.purple()
    )
    embed.set_footer(text="Wither Cloud Automation")
    
    view = GiveawayView()
    await interaction.response.send_message("Initializing giveaway pipeline...", ephemeral=True)
    
    # Deploy the live card post to the channel
    embed_msg = await interaction.channel.send(embed=embed, view=view)
    
    # Spin up an isolated background loop to watch the clock run down
    asyncio.create_task(run_giveaway(interaction.channel, prize, seconds, winners, embed_msg, view))

# Purge Command
@bot.tree.command(name="purge", description="Delete a specified number of recent messages from this channel.")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge_messages(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ Please enter a message amount between 1 and 100.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Successfully cleared **{len(deleted)}** messages from this channel!", ephemeral=True)

# Ticket Setup Command
@bot.tree.command(name="ticket-setup", description="Deploy the interactive support ticket panel into this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📩 Support Help Desk",
        description="Need assistance? Click the green button below to open a private support ticket window with our server staff team.",