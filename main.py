import asyncio
import datetime
import json
import time
from dataclasses import dataclass
from json import JSONEncoder

import discord
from discord.ext import commands

import databaseHandler as dbh
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
        Source code on GitHub: Awolize 
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
            date = datetime.datetime.now()
            result = dbh.getBirthdayByDate(date.day, date.month)
            dates = []
            for row in result:
                dates.append((row[0], "{}-{}-{}".format(row[1], row[2], row[3])))

            currentYear = datetime.datetime.now().year
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
        
        success = dbh.addBirthdayToDatabase(date, member.id) 
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

        dates = dbh.getBirthdayByID(member.id)
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

@dataclass
class MyMember:
    names: list()
    status: dict()
    games: dict()

class MemberEncoder(JSONEncoder):
    def default(self, object):
        if isinstance(object, MyMember):
            return object.__dict__
        else:
            # call base class implementation which takes care of
            # raising exceptions for unsupported types

            return json.JSONEncoder.default(self, object)

class Stat(commands.Cog):
    '''
    Stat: handels game time and stats 
    '''
    

    def __init__(self, bot):
        self.bot = bot
        self.memberInfo = dict()
        self.topList = dict()
        self.importBackup()
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
    async def show(self, ctx, index):
        if len(self.topList[ctx.guild.id]) == 0:
            return

        if index.isdigit() == False:
            return

        if int(index) < 1 or int(index) > len(self.topList[ctx.guild.id])+1:
            return

        status = ["Online", "Do Not Disturb", "Idle", "Offline"]


        games = dict()
        for member in ctx.guild.members: 
            if member.id in self.memberInfo[ctx.guild.id]:
                try:
                    games[member.name] = self.memberInfo[ctx.guild.id][member.id].games[self.topList[ctx.guild.id][int(index)-1]]
                except:
                    pass

        sorted_games = [(k, games[k]) for k in sorted(games, key=games.get, reverse=True)]

        personName = ""
        gameTime = ""
        counter = 0

        #for key in games.keys():
        for person, time in sorted_games:
            counter += 1
            personName += "{} \n".format(person)
            if time/3600 < 10:
                gameTime += "{:.1f} h\n".format(time/3600)
            else:
                gameTime += "{:.0f} h\n".format(time/3600)
            if counter == 10:
                break

        if personName == "":
            personName = "No games on record"
            gameTime = ":slight_frown:"

        embed=discord.Embed(title=self.topList[ctx.guild.id][int(index)-1], color=0x1016fe)
        #embed.set_author(name=)
        #embed.set_thumbnail(url=self.bot.avatar_url)
        embed.add_field(name="Top", value=personName, inline=True)
        embed.add_field(name="Time", value=gameTime, inline=True)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="~Thats it for this time~")
        await ctx.send(embed=embed)

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
            if member.id in self.memberInfo[ctx.guild.id]:
                statusName = ""
                statusValue = ""
                totalActiveTime = 0
                for activity in self.memberInfo[ctx.guild.id][member.id].status:
                    time = self.memberInfo[ctx.guild.id][member.id].status[activity]
                    if time/3600 < 10:
                        statusValue += "{:.1f} h\n".format(time/3600)
                    else:
                        statusValue += "{:.0f} h\n".format(time/3600)      
                    
                    statusName += "{}\n".format(str(activity))
                    if activity != "Offline":
                        totalActiveTime += self.memberInfo[ctx.guild.id][member.id].status[activity]

                if totalActiveTime == 0:
                    continue

                gameName = ""
                gameValue = ""
                for activity in self.memberInfo[ctx.guild.id][member.id].games:
                    time = self.memberInfo[ctx.guild.id][member.id].games[activity]
                    if time/3600 < 10:
                        gameValue += "{:.1f} h\n".format(time/3600)
                    else:
                        gameValue += "{:.0f} h\n".format(time/3600)                    
                    gameName += "{}\n".format(str(activity))
                
                # if empty
                if gameName == "":
                    gameName = "No games on record"
                    gameValue = ":slight_frown:"

                description="-------------------------------------------------\nShows {}'s time, yes.\n\n{} joined at {:.19}.\n-------------------------------------------------".format(member.mention, member.name, str(member.joined_at))
                embed=discord.Embed(title="Awot GitHub link")
                embed.set_author(name=member)
                embed.set_thumbnail(url=member.avatar_url)
                embed.description = description
                embed.color = 0x1016fe
                embed.timestamp = datetime.datetime.utcnow()
                embed.url = "https://github.com/Awolize/Awot-Discord-Bot"
                embed.set_footer(text="~Thats it for this time~")

                embed.add_field(name="Status", value=statusName, inline=True)
                embed.add_field(name="Time", value=statusValue, inline=True)
                embed.add_field(name="Games", value=gameName, inline=True)
                embed.add_field(name="Time", value=gameValue, inline=True)

                await ctx.send(embed=embed)

    @commands.command()
    async def gamestats(self, ctx):
        status = ["Online", "Do Not Disturb", "Idle", "Offline"]
        games = dict()
        for member in ctx.guild.members:  
            if member.id in self.memberInfo[ctx.guild.id]:
                for activity in self.memberInfo[ctx.guild.id][member.id].games:
                    time = self.memberInfo[ctx.guild.id][member.id].games[activity]
                    if activity not in games:
                        games[activity] = time
                    elif activity in games:
                        games[activity] += time

        sorted_games = [(k, games[k]) for k in sorted(games, key=games.get, reverse=True)]

        self.topList[ctx.guild.id] = list()
        for x in sorted_games:
            self.topList[ctx.guild.id].append(x[0])
        self.topList[ctx.guild.id] = self.topList[ctx.guild.id][:10]

        gamePlacement = ""
        gameName = ""
        gameValue = ""
        counter = 0

        for game, time in sorted_games:
            counter += 1
            #gamePlacement += "{}\n".format(counter)
            gameName += "{} \n".format(game)
            if time/3600 < 10:
                gameValue += "{:.1f} h\n".format(time/3600)
            else:
                gameValue += "{:.0f} h\n".format(time/3600)
            if counter == 10:
                break

        if gameName == "":
            gamePlacement = ":/"
            gameName = "No games on record"
            gameValue = ":slight_frown:"

        description="-------------------------------------------------\nHello:)\n-------------------------------------------------".format()
        embed=discord.Embed(title="All time stats", description=description, color=0x1016fe)
        #embed.set_author(name=)
        #embed.set_thumbnail(url=self.bot.avatar_url)
        #embed.add_field(name="Top", value=gamePlacement, inline=True)
        embed.add_field(name="Games", value=gameName, inline=True)
        embed.add_field(name="Time", value=gameValue, inline=True)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="~Thats it for this time~")
        await ctx.send(embed=embed)

    async def getMembersInfo(self):
        try:
            for server in self.bot.guilds:
                if server.id not in self.memberInfo:
                    self.memberInfo[server.id] = dict()
            
                for member in server.members:
                    if member.bot:
                        continue

                    name = member.id
                    
                    if name not in self.memberInfo[server.id]:
                        if member.status == discord.Status.online or member.status == discord.Status.idle or member.status == discord.Status.dnd:
                            self.memberInfo[server.id][name] = MyMember(list(),dict(),dict())
                            self.memberInfo[server.id][name].names.insert(0, str(member))
                            self.memberInfo[server.id][name].status["Online"] = 0
                            self.memberInfo[server.id][name].status["Idle"] = 0
                            self.memberInfo[server.id][name].status["Do Not Disturb"] = 0
                            self.memberInfo[server.id][name].status["Offline"] = 0
                        else:
                            continue

                    if str(member) not in self.memberInfo[server.id][name].names:
                        self.memberInfo[server.id][name].names.insert(0, str(member))

                    if member.status == discord.Status.online:
                        self.memberInfo[server.id][name].status["Online"] += update_frequency
                    elif member.status == discord.Status.idle:
                        self.memberInfo[server.id][name].status["Idle"] += update_frequency
                    elif member.status == discord.Status.dnd:
                        self.memberInfo[server.id][name].status["Do Not Disturb"] += update_frequency
                    elif member.status == discord.Status.offline:
                        self.memberInfo[server.id][name].status["Offline"] += update_frequency

                    if member.status == discord.Status.online or member.status == discord.Status.dnd:        
                        if member.activity is not None:
                            if str(member.activity.name) in self.memberInfo[server.id][name].games:
                                self.memberInfo[server.id][name].games[str(member.activity.name)] += update_frequency
                            else:
                                self.memberInfo[server.id][name].games[str(member.activity.name)] = update_frequency
                        
        except Exception as e:
            print("getMembersInfo: Exception: {}".format(e))
            pass

    def performBackup(self):
        with open('stats_backup.json', 'w') as write_file:
            json.dump(self.memberInfo, write_file, cls=MemberEncoder, indent=4)

    def importBackup(self):
        try: 
            with open('stats_backup.json', 'r') as f:
                json_data = json.load(f)

            for server in json_data.keys():
                self.memberInfo[int(server)] = dict()
                for member in json_data[server].keys():
                    self.memberInfo[int(server)][int(member)] = MyMember(list(json_data[server][member]["names"]),dict(json_data[server][member]["status"]),dict(json_data[server][member]["games"]))

        except Exception as e:
            print("importBackup: Exception: {}".format(e))

    async def backup_background_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id) # channel ID goes here
        while not self.bot.is_closed():
            await asyncio.sleep(backup_frequency)
            print("[{}] Automatic backup initiated...".format(datetime.datetime.now().strftime('%H:%M:%S')))
            self.performBackup()
                   
    async def update_background_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id) # channel ID goes here
        while not self.bot.is_closed():
            await self.getMembersInfo()
            await asyncio.sleep(update_frequency) # task runs every 60 seconds

    @commands.command()
    async def save(self, ctx):
        '''        
        Saves all the stats manually.
        '''
        self.performBackup()

        msg = await ctx.send("Saving data...")
        print("Performs backup!")
        members = 0
        for server in self.memberInfo.keys():
            members += len(self.memberInfo[server])
        
        servers_str = "Number of servers: {}.".format(len(self.memberInfo))
        members_str = "Number of members: {}.".format(members) 
        
        print("{}\n{}".format(servers_str, members_str))
        await msg.edit(content="Saving data...\n{}\n{}".format(servers_str, members_str))

    @commands.command()
    async def stop(self, ctx):
        '''
        Stops the bot and saves the data.
        '''
        await ctx.send("Shutting down...\nSaving data...")
        self.performBackup()
        await self.bot.logout()

def Launcher():
    bot.add_cog(Misc(bot))
    bot.add_cog(Date(bot))
    bot.add_cog(Stat(bot))
    bot.run(privateData.token_id)

if __name__ == "__main__":
    Launcher()
