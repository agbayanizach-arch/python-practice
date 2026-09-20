import discord
from datetime import datetime, timezone

class EmbedBuilder:
    @staticmethod
    def build_result_embed(data):
        if not data.get("success"):
            return discord.Embed(
                title="❌ Error",
                description=data.get("message", "Unknown Error"),
                color=0xFF0000
            )

        hypixel_stats = data.get("hypixel", {})
        donut_status = data.get("donut", {})
        
        is_banned = False
        is_unbanned = False
        
        if donut_status.get("status") == "Banned": is_banned = True
        elif donut_status.get("status") == "Unbanned": is_unbanned = True
        
        hypixel_ban = data.get("hypixel_ban", {})
        if hypixel_ban.get("status") == "Banned": 
            is_banned = True
        elif hypixel_ban.get("status") == "Clean":
            if not is_banned: is_unbanned = True
        
        if is_banned: color = 0xFF0000
        elif is_unbanned: color = 0x00FF00
        else: color = 0xFFFF00

        embed = discord.Embed(color=color)
        
        embed.set_author(name="MaceCloud Checker", icon_url="https://i.postimg.cc/Xvh32RQr/IMG-20260129-110839.jpg")
        
        embed.add_field(name="<:mmail:1430291754459856946> Eᴍᴀɪʟ", value=f"||`{data['email']}`||", inline=True)
        embed.add_field(name="<:keiy:1430291766590050304> Pᴀѕѕᴡᴏʀᴅ", value=f"||`{data['password']}`||", inline=True)
        embed.add_field(name="<:name_tag:1430291758893498460> Uѕᴇʀɴᴀᴍᴇ", value=f"`{data.get('username', 'N/A')}`", inline=True)
        embed.add_field(name="<:brok:1430291739272417353> Aᴄᴄᴏᴜɴᴛ Tʏᴘᴇ", value=f"`{data['type']}`", inline=True)
        
        if hypixel_stats.get('level'): embed.add_field(name="<:hypixel:1430291770012340246> Hʏᴘɪxᴇʟ Lᴇᴠᴇʟ", value=hypixel_stats['level'], inline=True)
        if hypixel_stats.get('rank'): embed.add_field(name="<:hypixel:1430291770012340246> Hʏᴘɪxᴇʟ Rᴀɴᴋ", value=hypixel_stats['rank'], inline=True)
        if hypixel_stats.get('first_login'): embed.add_field(name="<:hypixel:1430291770012340246> Fɪʀѕᴛ Lᴏɢɪɴ", value=hypixel_stats['first_login'], inline=True)
        if hypixel_stats.get('last_login'): embed.add_field(name="<:hypixel:1430291770012340246> Lᴀѕᴛ Lᴏɢɪɴ", value=hypixel_stats['last_login'], inline=True)
        if hypixel_stats.get('bw_stars'): embed.add_field(name="<:hypixel:1430291770012340246> Bᴇᴅᴡᴀʀѕ Sᴛᴀʀѕ", value=hypixel_stats['bw_stars'], inline=True)
        if hypixel_stats.get('sb_coins'): embed.add_field(name="<:hypixel:1430291770012340246> Sᴋʏʙʟᴏᴄᴋ Cᴏɪɴѕ", value=hypixel_stats['sb_coins'], inline=True)
        
        if hypixel_ban:
            h_emoji = "<a:unbanned:1430296212015419484>" if hypixel_ban.get('status') == "Clean" else "<a:banned:1430293755155448014>"
            ban_text = f"{h_emoji} {hypixel_ban.get('status', 'Unknown')}"
            if hypixel_ban.get('reason'):
                ban_text += f" ({hypixel_ban['reason']})"
            embed.add_field(name="<:hypixel:1430291770012340246> Hʏᴘɪxᴇʟ Bᴀɴ", value=ban_text, inline=True)

        capes = data.get('capes', [])
        if capes: embed.add_field(name="<:cape:1430291744934592612> Cᴀᴘᴇѕ", value=", ".join(capes), inline=True)
        
        if donut_status.get('status') != "Unknown":
            d_emoji = "<a:unbanned:1430296212015419484>" if donut_status['status'] == "Unbanned" else "<a:banned:1430293755155448014>"
            embed.add_field(name="<a:donut:1430291763641188372> Dᴏɴᴜᴛ Sᴛᴀᴛᴜѕ", value=f"{d_emoji} {donut_status['status']}", inline=True)
            
            if donut_status.get('money'): embed.add_field(name="<a:donut:1430291763641188372> Mᴏɴᴇʏ", value=donut_status['money'], inline=True)
            if donut_status.get('playtime'): embed.add_field(name="<a:donut:1430291763641188372> Pʟᴀʏᴛɪᴍᴇ", value=donut_status['playtime'], inline=True)
            if donut_status.get('reason'): embed.add_field(name="<a:donut:1430291763641188372> Bᴀɴ Rᴇᴀѕᴏɴ", value=donut_status['reason'], inline=True)

        embed.add_field(name="<:combo:1430291747912548454> Cᴏᴍʙᴏ", value=f"||```{data['email']}:{data['password']}```||", inline=False)
        
        embed.set_footer(text="MaceCloud Checker • Made by RahulxD", icon_url="https://i.postimg.cc/Xvh32RQr/IMG-20260129-110839.jpg")
        embed.timestamp = datetime.now(timezone.utc)
        
        if data.get('username') and data['username'] != "N/A":
            embed.set_thumbnail(url=f"https://mc-heads.net/body/{data['username']}")
        else:
            embed.set_thumbnail(url="https://mc-heads.net/body/steve")
            
        return embed

    @staticmethod
    def build_status_embed(stats):
        embed = discord.Embed(
            title="<a:loading:1434520216028577885> MaceCloud Checker Live Status",
            color=0x00FFFF
        )
        
        embed.add_field(name="<a:rght:1434491384370434168> Checked", value=f"`{stats['checked']}/{stats['total']}`", inline=True)
        embed.add_field(name="<:combo:1430291747912548454> Hits", value=f"`{stats['hits']}`", inline=True)
        embed.add_field(name="<a:unbanned:1430296212015419484> Unbanned", value=f"`{stats['unbanned']}`", inline=True)
        embed.add_field(name="<a:banned:1430293755155448014> Banned", value=f"`{stats['banned']}`", inline=True)
        embed.add_field(name="<:brok:1430291739272417353> Free/Bad", value=f"`{stats['bad']}`", inline=True)
        
        progress = int((stats['checked'] / stats['total']) * 10) if stats['total'] > 0 else 0
        bar = "🟩" * progress + "⬜" * (10 - progress)
        embed.add_field(name="Progress", value=f"`{bar}` {int((stats['checked'] / stats['total']) * 100) if stats['total'] > 0 else 0}%", inline=False)
        
        embed.set_footer(text="MaceCloud Checker • Made by RahulxD", icon_url="https://i.postimg.cc/Xvh32RQr/IMG-20260129-110839.jpg")
        embed.timestamp = datetime.now(timezone.utc)
        return embed
