from distutils.command.config import config
import json
from typing import TypedDict

API_START_POINT = "https://discord.com/api/v10"
DATA_PATH = "data/data.json"

def write_userdata(userdata: str):
    json.loads(userdata)
    jf = open(DATA_PATH, "w")
    jf.write(userdata)
    jf.close()