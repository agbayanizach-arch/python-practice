import os
import json
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

# --- 2. CONFIGURATION HELPER FUNCTIONS (JSON STORE) ---
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

# --- 3. PERSISTENT TICKET VIEWS (FROM PREVIOUS STEP) ---
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
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

# --- 4. CORE BOT INITIALIZATION ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(TicketControls())
        self.add_view(TicketCloseControl())

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
            # Replace placeholder token with actual member mention dynamically
            final_message = welcome_text.replace("{member}", member.mention)
            await channel.send(final_message)

# --- 6. SLASH COMMAND DEFINITIONS ---

# Ticket Command
@bot.tree.command(name="ticket-setup", description="Deploy the interactive support ticket panel into this channel.")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📩 Support Help Desk",
        description="Need assistance? Click the green button below to open a private support ticket window with our server staff team.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Wither Cloud Ticket System")
    view = TicketControls()
    await interaction.response.send_message("Deploying ticket dashboard...", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)

# 1. Custom Welcome Message Configuration Command
@bot.tree.command(name="customwelcome", description="Set the template text for greeting new users. Use '{member}' as a placement tag.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(message="The message to display. Example: Welcome {member} to our awesome gaming server!")
async def custom_welcome(interaction: discord.Interaction, message: str):
    config = load_config()
    guild_id = str(interaction.guild_id)
    
    if guild_id not in config:
        config[guild_id] = {}
        
    config[guild_id]["welcome_message"] = message
    save_config(config)
    
    await interaction.response.send_message(f"✅ **Welcome message updated!**\nPreview template:\n> {message}", ephemeral=True)

# 2. Welcome Channel Destination Setup Command
@bot.tree.command(name="channel_set", description="Assign which target text channel your welcome greeting card will drop into.")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(channel="The target text channel.")
async def channel_set(interaction: discord.Interaction, channel: discord.TextChannel):
    config = load_config()
    guild_id = str(interaction.guild_id)
    
    if guild_id not in config:
        config[guild_id] = {}
        
    config[guild_id]["welcome_channel"] = str(channel.id)
    save_config(config)
    
    await interaction.response.send_message(f"✅ **Success!** Welcome alerts will now target: {channel.mention}", ephemeral=True)

# 3. Greet System Diagnostics Verification Command
@bot.tree.command(name="greettest", description="Simulate a new member join entry event to test your greeting pipeline layouts.")
@app_commands.checks.has_permissions(administrator=True)
async def greet_test(interaction: discord.Interaction):
    config = load_config()
    guild_id = str(interaction.guild_id)
    
    if guild_id not in config or "welcome_channel" not in config[guild_id]:
        await interaction.response.send_message("❌ **Configuration Missing!** Please bind a target channel first using `/channel_set`.", ephemeral=True)
        return
        
    channel_id = config[guild_id].get("welcome_channel")
    welcome_text = config[guild_id].get("welcome_message", "Welcome {member} to the server!")
    
    channel = interaction.guild.get_channel(int(channel_id))
    if not channel:
        await interaction.response.send_message("❌ **Target Channel Not Found!** Reconfigure your target endpoint destination with `/channel_set`.", ephemeral=True)
        return
        
    final_message = welcome_text.replace("{member}", interaction.user.mention)
    
    await interaction.response.send_message("🧪 Executing welcome workflow test trigger pipeline simulation...", ephemeral=True)
    await channel.send(f"⚠️ **[GREET SIMULATION TEST]**\n{final_message}")

# Running step
TOKEN = os.environ.get("DISCORD_TOKEN")
bot.run(TOKEN)