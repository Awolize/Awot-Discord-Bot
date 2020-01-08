import json
from datetime import datetime

import discord
from discord.ext import tasks, commands


class Presence(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # update database with info every X amount of time
        # change custom status every hour with info about the bot
        # # name=f'{len(self.bot.guilds)} Guilds'),
        # # name=f'{len(self.bot.users)} Users'),
        # # name=f"{self.bot.config.DISCORD_PREFIX}help")]

        # Store bot stats (len(connected users and guilds))
        # Store game time stats


def setup(bot):
    bot.add_cog(Presence(bot))
