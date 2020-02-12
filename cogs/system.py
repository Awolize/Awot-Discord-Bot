import psutil
from math import isnan
import discord
from discord.ext import commands, tasks
import matplotlib.pyplot as plt
from io import BytesIO

class System(commands.Cog):
    """
    Commands related to the bot itself, system details, etc
    """

    def __init__(self, bot):
        self.bot = bot
        self.process = bot.process
        self._ping_save.start()

    def cog_unload(self):
        self._ping_save.stop()

    @tasks.loop(minutes=1)
    async def _ping_save(self):
        latency = self.bot.latency
        if isinstance(latency, float) and not isnan(latency):
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(f'''
                    INSERT INTO 
                        pings (ping)
                    VALUES 
                        ( $1 )
                    ''', latency)

    @commands.command(name="system", aliases=["sys"])
    async def _system(self, ctx):
        """
        Display system information.
        """

        embed = discord.Embed(
            colour=discord.Color.dark_gold(),
        )

        # embed.set_author(icon_url=self.bot.user.avatar_url_as(
        #    format="png"), name=f"{self.bot.user.name}'s system stats")

        thumbnail_url = self.bot.get_user(
            self.bot.owner_id).avatar_url_as(format="png")
        url = self.bot.user.avatar_url_as(format="png")

        embed.set_author(icon_url=url,
                         name=f"{self.bot.user.name}'s system stats")
        # embed.set_thumbnail(url=self.bot.user.avatar_url_as(format="png"))
        embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name="__**System CPU:**__",
                        value=f"**Cores:** {psutil.cpu_count()}\n"
                        f"**Usage:** {psutil.cpu_percent()}%\n"
                        f"**Frequency:** {round(psutil.cpu_freq().current, -1)} Mhz")  # round to 10s
        embed.add_field(name="\u200B", value="\u200B")  # hidden field
        embed.add_field(name="__**System Memory:**__",
                        value=f"**Total:** {round(psutil.virtual_memory().total / 1073741824, 2)} GB\n"
                        f"**Used:** {round(psutil.virtual_memory().used / 1073741824, 2)} GB\n"
                        f"**Available:** {round(psutil.virtual_memory().available / 1073741824, 2)} GB")
        embed.add_field(name="__**System Disk:**__",
                        value=f"**Total:** {round(psutil.disk_usage('/').total / 1073741824, 2)} GB\n"
                        f"**Used:** {round(psutil.disk_usage('/').used / 1073741824, 2)} GB\n"
                        f"**Free:** {round(psutil.disk_usage('/').free / 1073741824, 2)} GB")
        embed.add_field(name="\u200B", value="\u200B")  # hidden field
        embed.add_field(name="__**Process information:**__",
                        value=f"**Memory usage:** {round(self.process.memory_info().rss / 1048576, 2)} mb\n"
                        f"**CPU usage:** {self.process.cpu_percent()}%\n"
                        f"**Threads:** {self.process.num_threads()}")
        await ctx.send(embed=embed)

    # TODO
    @commands.command(name="bot")
    async def _bot(self, ctx):
        '''
        Information about the bot.
        '''
        pass

    @commands.group(name='ping', invoke_without_command=True)
    async def _ping(self, ctx):
        '''
        Shows the latency of the bot.
        '''

        latency = self.bot.latency
        await ctx.send("🏓 Pong! {:.0f} ms".format(latency*1000/2))

    @_ping.command(name="graph", aliases=["g"])
    async def _ping_graph(self, ctx):
        """
        Ping history displayed in a graph
        """

        async with self.bot.db.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch("SELECT * FROM pings where t >= NOW() - '24 hours'::INTERVAL")
                #result = await conn.fetch("SELECT * FROM pings")

        plt.style.use("ggplot")

        values = []
        dates = []
        for row in result:
            values.append(row["ping"]*1000/2)
            dates.append(row["t"])

        plt.title("Ping (last 24 h)")
        plt.xlabel("Time (UTC)")
        plt.xticks(rotation=60)
        plt.ylabel("(ms)")
        plt.tight_layout(pad=2.5)
        plt.plot_date(dates, values, 'b-')

        buffer = BytesIO()
        plt.savefig(buffer, format='png', transparent=False)
        buffer.seek(0)

        plt.clf()
        plt.cla()

        await ctx.send(file=discord.File(fp=buffer, filename="Ping.png"))

    @commands.command(name="source")
    async def _source(self, ctx):
        """
        Get the github link to the repository.
        """

        await ctx.send(f"https://github.com/Awolize/Awot-Discord-Bot")

    '''    @commands.group(name='reload', hidden=True, invoke_without_command=True)
        async def _reload(self, ctx, *, module):
            """
            Reloads a module.
            """

            if ctx.author.id not in self.bot.owner_ids:
                await ctx.send("You do not have permission for this command.")
                return

            try:
                self.bot.reload_extension(f"cogs.{module.lower()}")
            except commands.ExtensionError as e:
                await ctx.send(f'{e.__class__.__name__}: {e}')
            else:
                await ctx.send('👌')

        @_reload.command(name='all', hidden=True)
        async def _reload_all(self, ctx):
            """
            Reloads all modules, while pulling from git.
            """

            if ctx.author.id not in self.bot.owner_ids:
                await ctx.send("You do not have permission for this command.")
                return

            msg = await ctx.send("Reloading all cogs...\n")
            content = msg.content + "\n"

            cogs = list(self.bot.cogs)
            successful_reloads = 0
            temp = ""
            for cog in cogs:
                cog = cog.lower()
                try:
                    self.bot.reload_extension(f"cogs.{cog}")
                    temp = f"👍 Reloaded cogs.{cog}\n"
                    successful_reloads += 1
                except commands.ExtensionError as e:
                    temp = f'{e.__class__.__name__}: {e} 👎\n'
                except Exception as e:
                    print(f"ERRRRRRRRRRORRRRRRRRRRRRRRRRRR: {e}")
                content += temp

            content += f"\nSuccessfully reloaded [ {successful_reloads} / {len(cogs)} ]"
            await msg.edit(content=content)
            if successful_reloads == len(cogs):
                await msg.add_reaction("✅")
            else:
                await msg.add_reaction("❌")

        @commands.command(hidden=True)
        async def load(self, ctx, *, module):
            """Loads a module."""
            try:
                self.bot.load_extension(f"cogs.{module.lower()}")
            except commands.ExtensionError as e:
                await ctx.send(f'{e.__class__.__name__}: {e}')
            else:
                await ctx.send('\N{OK HAND SIGN}')

        @commands.command(hidden=True)
        async def unload(self, ctx, *, module):
            """Unloads a module."""
            try:
                self.bot.unload_extension(f"cogs.{module.lower()}")
            except commands.ExtensionError as e:
                await ctx.send(f'{e.__class__.__name__}: {e}')
            else:
                await ctx.send('\N{OK HAND SIGN}')
    '''
def setup(bot):
    bot.add_cog(System(bot))
