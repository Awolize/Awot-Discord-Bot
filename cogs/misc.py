import discord
from discord.ext import commands

import subprocess
import asyncio
import sys


class Misc(commands.Cog):
    '''
    Misc: misc
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def joined(self, ctx, *, member: discord.Member):
        '''        
        Shows the date [@name] joined the server.
        '''
        print("joined()")
        await ctx.send('{} joined on {:.19}'.format(member.mention, str(member.joined_at)))

    @commands.command()
    async def ping(self, ctx):
        '''
        Shows the latency of the bot.
        '''

        latency = self.bot.latency
        await ctx.send("{:.0f} ms".format(latency*1000/2))

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @_reload.command(name='all', hidden=True)
    async def _reload_all(self, ctx):
        """Reloads all modules, while pulling from git."""

        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')

        if stdout.startswith('Already up-to-date.'):
            return await ctx.send(stdout)


def setup(bot):
    bot.add_cog(Misc(bot))
