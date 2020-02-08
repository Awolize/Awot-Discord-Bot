import json
from datetime import datetime

import discord
from discord.ext import tasks, commands


class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.presence_list_index = 0    
        self.change_presence.start()

    def cog_unload(self):
        self.change_presence.stop()

    @commands.Cog.listener()
    async def on_ready(self):
        activity = discord.Activity(
            name=f'{len(self.bot.users)} Users on {len(self.bot.guilds)} Servers',
            type=discord.ActivityType.watching)
        await self.bot.change_presence(activity=activity)

    @tasks.loop(minutes=11)
    async def change_presence(self):
        await self.bot.wait_until_ready()

        presence_list = [
            [f'{len(self.bot.users)} Users on {len(self.bot.guilds)} Servers', discord.ActivityType.watching],
            [f'Awot for: {str((datetime.now() - self.bot.start_time))[:-7]}', discord.ActivityType.playing]
        ]

        curr = presence_list[self.presence_list_index]

        activity = discord.Activity(name=curr[0], type=curr[1])
        await self.bot.change_presence(activity=activity)

        self.presence_list_index += 1
        if self.presence_list_index > (len(presence_list)-1):
            self.presence_list_index = 0

def setup(bot):
    bot.add_cog(Presence(bot))
