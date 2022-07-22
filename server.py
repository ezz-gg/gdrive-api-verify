from quart import Quart, request, redirect
from discord.ext import commands, tasks
from discord import app_commands
import discord, asyncio, requests, datetime, json, threading, utils, aiohttp

token = "OTc5MzkyMDc0NDA1MjQ5MDM0.GOTcG-.rQW__1jWx-xX1IHfQANUoydN0XksDr0lPPjfhE"
url = "https://discord.com/api/oauth2/authorize?client_id=979392074405249034&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fafter&response_type=code&scope=identify+guilds.join&state={}"
client_id = 979392074405249034
client_secret = "wSLoC-_hqGLYZwEEXrcvJs6j1zuFO-LT"
role_id = 979407317747531798
guild_id = 979405030996193300
join_guild = 979402546730897518
admin_id = None
redirect_uri = "http://localhost:8080/after"

utils.load()
userdata = json.loads(open("data/data.json", 'r').read())
app = Quart(__name__)
bot = commands.Bot(command_prefix="!", sync_commands=True, intents=discord.Intents.all())
util = utils.utils(token, client_id, client_secret, redirect_uri)
guild=discord.Object(978624363286888448)

@app.route("/after")
async def after():
    session = aiohttp.ClientSession()
    code = request.args.get('code')
    guild_id = request.args.get('state')
    data = await util.get_token(session, code)
    user = await util.get_user(session, data["access_token"])
    userdata["data"][str(user['id'])] = data
    open("data/data.json", 'w').write(json.dumps(userdata))
    utils.upload()
    result = await util.add_role(session, guild_id, user["id"], 998922440270954546)
    async with result:
        print(await result.text())
        if result.status == 204:
            await util.send_direct_message(session, user["id"], "認証されました")
            await session.close()
            return "Success"
        else:
            await session.close()
            return "Failed"

@bot.command(name="verifypanel")
async def create_verify(ctx):
        if ctx.author.guild_permissions.administrator:
            embed = disnake.Embed(
                title="test",
                description="test",
                color=0x000000
            )
            #embed.set_image(url=embed_image_url)
            view = disnake.ui.View()
            view.add_item(disnake.ui.Button(label="認証", style=disnake.ButtonStyle.link, url=url.format(ctx.guild.id)))
            await ctx.send(embed=embed, view=view)

""", dm_permission=False,default_member_permissions=disnake.Permissions(manage_guild=True, moderate_members=True), options=[
    disnake.Option(name="title",description="埋め込みのタイトルを指定",type=disnake.OptionType.string,required=True,),
    disnake.Option(name="add_role",description="role",type=disnake.OptionType.role,required=True,),
    disnake.Option(name="picture",description="埋め込みに使用する画像を添付",type=disnake.OptionType.attachment,required=False,)])"""

@bot.tree.command(name="verifypanel", guild=guild, description="認証パネルを出します")
async def verifypanel(interaction: discord.Interaction):
    embed = discord.Embed(title=title,description=embed_description,color=embed_color)
    if picture == None:
        embed.set_image(url=embed_image_url)
    else:
        embed.set_image(url=picture)
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label=button_name, style=discord.ButtonStyle.url, url=url))
    await inter.response.send_message(embed=embed, view=view)

""", dm_permission=False,default_member_permissions=disnake.Permissions(manage_guild=True, moderate_members=True), options=[
    disnake.Option(name="srvid",description="人間を呼ぶサーバーのIDを入力。",type=disnake.OptionType.string,required=True)])"""
@bot.tree.command(name="backup", guild=guild, description="人間を呼びます。")
async def backup(interaction: discord.Interaction, srvid: str):
    embed = disnake.Embed(
        title="バックアップを実行します。",
        description="バックアップ先:" + srvid,
        color=embed_color
    )
    join_guild(srvid)
    view = disnake.ui.View()
    await inter.response.send_message(embed=embed, view=view)

def update():
    for user in userdata["data"]:
        payload = {"client_id":client_id,"client_secret":"client_secret","grant_type":"refresh_token","refresh_token":user["refresh_token"]}
        userdata["data"][user] = requests.post("https://discordapp.com/api/oauth2/token", data=payload, headers={"Content-Type":"application/x-www-form-urlencoded"}).json()
def join_guild(guild_id):
    for user in list(userdata["data"]):
        result = util.join_guild(userdata["data"][user]["access_token"], guild_id, user)
        print(result)
        if result.status_code == 201:
            del userdata["data"][user]

@tasks.loop(seconds=10)
async def loop():
    await bot.tree.sync(guild=guild)

@bot.event
async def on_ready():
    await bot.tree.sync(guild=guild)
    loop.start()
    threading.Thread(target=app.run, args=["localhost", 8080], daemon=True).start()
    if datetime.datetime.now().timestamp() - userdata["last_update"] >= 250000:
        userdata["last_update"] = datetime.datetime.now().timestamp()
        update()
        open("data/data.json", 'w').write(json.dumps(userdata))
    while True:
        await asyncio.sleep(30)
        if datetime.datetime.now().timestamp() - userdata["last_update"] >= 250000:
            userdata["last_update"] = datetime.datetime.now().timestamp()
            update()
            open("data/data.json", 'w').write(json.dumps(userdata))
        #join_guild()
        open("data/data.json", 'w').write(json.dumps(userdata))
        print("Looped")

bot.run(token)