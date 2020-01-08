import time
import asyncpg
import discord
from discord.ext import tasks, commands


class Stats(commands.Cog):
    '''
    Stat: handels game time and stats
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(f"New member connected.\nName: {member.name}"
              f"\nAdding to database...")
        await self.add_user(member, member.guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(f"Bot connected to new guild [{guild.name}]")
        print(guild)
        for member in guild.members:
            await self.add_user(member, guild.id)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"[Stats] Collecting members..")
        start = time.time()
        for guild in self.bot.guilds:
            for member in guild.members:
                await self.add_user(member, guild.id)
        print(f"[Stats] Done. ({time.time()-start})")

    async def add_user(self, member: discord.Member, server_id):
        try:
            await self.bot.db.add_user(member.id, member.name)
            await self.bot.db.add_server(member.id, server_id)
            await self.bot.db.add_status(member.id)
        except asyncpg.exceptions.UniqueViolationError as e:
            try:
                await self.bot.db.set_user_name(member.id, member.name)
            except Exception as e:
                print(f"{member}, {member.id}, {member.name}")

    # @commands.command(name="stats", aliases=["stats"])
    @commands.command(name="stats")
    async def stats(self, ctx, member: discord.Member = None):
        pass

    @stats.error
    async def stats_error(self, ctx, error):
        print("[Error] stats.py -> stats() -> Exception: {}".format(error))
        await ctx.send("[Error] stats.py -> stats() -> Exception: {}".format(error))


class Stats0(commands.Cog):
    '''
    Stat: handels game time and stats 
    '''

    def __init__(self, bot):
        self.bot = bot
        self.memberInfo = dict()
        self.topList = dict()
        self.importBackup()
        self.bg_task_update = self.bot.loop.create_task(
            self.update_background_task())
        self.bg_task_backup = self.bot.loop.create_task(
            self.backup_background_task())
        self.bg_task_db_update = self.bot.loop.create_task(
            self.update_database_background_task())

    # ------------------------------------------

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

    @commands.command(parent="gamestats")
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
                    games[member.name] = self.memberInfo[ctx.guild.id][member.id].games[self.topList[ctx.guild.id][int(
                        index)-1]]
                except:
                    pass

        sorted_games = [(k, games[k])
                        for k in sorted(games, key=games.get, reverse=True)]

        personName = ""
        gameTime = ""
        counter = 0

        # for key in games.keys():
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

        embed = discord.Embed(
            title=self.topList[ctx.guild.id][int(index)-1], color=0x1016fe)
        # embed.set_author(name=)
        # embed.set_thumbnail(url=self.bot.avatar_url)
        embed.add_field(name="Top", value=personName, inline=True)
        embed.add_field(name="Time", value=gameTime, inline=True)
        embed.timestamp = datetime.datetime.utcnow()
        embed.set_footer(text="~Thats it for this time~")
        await ctx.send(embed=embed)

    @commands.command()
    async def stats(self, ctx, member: discord.Member, showAmount=5):
        '''            
        Shows game time.
        '''
        members = []
        members.append(member)

        await self.statscalc(ctx, members, showAmount)

    @stats.error
    async def stats_error(self, ctx, error):
        print("[Error] stats.py -> stats() -> Exception: {}".format(error))
        await ctx.send("[Error] stats.py -> stats() -> Exception: {}".format(error))

    async def statscalc(self, ctx, members, showAmount=5):
        try:
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

                    games = self.memberInfo[ctx.guild.id][member.id].games
                    games = [(k, games[k]) for k in sorted(
                        games, key=games.get, reverse=True)]
                    gameName = ""
                    gameValue = ""
                    counter = 0
                    for activity in games:
                        if counter == showAmount:
                            break
                        time = activity[1]
                        if time/3600 < 10:
                            gameValue += "{:.1f} h\n".format(time/3600)
                        else:
                            gameValue += "{:.0f} h\n".format(time/3600)
                        gameName += "{}\n".format(activity[0])
                        counter += 1

                    description = "-------------------------------------------------\nShows {}'s game time, top {} games, yes.\n\n{} joined at {:.19}.\n".format(
                        member.mention, showAmount, member.name, str(member.joined_at))

                    # adds birthday to the stats card
                    date = dbh.getBirthdayByID(member.id, ctx.message.guild.id)

                    if date:
                        day = date[0][0]
                        month = date[0][1]
                        year = date[0][2]

                        if year is 0:
                            birthday = "Birthday at {}/{}.".format(day, month)
                        else:
                            birthday = "Birthday at {}-{}-{}.".format(
                                day, month, year)

                        description = description + birthday + "\n"
                    # --------------------------------

                    description = description + "-------------------------------------------------"

                    embed = discord.Embed(title="Awot GitHub link")
                    embed.set_author(name=member)
                    embed.set_thumbnail(url=member.avatar_url)
                    embed.description = description
                    embed.color = 0x1016fe
                    embed.timestamp = datetime.datetime.utcnow()
                    embed.url = "https://github.com/Awolize/Awot-Discord-Bot"
                    embed.set_footer(text="~Thats it for this time~")

                    embed.add_field(name="**Status**",
                                    value=statusName, inline=True)
                    embed.add_field(name="**Time**",
                                    value=statusValue, inline=True)
                    if gameName:
                        embed.add_field(name="x", value="x", inline=False)
                        embed.add_field(name="**Games**",
                                        value=gameName, inline=True)
                        embed.add_field(name="**Time**",
                                        value=gameValue, inline=True)

                    await ctx.send(embed=embed)

        except Exception as e:
            print("[Error] stats.py -> statscalc() -> Exception: {}".format(e))
            success = False

    @commands.command()
    async def updatedatabase(self, ctx):
        msg = await ctx.send("Updating firebase with the current data...")
        self.updateDatabase()
        await msg.edit(content="Updating firebase with the current data... Done")

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

        sorted_games = [(k, games[k])
                        for k in sorted(games, key=games.get, reverse=True)]

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
            # gamePlacement += "{}\n".format(counter)
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

        description = "-------------------------------------------------\nHello:)\n-------------------------------------------------".format(
        )
        embed = discord.Embed(title="All time stats",
                              description=description, color=0x1016fe)
        # embed.set_author(name=)
        # embed.set_thumbnail(url=self.bot.avatar_url)
        # embed.add_field(name="Top", value=gamePlacement, inline=True)
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
                            self.memberInfo[server.id][name] = MyMember(
                                list(), dict(), dict())
                            self.memberInfo[server.id][name].names.insert(
                                0, str(member))
                            self.memberInfo[server.id][name].status["Online"] = 0
                            self.memberInfo[server.id][name].status["Idle"] = 0
                            self.memberInfo[server.id][name].status["Do Not Disturb"] = 0
                            self.memberInfo[server.id][name].status["Offline"] = 0
                        else:
                            continue

                    if str(member) not in self.memberInfo[server.id][name].names:
                        self.memberInfo[server.id][name].names.insert(
                            0, str(member))

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
                                self.memberInfo[server.id][name].games[str(
                                    member.activity.name)] += update_frequency
                            else:
                                self.memberInfo[server.id][name].games[str(
                                    member.activity.name)] = update_frequency

        except Exception as e:
            print("getMembersInfo: Exception: {}".format(e))
            pass

    def performBackup(self):

        # remove removed accounts
        removeUserList = []
        for serverID, usersInfo in self.memberInfo.items():
            # serverID = unique_id
            for userID, myMember in usersInfo.items():
                # Check if valid userID
                if self.bot.get_user(userID) is None:
                    print("User id not valid: {}".format(userID))
                    removeUser = {"server": serverID, "user": userID}
                    removeUserList.append(removeUser)

        for userDict in removeUserList:
            del self.memberInfo[userDict["server"]][userDict["user"]]

        # Save to json
        with open('stats_backup.json', 'w') as write_file:
            json.dump(self.memberInfo, write_file, cls=MemberEncoder, indent=4)

    def updateDatabase(self):
        # Save to database
        gsDB = gameStatsDBh.GameStatsDB()
        firestoreHandler = FH.FirestoreHandler()

        for serverID, usersInfo in self.memberInfo.items():
            # serverID = unique_id
            for userID, myMember in usersInfo.items():
                # Check if valid userID
                if self.bot.get_user(userID) is None:
                    print("User id not valid: {}".format(userID))
                    continue
                # userID = unique_id
                # users.games (dict)
                # users.names (List)
                # users.status (dict)

                # Add user if user doesn't exist
                # check if user exists
                if not gsDB.get_user(user_id=userID)[0]:
                    user = self.bot.get_user(userID)
                    if user:
                        # adds if doesn't exist
                        gsDB.add_user(userID, serverID, str(user))

                # Add server to users
                gsDB.add_server_to_user(userID, serverID)

                # Update Status counters
                statusList = list()

                for key, value in myMember.status.items():
                    statusList.append(value)

                gsDB.add_status_time_to_user_id(userID, statusList)

                # Update nicknames
                gsDB.add_nicknames_to_user(userID, myMember.names)

                # Add games and update time
                gamesList = list()
                gameListFirebase = list()

                for key, value in myMember.games.items():
                    gamesList.append((key, value))
                    gameListFirebase.append({"id": key, "time": value})

                gsDB.update_games_by_user_id(userID, gamesList)
                userobj = self.bot.get_user(userID)
                firestoreHandler.main(str(userID), myMember.names, statusList, gameListFirebase, userobj.name, str(
                    userobj.avatar_url_as(static_format='png', size=512)))

                server = self.bot.get_guild(serverID)
                firestoreHandler.addServersToUsers(str(userID), server.id, server.name, str(
                    server.icon_url_as(static_format='png', size=512)))

        for serverId, serverInfo in self.memberInfo.items():
            userList = list()
            for userId, userInfo in serverInfo.items():
                userobj = self.bot.get_user(userId)
                userList.append({"id": str(userId), "name": userobj.name})
            server = self.bot.get_guild(serverId)
            firestoreHandler.addServers(str(server.id), server.name, str(
                server.icon_url_as(static_format='png', size=512)), userList)

        firestoreHandler.addServersToUsers_done()

        firestoreHandler.commit()
        gsDB.commit()
        pass

    def importBackup(self):
        try:
            # Json solution
            ttime = time.time()
            with open('stats_backup.json', 'r') as f:
                json_data = json.load(f)

            for server in json_data.keys():
                self.memberInfo[int(server)] = dict()
                for member in json_data[server].keys():
                    self.memberInfo[int(server)][int(member)] = MyMember(list(json_data[server][member]["names"]), dict(
                        json_data[server][member]["status"]), dict(json_data[server][member]["games"]))
            print("[Json] Import backup took: {0:.3f}s".format(
                time.time() - ttime))

            # Database solution
            # Populate usersdict with users and their information
            ttime = time.time()
            gsDB = gameStatsDBh.GameStatsDB()
            self.userDict = dict()
            users = gsDB.get_all_users()[1]

            for user in users:
                user = user[0]

                self.userDict[user] = UserStruct(
                    user, list(), dict(), dict(), list())

                # Game stats
                gameList = gsDB.get_all_games(user)[1]
                for gameName, gameTime in gameList:
                    self.userDict[user].games[gameName] = gameTime

                # Status stats
                statusTuple = gsDB.get_all_status(user)[1]
                self.userDict[user].status["online"] = statusTuple[0]
                self.userDict[user].status["idle"] = statusTuple[1]
                self.userDict[user].status["busy"] = statusTuple[2]
                self.userDict[user].status["offline"] = statusTuple[3]

                # Usernames
                nameList = gsDB.get_all_nicknames(user)[1]
                templist = list()
                for name in nameList:
                    templist.append(name[0])
                self.userDict[user].names = templist

                # Servers
                nameList = gsDB.get_all_servers(user)[1]
                templist = list()
                for name in nameList:
                    templist.append(name[0])
                self.userDict[user].servers = templist
            # --------------------------------------------------------

            print("[DB] Import backup took: {0:.3f}s".format(
                time.time() - ttime))

        except Exception as e:
            print("[Error] stats.py -> importBackup() -> Exception: {}".format(e))

    async def backup_background_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id)  # channel ID goes here
        while not self.bot.is_closed():
            await asyncio.sleep(backup_frequency)
            print("[{}] Automatic backup initiated...".format(
                datetime.datetime.now().strftime('%H:%M:%S')))
            self.performBackup()

    async def update_database_background_task(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(backupDatabase_frequency)
            self.updateDatabase()

    async def update_background_task(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(channel_id)  # channel ID goes here
        while not self.bot.is_closed():
            await self.getMembersInfo()
            await asyncio.sleep(update_frequency)  # task runs every 60 seconds

    @commands.command()
    async def save(self, ctx):
        '''        
        Saves all the stats manually.
        '''

        msg = await ctx.send("Saving data...")
        print("Performs backup!")

        self.performBackup()

        members = 0
        for server in self.memberInfo.keys():
            members += len(self.memberInfo[server])

        servers_str = "Number of servers: {}.".format(len(self.memberInfo))
        members_str = "Number of members: {}.".format(members)

        print("{}\n{}".format(servers_str, members_str))
        await msg.edit(content="Saving data...\n{}\n{}".format(servers_str, members_str))

    @commands.command()
    async def test(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        isAdmin = member.permissions_in(ctx.channel).administrator

        if isAdmin:
            pass
            # msg = await ctx.send("Admin")
        else:
            pass
            # msg = await ctx.send("Not admin")


def setup(bot):
    bot.add_cog(Stats(bot))
