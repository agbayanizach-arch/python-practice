# Add this import at the top
from keep_alive import keep_alive

# ... keep the rest of your code ...

if __name__ == "__main__":
    if TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your Discord Bot Token!")
        # Note: input() will crash on Render, so we will use Environment Variables instead
        import os
        TOKEN = os.environ.get("DISCORD_TOKEN")
         
    if not TOKEN:
         print("Exiting...")
         sys.exit(1)
         
    try:
        keep_alive() # <--- CALL THIS HERE to start the web server
        client.run(TOKEN)
    except Exception as e:
        print(f"❌ Error running bot: {e}")
