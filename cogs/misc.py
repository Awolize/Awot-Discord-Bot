import discord
from discord.ext import commands, tasks
from asyncio import sleep
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO

import traceback
from contextlib import redirect_stdout
import textwrap

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("User.log")
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)8s - %(message)s"))
logger.addHandler(handler)


class Misc(commands.Cog):
    '''
    Misc: misc, yes very miscellaneous
    '''

    def __init__(self, bot):
        self.bot = bot
        self._user_growth_save.start()

        self._last_result = None

    def cog_unload(self):
        self._user_growth_save.stop()

    @commands.Cog.listener()
    async def on_command_error(self, ctx, e):
        print(e)
        logger.warning(f"{e}")

    @commands.Cog.listener()
    async def on_command(self, ctx):
        logger.info(f"{ctx.message.author} - {ctx.message.content}")

    @commands.command()
    async def joined(self, ctx, *, member: discord.Member):
        '''        
        Shows the date [@name] joined the server.
        '''

        await ctx.send('{} joined on {:.19}'.format(member.mention, str(member.joined_at)))

    @tasks.loop(hours=12)
    async def _user_growth_save(self):
        await self.bot.wait_until_ready()

        for guild in self.bot.guilds:
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(f'''
                    INSERT INTO 
                        server_growth (server_id, users)
                    VALUES 
                        ( $1, $2 )
                    ''', guild.id, len(guild.members))

        '''    @_user_growth_save.before_loop
    async def _before_user_growth_save(self):
        await self.bot.wait_until_ready()

        # Calc delta til 03.00
        now = datetime.utcnow().strftime('%H:%M:%S')
        delta = (datetime.strptime("03:00:00", '%H:%M:%S') -
                 datetime.strptime(now, '%H:%M:%S')).seconds

        await sleep(delta)'''

    @commands.command(name="growth")
    async def _growth(self, ctx):
        """
        Ping history displayed in a graph
        """

        try:
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.fetch('''
                        SELECT 
                            * 
                        FROM 
                            server_growth
                        WHERE 
                            server_id = $1
                    ''', ctx.guild.id)

            plt.style.use("ggplot")

            values = []
            dates = []
            for row in result:
                values.append(row["users"])
                dates.append(row["t"])

            plt.title("Member Growth")
            plt.xlabel("Time (UTC)")
            plt.xticks(rotation=60)
            plt.ylabel("Members")
            plt.tight_layout(pad=2.5)
            plt.plot_date(dates, values, 'b-')
            plt.ylim(bottom=0, top=max(values)*2)

            buffer = BytesIO()
            plt.savefig(buffer, format='png', transparent=False)
            buffer.seek(0)

            plt.clf()
            plt.cla()

            await ctx.send(file=discord.File(fp=buffer, filename="Member_Growth.png"))
        except Exception as e:
            print(e)

def embedify(text: str, len: int = 55) -> str:
    text = text[:len] + (text[len:] and '..')
    return text

def setup(bot):
    bot.add_cog(Misc(bot))