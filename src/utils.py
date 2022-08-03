from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import json
import re
from datetime import datetime
from lib import API_START_POINT_V10, write_userdata
from dotenv import load_dotenv
import os

load_dotenv()
if not os.path.isfile("data/credentials.json"):
    gdrive_dredentials = os.getenv('GDRIVE_CREDENTIALS')
    if not gdrive_dredentials:
        raise Exception("[!] GDRIVE_CREDENTIALSが設定されていません")
    print("[+] GDRIVE_CREDENTIALSがないので環境変数から書き込みます")
    with open("data/credentials.json", 'w') as f:
        f.write(gdrive_dredentials)
    print("[+] 書き込みが完了しました")

gauth = GoogleAuth()
scope = "https://www.googleapis.com/auth/drive"
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
    "data/credentials.json", scope)
drive = GoogleDrive(gauth)


class FileManager:
    def __init__(self, data, backup):
        match = r"https://drive.google.com/file/d/([a-zA-Z0-9-_]+)/.*"
        self.data_id = re.match(match, data).group(1)
        self.backup_id = re.match(match, backup).group(1)
        self.upload = False

    def save(self, data):
        plain_data = json.dumps(data)
        open("data/data.json", 'w').write(plain_data)
        print("[+] アップロードを実行します、Botを停止しないでください。")
        file = drive.CreateFile({'id': self.data_id})
        if not file:
            print("[!] URLが無効かファイルが存在しません")
            return
        else:
            file.SetContentString(plain_data)
            file.Upload()
            self.backup(plain_data)
        print("[+] 完了しました")

    def backup(self, plain_data):
        file = drive.CreateFile({'id': self.backup_id})
        file.SetContentString(plain_data)
        file.Upload()

    def load_file(self):
        print("[+] ファイルをGoogleドライブから読み込んでいます")
        f = drive.CreateFile({'id': self.data_id})
        plain_data = f.GetContentString()
        print("[+] 読み込みました")
        if not plain_data:
            self.load_backup()
        try:
            write_userdata(plain_data)
        except:
            self.load_backup()

    def load_backup(self):
        print("[!] ファイルの中身がない、または破損しているためバックアップを読み込んでいます")
        f = drive.CreateFile({'id': self.backup_id})
        plain_data = f.GetContentString()
        print("[+] バックアップを読み込みました")
        if not plain_data:
            raise Exception
        try:
            write_userdata(plain_data)
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
        res_data = None
        for user in data["users"]:
            post_headers = {
                "Content-Type": "application/x-www-form-urlencoded"}
            post_data = {"client_id": self.client_id, "client_secret": self.client_secret,
                         "grant_type": "refresh_token", "refresh_token": data["users"][user]["refresh_token"]}
            endpoint = f"{API_START_POINT_V10}/oauth2/token"
            if datetime.utcnow().timestamp() - data["users"][user]["last_update"] >= 300000:
                while self.pause:
                    await asyncio.sleep(1)
                while True:
                    temp = await session.post(endpoint, data=post_data, headers=post_headers)
                    res_data = await temp.json()
                    if 'message' in res_data:
                        if res_data['message'] == 'You are being rate limited.':
                            print("[!] Rate Limited. Sleeping {}s".format(
                                res_data["retry_after"]))
                            await asyncio.sleep(res_data["retry_after"])
                    else:
                        break
        return res_data

    async def get_token(self, session, code):
        post_headers = {"content-type": "application/x-www-form-urlencoded"}
        post_data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": code,
            "grant_type": "authorization_code"}
        endpoint = f"{API_START_POINT_V10}/oauth2/token"
        while True:
            temp = await session.post(endpoint, data=post_data, headers=post_headers)
            res_data = await temp.json()
            if 'message' in res_data:
                if res_data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(
                        res_data["retry_after"]))
                    await asyncio.sleep(res_data["retry_after"])
            else:
                return res_data

    async def get_user(self, session, access_token):
        endpoint = f"{API_START_POINT_V10}/users/@me"
        get_headers = {"Authorization": f"Bearer {access_token}"}
        while True:
            temp = await session.get(endpoint, headers=get_headers)
            res_data = await temp.json()
            if 'message' in res_data:
                if res_data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(
                        res_data["retry_after"]))
                    await asyncio.sleep(res_data["retry_after"])
            else:
                return res_data

    async def add_role(self, session, guild_id, user_id, role_id):
        endpoint = "{}/guilds/{}/members/{}/roles/{}".format(
            API_START_POINT_V10, guild_id, user_id, role_id)
        put_headers = {"authorization": f"Bot {self.token}"}
        while True:
            temp = await session.put(endpoint, headers=put_headers)
            try:
                res_data = await temp.json()
                if 'message' in res_data:
                    if res_data['message'] == 'You are being rate limited.':
                        print("[!] Rate Limited. Sleeping {}s".format(
                            res_data["retry_after"]))
                        await asyncio.sleep(res_data["retry_after"])
                    else:
                        return "Unknown Error"
                else:
                    return "Already Added"
            except:
                return "Success"

    async def join_guild(self, session, access_token, guild_id, user_id):
        endpoint = "{}/guilds/{}/members/{}".format(
            API_START_POINT_V10, guild_id, user_id)
        put_headers = {"Content-Type": "application/json",
                       "Authorization": f"Bot {self.token}"}
        put_data = {"access_token": access_token}
        while True:
            temp = await session.put(endpoint, headers=put_headers, json=put_data)
            try:
                res_data = await temp.json()
                if 'message' in res_data:
                    if res_data['message'] == 'You are being rate limited.':
                        print("[!] Rate Limited. Sleeping {}s".format(
                            res_data["retry_after"]))
                        await asyncio.sleep(res_data["retry_after"])
                    else:
                        return "Unknown Error"
                else:
                    return "Already Joined"
            except:
                return "Success"

    async def send_direct_message(self, session, user_id, content):
        endpoint = f"{API_START_POINT_V10}/users/@me/channels"
        post_header = {"Authorization": f"Bot {self.token}"}
        post_data = {"recipient_id": user_id}
        res_data = None
        while True:
            temp = await session.post(endpoint, headers=post_header, json=post_data)
            res_data = await temp.json()
            if 'message' in res_data:
                if res_data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(
                        res_data["retry_after"]))
                    await asyncio.sleep(res_data["retry_after"])
            else:
                break
        dmid = res_data["id"]
        while True:
            endpoint = f"{API_START_POINT_V10}/channels/{dmid}/messages"
            post_header = {"Authorization": f"Bot {self.token}"}
            post_data = {"content": "", "embeds": [{"title": content}]}
            temp = await session.post(endpoint, headers=post_header, json=post_data)
            res_data = await temp.json()
            if 'message' in res_data:
                if res_data['message'] == 'You are being rate limited.':
                    print("[!] Rate Limited. Sleeping {}s".format(
                        res_data["retry_after"]))
                    await asyncio.sleep(res_data["retry_after"])
            else:
                return res_data
