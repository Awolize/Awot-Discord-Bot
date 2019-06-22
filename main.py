import discord
from discord.ext import commands
import databaseHandler as dbh
import asyncio

import time
import datetime
import json

import privateData

'''

Invite link: 

https://discordapp.com/api/oauth2/authorize?client_id=536525492015333376&permissions=322560&scope=bot

'''

command_prefix='>'
description = '''
------------------------------------------
               __Awot__
          Tracks user game time.
        Custom calender reminders.      

            Made by Lolisen#2158
------------------------------------------'''

bot = commands.Bot(command_prefix=command_prefix, description=description)

channel_id = privateData.channel_id
update_frequency = 20
backup_frequency = 3600 # 60min

@bot.event
async def on_ready():
    print('Armed and ready!')
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

    activity = discord.Activity(name='your data', type=discord.ActivityType.watching)
    await bot.change_presence(activity=activity)

class Date(commands.Cog):
    '''
    Date: handels dates
    '''
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.printbday())

    async def printbday(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id) 
        while not self.bot.is_closed():

            # Calc delta til next 00:00:00
            now = time.strftime('%H:%M:%S')
            later = '00:00:00'
            delta = (datetime.datetime.strptime(later, '%H:%M:%S') - datetime.datetime.strptime(now, '%H:%M:%S')).seconds
            await asyncio.sleep(delta)

            now = time.strftime('%m-%d')
            date = datetime.now()
            result = dbh.getBirthdayByDate(date.day, date.month)
            dates = []
            for row in result:
                dates.append((row[0], "{}-{}-{}".format(row[1], row[2], row[3])))

            currentYear = datetime.now().year
            for memberID, memberInfo in dates:
                member = bot.get_user(memberID)
                
                birthyear = datetime.datetime.strptime(memberInfo, '%d-%m-%Y').year
                age = currentYear - birthyear

                if age == 1:
                    msg = await channel.send("Happy {}st birthday {}!!". format(age, member.mention))
                elif age == 2:
                    msg = await channel.send("Happy {}nd birthday {}!!". format(age, member.mention))
                elif age == 3:
                    msg = await channel.send("Happy {}nd birthday {}!!". format(age, member.mention))
                else:
                    msg = await channel.send("Happy {}th birthday {}!!". format(age, member.mention))

            await asyncio.sleep(1)

    @commands.command()
    async def addbday(self, ctx, dateStr: str, member: discord.Member = None):
        '''
        Adds a birthday.
        '''
        if member is None:
            member = ctx.author

        msg = await ctx.send('Adding birthday to the database')
        date = datetime.datetime.strptime(dateStr, "%d-%m-%Y")
        
        success = dbh.addBirthdayToDatabase(date, str(member.id)) 
        if success:
            await asyncio.sleep(0.5)
            await msg.edit(content='Trying to add birthday to the database...\nAdded {0}\'s birthday ({1}) to the database.'.format(member.mention, dateStr))
        else:
            await asyncio.sleep(2.0)
            await msg.edit(content='Trying to add birthday to the database...\nFailed trying to add birthday.')

    @commands.command()
    async def bday(self, ctx, member: discord.Member = None):
        '''
        Shows birthday of a specific member.
        '''

        if member is None:
            member = ctx.author

        dates = dbh.getBirthdayByID(str(member.id))
        temp = []
        for d,m,y in dates:
            temp.append(datetime.datetime.strptime("{}-{}-{}".format(d,m,y), "%d-%m-%Y").date())
        dates = []
        dates = temp

        for date in dates:
            await ctx.send("{}'s birthday: {}.".format(member.mention, date))

    @commands.command()
    async def removebday(self, ctx, member: discord.Member = None):
        '''
        Removes birthday from a member.
        '''

        if member is None:
            member = ctx.author


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

    @commands.command()
    async def test(self, ctx, member: discord.Member):
        await ctx.send("{}".format(member.status))

class Stat(commands.Cog):
    '''
    Stat: handels game time and stats 
    '''

    def __init__(self, bot):
        self.bot = bot
        self.memberInfo = self.importBackup()
        self.bg_task_update = self.bot.loop.create_task(self.update_background_task())
        self.bg_task_backup = self.bot.loop.create_task(self.backup_background_task())

    @commands.has_permissions(administrator=True)
    @commands.command()
    async def allstats(self, ctx):  
        '''            
        Shows everyones stats.
        '''
        members = []
        for member in ctx.guild.members:
            members.append(member)

        await self.statscalc(ctx, members)

    @commands.command()
    async def stats(self, ctx, member: discord.Member):  
        '''            
        Shows game time.
        '''
        members = []
        members.append(member)

        await self.statscalc(ctx, members)

    async def statscalc(self, ctx, members):

        status = ["Online", "Do Not Disturb", "Idle", "Offline"]
        for member in members:  
            if member.id in self.memberInfo:
                statusName = ""
                statusValue = ""
                totalActiveTime = 0
                for activity in self.memberInfo[member.id]:
                    if activity in status:
                        time = datetime.timedelta(seconds=self.memberInfo[member.id][activity])
                        statusName += "{}\n".format(str(activity))
                        statusValue += "{}\n".format(str(time))
                        if activity != "Offline":
                            totalActiveTime += self.memberInfo[member.id][activity]

                if totalActiveTime == 0:
                    continue

                gameName = ""
                gameValue = ""
                for activity in self.memberInfo[member.id]:
                    if activity not in status:
                        time = datetime.timedelta(seconds=self.memberInfo[member.id][activity])
                        gameName += "{}\n".format(str(activity))
                        gameValue += "{}\n".format(str(time))
                if gameName == "":
                    gameName = "No games on record"
                    gameValue = ":slight_frown:"

                description="-------------------------------------------------\nShows {}'s time, yes.\n\n{} joined at {:.19}.\n-------------------------------------------------".format(member.mention, member.name, str(member.joined_at))
                embed=discord.Embed(title="All time stats", description=description, color=0x1016fe)
                embed.set_author(name=member)
                embed.set_thumbnail(url=member.avatar_url)
                embed.add_field(name="Status", value=statusName, inline=True)
                embed.add_field(name="Time", value=statusValue, inline=True)
                embed.add_field(name="Games", value=gameName, inline=True)
                embed.add_field(name="Time", value=gameValue, inline=True)
                #embed.timestamp(datetime.datetime.utcnow())
                embed.set_footer(text="~Thats it for this time~ ")
                await ctx.send(embed=embed)

    async def getMembersInfo(self):
        try:
            for server in self.bot.guilds:
                for member in server.members:
                    name = member.id
                    
                    if name not in self.memberInfo:
                        if member.status == discord.Status.online or member.status == discord.Status.idle or member.status == discord.Status.dnd:
                            self.memberInfo[name] = dict()
                            self.memberInfo[name]["Online"] = 0
                            self.memberInfo[name]["Idle"] = 0
                            self.memberInfo[name]["Do Not Disturb"] = 0
                            self.memberInfo[name]["Offline"] = 0
                        else:
                            continue

                    if member.status == discord.Status.online:
                        self.memberInfo[name]["Online"] += update_frequency
                    elif member.status == discord.Status.idle:
                        self.memberInfo[name]["Idle"] += update_frequency
                    elif member.status == discord.Status.dnd:
                        self.memberInfo[name]["Do Not Disturb"] += update_frequency
                    elif member.status == discord.Status.offline:
                        self.memberInfo[name]["Offline"] += update_frequency
                               
                    if member.activity is not None:
                        if str(member.activity.name) in self.memberInfo[name]:
                            self.memberInfo[name][str(member.activity.name)] += update_frequency
                        else:
                            self.memberInfo[name][str(member.activity.name)] = update_frequency
                        
        except Exception as e:
            print("Exception: {}".format(e))
            pass

    @commands.command()
    async def backup(self, ctx):
        '''        
        This command manually backups all the stats and is normally not used.
        Normal use: automatic frequency.
        '''

        print("Manual backup initiated...")
        msg = await ctx.send("Manual backup initiated...")
        self.performBackup()
        await msg.edit(content="Manual backup initiated... Done.")
  
    def performBackup(self):
        print("Performs backup!")
        print("Number of users: {}.".format(len(self.memberInfo)))
        rawData = self.memberInfo
        jsonData = json.dumps(rawData, sort_keys=True)
        with open('stats_backup.json', 'w') as f:
            json.dump(rawData, f)

    def importBackup(self):
        try: 
            with open('stats_backup.json', 'r') as f:
                return json.load(f)

        except Exception as e:
            print(e)
            return {}

    async def backup_background_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id) # channel ID goes here
        while not self.bot.is_closed():
            await asyncio.sleep(backup_frequency)
            print("Automatic backup initiated...")
            self.performBackup()

            #msg = await channel.send("Automatic backup initiated...")
            #msg = await msg.edit(content="Automatic backup initiated... \tDone.")
                   
    async def update_background_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id) # channel ID goes here
        while not self.bot.is_closed():
            await self.getMembersInfo()
            await asyncio.sleep(update_frequency) # task runs every 60 seconds

    @commands.command()
    async def stop(self, ctx):
        '''
        Stops the bot and saves the data.
        '''
        await ctx.send("Shutting down...")
        self.performBackup()
        await self.bot.logout()

     
def Launcher():
    bot.add_cog(Misc(bot))
    bot.add_cog(Date(bot))
    bot.add_cog(Stat(bot))
    bot.run(privateData.token_id)

if __name__ == "__main__":
    Launcher()

