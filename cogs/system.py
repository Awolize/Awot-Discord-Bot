import psutil

import discord
from discord.ext import commands


class System(commands.Cog):
    """
    Get system information about the system the bot is running on.
    """

    def __init__(self, bot):
        self.bot = bot
        self.process = bot.process

    @commands.command(name="system", aliases=["sys"])
    async def system(self, ctx):
        """
        Display system information
        """

        embed = discord.Embed(
            colour=discord.Color.dark_gold(),
        )

        # embed.set_author(icon_url=self.bot.user.avatar_url_as(
        #    format="png"), name=f"{self.bot.user.name}'s system stats")

        thumbnail_url = self.bot.get_user(
            self.bot.owner).avatar_url_as(format="png")
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


def setup(bot):
    bot.add_cog(System(bot))
