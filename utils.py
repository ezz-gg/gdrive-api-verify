from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import asyncio, json, re
from datetime import datetime

gauth = GoogleAuth()
scope = ["https://www.googleapis.com/auth/drive"]
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name("data/credentials.json", scope)
drive = GoogleDrive(gauth)

class FileManager:
    def __init__(self, data, backup):
        match = r"https://drive.google.com/file/d/([a-zA-Z0-9-]+)/"
        self.data_id = re.match(match, data).group(1)
        self.backup_id = re.match(match, backup).group(1)
        self.upload = False
    def save(self, datas):
        data = json.dumps(datas)
        open("data/data.json", 'w').write(data)
        print("[+] アップロードを実行します、Botを停止しないでください。")
        file = drive.CreateFile({'id': self.data_id})
        if not file:
            print("[!] URLが無効かファイルが存在しません")
            return
        else:
            file.SetContentString(data)
            file.Upload()
            self.backup(data)
        print("[+] 完了しました")
    def backup(self, data):
        file = drive.CreateFile({'id': self.backup_id})
        file.SetContentString(data)
        file.Upload()
    def load_file(self):
        print("[+] ファイルをGoogleドライブから読み込んでいます")
        f = drive.CreateFile({'id': self.data_id})
        data = f.GetContentString()
        print("[+] 読み込みました")
        if not data:
            self.load_backup()
        try:
            json.loads(data)
            open("data/data.json", "w").write(data)
        except:
            self.load_backup()
    def load_backup(self):
        print("[!] ファイルの中身がない、または破損しているためバックアップを読み込んでいます")
        f = drive.CreateFile({'id': self.backup_id})
        data = f.GetContentString()
        print("[+] バックアップを読み込みました")
        if not data:
            raise Exception
        try:
            json.loads(data)
            open("data/data.json", "w").write(data)
        except:
            raise Exception


class utils:
    def __init__(self, token, client_id, client_secret, redirect_uri):
        self.token = token
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.pause = False
    async def update_token(self, session, data):
        for user in data["users"]:
            if datetime.utcnow().timestamp() - data["users"][user]["last_update"] >= 300000:
                payload = {"client_id": self.client_id, "client_secret": self.client_secret, "grant_type": "refresh_token", "refresh_token": user["refresh_token"]}
                while self.pause:
                    await asyncio.sleep(1)
                while True:
                    temp = await session.post("https://discordapp.com/api/oauth2/token", data=payload,headers={"Content-Type": "application/x-www-form-urlencoded"})
                    data = await temp.json()
                    if 'message' in data:
                        if data['message'] == 'You are being rate limited.':
                            print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                            await asyncio.sleep(data["retry_after"])
                    else:
                        break
                userdata["data"][user] = data
                userdata["last_update"] = datetime.utcnow().timestamp()
        return data
    async def get_token(self, session, code):
        while True:
            temp = await session.post("https://discordapp.com/api/oauth2/token",
                                      data={
                                          "client_id": self.client_id,
                                          "client_secret": self.client_secret,
                                          "redirect_uri": self.redirect_uri,
                                          "code": code,
                                          "grant_type": "authorization_code"},
                                      headers={"content-type": "application/x-www-form-urlencoded"})
            data = await temp.json()
            if 'message' in data:
                if data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                    await asyncio.sleep(data["retry_after"])
            else:
                return data
    async def get_user(self, session, access_token):
        while True:
            temp = await session.get("https://discordapp.com/api/users/@me", headers={"Authorization":"Bearer {}".format(access_token)})
            data = await temp.json()
            if 'message' in data:
                if data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                    await asyncio.sleep(data["retry_after"])
            else:
                return data
    async def add_role(self, session, guild_id, user_id, role_id):
        while True:
            temp = await session.put(
                "https://discord.com/api/v9/guilds/{}/members/{}/roles/{}".format(guild_id, user_id, role_id),
                headers={"authorization": f"Bot {self.token}"})
            try:
                data = await temp.json()
                if 'message' in data:
                    if data['message'] == 'You are being rate limited.':
                        print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                        await asyncio.sleep(data["retry_after"])
                    else:
                        return "Unknown Error"
                else:
                    return "Already Added"
            except:
                return "Success"
    async def join_guild(self, session, access_token, guild_id, user_id):
        while True:
            temp = await session.put("https://discord.com/api/v9/guilds/{}/members/{}".format(guild_id, user_id),
                                     headers={"Content-Type": "application/json", "Authorization": f"Bot {self.token}"},
                                     json={"access_token": access_token})
            try:
                data = await temp.json()
                if 'message' in data:
                    if data['message'] == 'You are being rate limited.':
                        print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                        await asyncio.sleep(data["retry_after"])
                    else:
                        return "Unknown Error"
                else:
                    return "Already Joined"
            except:
                return "Success"
    async def send_direct_message(self, session, user_id, content):
        while True:
            temp = await session.post("https://discord.com/api/users/@me/channels",
                                      headers={"Authorization": f"Bot {self.token}"},
                                      json={"recipient_id": user_id})
            data = await temp.json()
            if 'message' in data:
                if data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                    await asyncio.sleep(data["retry_after"])
            else:
                break
        dmid = data["id"]
        while True:
            temp = await session.post(f"https://discord.com/api/channels/{dmid}/messages",
            headers={"Authorization": f"Bot {self.token}"}, json={"content": "", "embeds": [{"title": content}]})
            data = await temp.json()
            if 'message' in data:
                if data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(data["retry_after"]))
                    await asyncio.sleep(data["retry_after"])
            else:
                return data
