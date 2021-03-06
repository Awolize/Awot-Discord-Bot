import asyncio
import time
import json
import os
import psutil
import asyncpg
from datetime import datetime

import discord
from discord.ext import commands

import database_handler as dbh
import config

INIT_EXTENSIONS = [
    "cogs.admin",
    "cogs.birthday",
    "cogs.help",
    "cogs.misc",
    "cogs.presence",
    "cogs.stats",
    "cogs.system",    
]

DESCRIPTION = "Awot 😎"


class Awot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(config.DISCORD_PREFIX),
            description=DESCRIPTION,
            reconnect=True,
        )
        self.process = psutil.Process(os.getpid())
        self.start_time = datetime.now()
        self.config = config
        self.owner_id = 133309367297507329
        self.owner_ids = [133309367297507329]

        self.db = dbh.Database()

        for extension in INIT_EXTENSIONS:
            try:
                self.load_extension(extension)
                print(f"[init] - Successfully loaded: {extension}")
            except Exception as e:
                print(f"[init] - Failed to load: {extension}")
                print(f"[Error] - {e}")

    def run(self):
        try:
            super().run(config.DISCORD_TOKEN, reconnect=True)
        except Exception as e:
            print(f'[Error] [run] {e}')

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        db = dbh.Database()
        pool = loop.run_until_complete(db.init())

        bot = Awot()
        bot.db = db
        bot.run()
    except Exception as e:
        print(e)
