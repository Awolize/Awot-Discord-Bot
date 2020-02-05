from datetime import datetime
import time
import asyncio
import asyncpg
import discord
from discord.ext import tasks, commands

import database_handler as dbh


class Birthday(commands.Cog):
    '''
    Date: Handles Birthdays
    '''

    def __init__(self, bot):
        try:
            self.bot = bot
            self.print_birthday.start()
            self.BIRTHDAY_PRINT_TIME = bot.config.BIRTHDAY_PRINT_TIME
        except Exception as e:
            print(f"[Error] - [Birthday] - [init] - {e}.")

    def cog_unload(self):
        self.print_birthday.stop()

    # Rewrite
    @tasks.loop(hours=24)
    async def print_birthday(self):
        # channel = self.bot.get_channel(channel_id)
        print("printbday")
        print(datetime.now())

        for server in self.bot.guilds:

            result = await self.bot.db.get_birthday(server.id)
            print(result)
            return

            dates = []
            for row in result:
                print(row)
                dates.append((row[0], f"{row[1]}"))

            currentYear = datetime.now().year
            for memberID, memberInfo in dates:

                member = bot.get_user(memberID)
                birth_day, birth_month, birth_year = memberInfo.split("-")
                age = currentYear - int(birth_year)

                channel = server.text_channels[0]

                if birth_year == 0:  # member does not want to display the birth year
                    msg = await channel.send(f"Happy birthday {member.mention}!!")
                else:
                    ordinal = "th"
                    if age > 10 and age < 20:
                        ordinal = "th"
                    elif age % 10 == 1:
                        ordinal = "st"
                    elif age % 10 == 2:
                        ordinal = "nd"
                    elif age % 10 == 3:
                        ordinal = "rd"

                    msg = await channel.send(f"Happy {age}{ordinal} birthday {member.mention}!!")

    @print_birthday.before_loop
    async def before_print_birthday(self):
        await self.bot.wait_until_ready()

        # Calc delta til next BIRTHDAY_PRINT_TIME
        now = time.strftime('%H:%M:%S')
        delta = (datetime.strptime(self.BIRTHDAY_PRINT_TIME, '%H:%M:%S') -
                 datetime.strptime(now, '%H:%M:%S')).seconds

        # sleep until BIRTHDAY_PRINT_TIME
        await asyncio.sleep(delta)

    @commands.command(name="bday", aliases=["getBirthday", "getbday"])
    async def _bday(self, ctx, member: discord.Member = None):
        '''
        Shows birthday of a specific member.
        '''

        if not member:
            member = ctx.author

        date = await self.bot.db.get_birthday_by_id(
            member.id, ctx.message.guild.id)

        if not date:
            await ctx.send(f"No birthday found for {member.name}.")
            return

        if date.year < 1900:
            await ctx.send(f"{member.mention}'s birthday is on the {date.day}/{date.month}.")
        else:
            await ctx.send(f"{member.mention}'s birthday: {date}.")

    @_bday.error
    async def _bday_error(self, ctx, error):
        await ctx.send(f"[Error] - [Birthday] - [bday] - {error}.")

    @commands.command(name="setbday", aliases=["setBirthday"])
    async def _setbday(self, ctx, date: str, member: discord.Member = None):
        '''
        Format [yyyy-mm-dd]. Add birthday to the database. Only Admins can add others birthdays. 

        If you do not want to display your birthyear; enter a year less than 1900.
        '''
        if member is None:
            member = ctx.author
        else:
            isAdmin = ctx.author.guild_permissions.administrator
            if not isAdmin:
                await ctx.send(
                    f"You, {ctx.author.name}, are **not** an admin, "
                    f"you may **not** add {member.name}'s birthday.")
                return

        year = date.split("-")[0]
        month = date.split("-")[1]
        day = date.split("-")[2]

        if int(year) < 1900:
            year = "1000"

        date = datetime.strptime(f'{year}-{month}-{day}', "%Y-%m-%d")

        try:
            result = await self.bot.db.set_birthday(member.id, ctx.guild.id, date)
            if type(result) == asyncpg.exceptions.ForeignKeyViolationError:
                await self.bot.db.add_user(member.id)
                await self.bot.db.set_birthday(member.id, ctx.guild.id, date)
            msg = await ctx.send(f"{member.name}'s birthday has been set.")
        except Exception as e:
            msg = await ctx.send(f"Error setting {member.name}'s birthday. Already set or wrong input")

    @_setbday.error
    async def _setbday_error(self, ctx, error):
        await ctx.send(f"[Error] - [Birthday] - [set_birthday] - {error}.")

    @commands.command(name="removebday", aliases=["removeBirthday"])
    async def _removebday(self, ctx, member: discord.Member = None):
        '''
        Removes birthday from a member. (Only Admins can remove others bdays. You can remove your own one.)
        '''

        if member is None:
            member = ctx.author
        else:
            isAdmin = ctx.author.guild_permissions.administrator

            if member != ctx.author and not isAdmin:
                await ctx.send("You do not have permissions to do that.")
                return
        try:
            result = await self.bot.db.remove_birthday(member.id, ctx.message.guild.id)
            await ctx.send(f"Birthday removed. [{result}]")
        except Exception as e:
            await ctx.send(f"Error removing birthday. [{result}]")
            print(f'Error in remove birthday: {e}')

def setup(bot):
    bot.add_cog(Birthday(bot))