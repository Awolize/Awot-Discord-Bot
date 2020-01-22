import json
from datetime import datetime

import discord
from discord.ext import tasks, commands


class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_presence.start()
        self.presence_list_index = 0
        self.presence_list = [
            f'{len(self.bot.users)} Users on {len(self.bot.guilds)} Servers', "Hello 😎"
        ]
    
    def cog_unload(self):
        self.change_presence.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        activity = discord.Activity(
            name=f'{len(self.bot.users)} Users on {len(self.bot.guilds)} Servers',
            type=discord.ActivityType.watching)
        await self.bot.change_presence(activity=activity)

        # update database with info every X amount of time
        # change custom status every hour with info about the bot
        # # name=,
        # # name=,
        # # name=]

        # Store bot stats (len(connected users and guilds))
        # Store game time stats

    @tasks.loop(minutes=10)
    async def change_presence(self):
        await bot.wait_until_ready()
        activity = discord.Activity(
            name=self.presence_list[self.presence_list_index], 
            type=discord.ActivityType.watching)
        await self.bot.change_presence(activity=activity)

        self.presence_list_index += 1
        if self.presence_list_index > (len(self.presence_list)-1):
            self.presence_list_index = 0


def setup(bot):
    bot.add_cog(Presence(bot))
