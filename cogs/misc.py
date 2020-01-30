import discord
from discord.ext import commands
import asyncio

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("user.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)8s - %(message)s"))
logger.addHandler(handler)


class Misc(commands.Cog):
    '''
    Misc: misc, yes very miscellaneous
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        logger.warning(f"{e}")
        pass

    @commands.Cog.listener()
    async def on_command(self, ctx):
        logger.info(f"{ctx.message.author} - {ctx.message.content}")
        pass

    @commands.command()
    async def joined(self, ctx, *, member: discord.Member):
        '''        
        Shows the date [@name] joined the server.
        '''
        
        await ctx.send('{} joined on {:.19}'.format(member.mention, str(member.joined_at)))

    @commands.command()
    async def ping(self, ctx):
        '''
        Shows the latency of the bot.
        '''

        latency = self.bot.latency
        await ctx.send("{:.0f} ms".format(latency*1000/2))

    @commands.command(name="source")
    async def source(self, ctx):
        """
        Get the github link to the repository.
        """

        await ctx.send(f"<https://github.com/Awolize/Awot-Discord-Bot>")

    @commands.group(name='reload', hidden=True, invoke_without_command=True)
    async def _reload(self, ctx, *, module):
        """Reloads a module."""
        try:
            self.bot.reload_extension(f"cogs.{module.lower()}")
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send('👌')

    @_reload.command(name='all', hidden=True)
    async def _reload_all(self, ctx):
        """Reloads all modules, while pulling from git."""

        msg = await ctx.send("Reloading all cogs...\n")
        content = msg.content + "\n"

        cogs = list(self.bot.cogs)
        successfull_reloads = 0
        for cog in cogs:
            cog = cog.lower()
            try:
                self.bot.reload_extension(f"cogs.{cog}")
                temp = f"👍 Reloaded cogs.{cog}\n"
                successfull_reloads += 1
            except commands.ExtensionError as e:
                temp = f'{e.__class__.__name__}: {e} 👎\n'
            except Exception as e:
                print(f"ERRRRRRRRRRORRRRRRRRRRRRRRRRRR: {e}")
            content += temp
                
        content += f"\nSuccessfully reloaded [ {successfull_reloads} / {len(cogs)} ]"
        await msg.edit(content=content)
        if successfull_reloads == len(cogs):
            await msg.add_reaction("✅")
        else:
            await msg.add_reaction("❌")

def setup(bot):
    bot.add_cog(Misc(bot))
