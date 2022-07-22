from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import requests, os

gauth = GoogleAuth()
scope = ["https://www.googleapis.com/auth/drive"]
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name("data/credentials.json", scope)
drive = GoogleDrive(gauth)

def upload():
    print("アップロードを実行します、Botを停止しないでください。")
    file_id = drive.ListFile({'q': 'title = "data.json"'}).GetList()[0]["id"]
    f = drive.CreateFile({'id': file_id})
    f.Delete()
    file = drive.CreateFile({"title": "data.json", "parents": [{"id": "179CRbzqyrLtzf9wnk65MdGFLL5B_s25d"}]})
    file.SetContentString(open("data/data.json","r").read())
    file.Upload()
    print("完了しました")

def load():
    file_id = drive.ListFile({'q': 'title = "data.json"'}).GetList()[0]["id"]
    f = drive.CreateFile({'id': file_id})
    f.GetContentFile('data/data.json')

class utils:
    def __init__(self, token, client_id, client_secret, redirect_uri):
        self.token = token
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
    async def get_token(self, session, code):
        data = await session.post("https://discordapp.com/api/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": code,
                "grant_type": "authorization_code"},
            headers={"content-type": "application/x-www-form-urlencoded"})
        return await data.json()
    async def get_user(self, session, access_token):
        data = await session.get("https://discordapp.com/api/users/@me", headers={"Authorization":"Bearer {}".format(access_token)})
        return await data.json()
    async def add_role(self, session, guild_id, user_id, role_id):
        data = await session.put("https://discord.com/api/v9/guilds/{}/members/{}/roles/{}".format(guild_id, user_id, role_id),
            headers={"authorization": f"Bot {self.token}"})
        return data
    async def join_guild(self, session, access_token, guild_id, user_id):
        data = await session.put("https://discord.com/api/v9/guilds/{}/members/{}".format(guild_id, user_id),
                              headers={"Content-Type": "application/json", "Authorization": f"Bot {self.token}"},
                              json={"access_token": access_token})
        return await data.json()
    async def send_direct_message(self, session, user_id, content):
        dmid = await session.post("https://discord.com/api/users/@me/channels", headers={"Authorization": f"Bot {self.token}"},
            json={"recipient_id": user_id})
        dmid = (await dmid.json())["id"]
        data = await session.post(f"https://discord.com/api/channels/{dmid}/messages",
            headers={"Authorization": f"Bot {self.token}"}, json={"content": "", "embeds": [{"title": content}]})
        return await data.json()