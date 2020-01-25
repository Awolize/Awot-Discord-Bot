import time
import asyncpg
import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import sys

import logging

stat_logger = logging.getLogger("Stat Logger")
stat_logger.setLevel(logging.INFO)
handler = logging.FileHandler("Stats.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d"))
stat_logger.addHandler(handler)

status_logger = logging.getLogger("Status Logger")
status_logger.setLevel(logging.INFO)
handler = logging.FileHandler("Status.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d"))
status_logger.addHandler(handler)

song_logger = logging.getLogger("Spotify Logger")
song_logger.setLevel(logging.INFO)
handler = logging.FileHandler("Spotify.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d"))
song_logger.addHandler(handler)

class Stats(commands.Cog):
    """
    Stat: handels game time and stats
    """

    def __init__(self, bot):
        try:
            self.bot = bot
            self.current_songs = {}
            self.member_main_guild = {}
        except Exception as e:
            print(f"Could not run __init__. Error: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(
            f"[{member.guild.name}] New member connected. Name: {member.name}\n"
            f"Adding to database...")
        await self.add_user(member, member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # was the guild that the user left the main guild of this member?
        if self.member_main_guild[member_id] == member.guild.id:
            del self.member_main_guild[member_id]

        print(f"[{member.guild.name}] Guild removed Member. {member.name}\n")

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.discriminator != after.discriminator:
            print(f"[on_user_update] {before} -> {after}")
            self.bot.db.set_user_name(after.id, str(after))
        else:
            print(f"[on_user_update] {before} -> {after} profile pic update? najs")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        clock = datetime.now().strftime("%H:%M:%S") #local time
        print(f"[{clock}] Bot connected to guild: {guild.name}")
        print(guild)
        await self.init([guild])

    @commands.Cog.listener()
    async def on_ready(self):
        await self.init(self.bot.guilds)
        try:
            print(f"[Stats] Comparing members to the database..")
            start = time.time()
            # Redundant but shouldnt restart more than one time a month anyways
            for guild in self.bot.guilds:
                for member in guild.members:
                    await self.add_user(member, guild.id)
            print(f"[Stats] DB init. Done. ({int(time.time()-start)}s)")
        except Exception as e:
            print(f"[on_ready] [Database] Error: {e}")

    async def init(self, guild: list):
        try:
            start = time.time()
            for guild in self.bot.guilds:
                for member in guild.members:
                    await self.bot.db.set_user_name(member.id, str(member))

            print(f"[Stats] Reading in activities. Done. ({time.time()-start}s)")

        except Exception as e:
            print(f"[on_ready] [init] {e}")

    async def add_user(self, member: discord.Member, server_id):
        try:
            await self.bot.db.add_user(member.id, member.name)
            await self.bot.db.add_server(member.id, server_id)
            await self.bot.db.add_status(member.id)
        except asyncpg.exceptions.UniqueViolationError as e:
            try:
                await self.bot.db.set_user_name(member.id, str(member))
            except Exception as e:
                print(f"{member}, {member.id}, {member.name}")

    # TODO
    @commands.Cog.listener()
    async def on_member_update(self, member_before, member_after):
        if member_before.bot or member_after.bot:
            return
       
        # add server as main server if member doesnt have a main server
        if member_before.id not in self.member_main_guild:
            self.member_main_guild[member_before.id] = member_before.guild.id

        # is this the main server? if not exit to prevent dublicate updates
        if member_before.guild.id != self.member_main_guild[member_before.id]:
            return

        mb_activities = [item for item in member_before.activities if int(item.type) != 4]
        member_before.activities = mb_activities
        ma_activities = [item for item in member_after.activities if int(item.type) != 4]
        member_after.activities = ma_activities

        
        # TODO 
        # Games: done
        # Spotify: TODO

        # Activity 
        if member_before.activities != member_after.activities:
            await self.update_activity(member_before, member_after)

        # TODO
        # Status: TODO
        if member_before.status != member_after.status:
            await self.update_status(member_before, member_after)
      
    async def update_activity(self, member_before, member_after):
        member_id = member_before.id
        clock = datetime.now().strftime("%H:%M:%S")

        # Started something
        if len(member_before.activities) < len(member_after.activities):

            # diff
            new_act = activity_diff(member_before.activities, member_after.activities)

            if new_act:
                    # Listening
                if new_act.type == discord.ActivityType.listening:
                    self.start_song(member_after, new_act)
                    stat_logger.info(f"[{clock}] {str(member_after):<20} {new_act.name:<30} <- {'':<30}")

                elif int(new_act.type) == discord.ActivityType.streaming:
                    print(f"[{clock}] {str(member_before):<30} Started Streaming")
                    pass

                elif new_act.type == discord.ActivityType.playing:
                    try:
                        stat_logger.info(f"[{clock}] {str(member_after):<20} {'':<30} -> {new_act.name} ")
                    except Exception as e:
                        pass
            else:
                new_act = get_activity_by_type(member_after.activities, discord.ActivityType.listening)

                if new_act.type == discord.ActivityType.listening:
                    print(f'new_act.type == discord.ActivityType.listening ({new_act.type} == {discord.ActivityType.listening})')
                    self.start_song(member_after, new_act)
                    song_logger.info(f"[{clock}] {str(member_after):<20} {'':<30} -> {new_act.title:<30}")
                    pass

        # Stopped something
        elif len(member_before.activities) > len(member_after.activities):
            # diff
            stopped_act = activity_diff(member_before.activities, member_after.activities)

            if stopped_act:
                        
                # Listening
                if stopped_act.type == discord.ActivityType.listening:

                    member = member_after
                    if member.id in self.current_songs:
                        try:
                            spotify = self.current_songs[member.id]
                            act = spotify.song
                            duration = datetime.now() - spotify.start
                            await self.bot.db.add_song(member.id, act.title, act.album, act.artist, act.track_id, act.duration.seconds, duration.seconds, act.album_cover_url)
                            stat_logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} <- {'':<30}")
                        except Exception as e:
                            print(e)
                            print()
                # Streaming
                elif stopped_act.type == discord.ActivityType.streaming:
                    print(f"[{clock}] {str(member_before):<30} Stopped Streaming")

                    stat_logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} <- {'Stopped Streaming.':<30}")
                    pass
                
                # Playing
                elif stopped_act.type == discord.ActivityType.playing:
                    try:                        
                        clock = datetime.now().strftime("%H:%M:%S")
                        if stopped_act.start > datetime.utcnow():
                            print(f"[{clock}] [ERROR] act.start > datetime.utcnow() : {stopped_act.start} > {datetime.utcnow()}")
                            print(stopped_act)

                        duration = datetime.utcnow()-stopped_act.start
                        
                        if stopped_act.type == discord.ActivityType.playing:
                            await self.bot.db.add_game(member_id, stopped_act.name, duration.seconds)    

                        stat_logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} <- {'':<30} (Duration: {duration.seconds:>6} s)") 
                    except TypeError as e:
                        print(f"TypeError, passing")
                        pass
                    except Exception as e:
                        print(f"-----------[Error]-----------")
                        print(f"Error in 'elif stopped_act.type == discord.ActivityType.playing:'")
                        print(f"Error type {type(e)}")
                        print(f"Error {e}")
                        pass 
            else:
                print("------------------------------------")
                print("Hur kom jag till denna else satsen??")
                print("------------------------------------")
                stopped_act = get_activity_by_type(member_after.activities, discord.ActivityType.listening)
                if stopped_act:
                    if stopped_act.type == discord.ActivityType.listening:
                        await self.end_song(member_after)
                        song_logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.title:<30} <- {'':<30}")

        # Something Changed
        elif len(member_before.activities) == len(member_after.activities):

            # old activity
            stopped_act = activity_diff(member_after.activities, member_before.activities)
            # new activity
            started_act = activity_diff(member_before.activities, member_after.activities)

            if stopped_act and started_act:
                stop_start_clock = stopped_act.start.strftime("%H:%M:%S")
                start_start_clock= started_act.start.strftime("%H:%M:%S")

                if int(stopped_act.type) == 0:
                    if stopped_act.start > datetime.utcnow():
                        print("wtf is going on")
                        print(stopped_act)
                    duration = datetime.utcnow()-stopped_act.start
                    await self.bot.db.add_game(member_id, stopped_act.name, duration.seconds)
                stat_logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} -> {started_act.name:<30} (Duration: {duration.seconds:>6} s)")

            # something updated
            else:
                member_before.activities.sort(key=lambda a: a.type, reverse=True)
                member_after.activities.sort(key=lambda a: a.type, reverse=True)

                for i in range(len(member_before.activities)):
                    act1 = member_before.activities[i]
                    act2 = member_after.activities[i]

                    if act1.type != act2.type:
                        print("how?")
                        continue

                    # Spotify changes
                    if act1.type == discord.ActivityType.listening:
                        song_logger.info(f"[{clock}] {str(member_after):<20} {act1.title:<30} -> {act2.title:<30}")
                        
                        if act1 == act2:
                            print("same")

                        await self.end_song(member_after)
                        self.start_song(member_after, act2)

                    pass
                if False: #listening to song: if spotify before and after -> if song name changes -> save finished
                    pass
                else:
                    pass
                #print(f"Updated something.")
            pass

        else:
            print(f"What happened??. {member_before.activities} - {member_after.activities}")

    async def update_status(self, member_before, member_after):
        
        if member_before.status == discord.Status.offline:
            status_logger.info(f"{str(member_before)} went online")

        if member_after.status == discord.Status.offline:
            status_logger.info(f"{str(member_before)} went offline")

    async def stats_embedd(self, ctx, title:str, author:str, thumbnail_url:str, members: list, limit = 10):

        rows = await self.bot.db.get_most_played_game(tuple(members), limit)
        games = {}
        for row in rows:
            if "game" in row and "play_time" in row:
                game = row["game"]
                time = row["play_time"]

                if game in games:
                    games[game] += timedelta(seconds=time) 
                else:
                    games[game] = timedelta(seconds=time)

        sorted_games = sorted(games, key=games.get, reverse=True)

        string_games = ""
        string_played_time = ""

        for game in sorted_games:
            
            hours = games[game].total_seconds()/3600

            if hours < 10:
                hours = round(hours, 1)
            else:
                hours = int(round(hours, 0))

            string_games += f"{game}\n"
            string_played_time += f"{hours}\n"


        embed = discord.Embed   (title= title, color=0x1016FE)
        embed.set_author        (name = author)
        embed.set_thumbnail     (url  = thumbnail_url)
        embed.add_field(name="Game Name",       value=string_games,       inline=True)
        embed.add_field(name="Time Played (h)", value=string_played_time, inline=True)
        embed.timestamp = ctx.message.created_at
        embed.set_footer(text="~ Thats it for this time ~")
        await ctx.send(embed=embed)

    @commands.command(name="stats")
    async def _stats(self, ctx, member: discord.Member = None, limit: int = 10):
        '''
        Shows most played games on the server or by a member by tagging them.
        
        Examples:
        stats @name 5  will display the 5  most played games by the user.
        stats          will display the 10 most played games on the server.
        '''
        if member:
            if member.bot:
                return

            title = f"List of the most played games"
            author= f"~~ {str(member)} ~~"
            thumbnail_url = member.avatar_url

            await self.stats_embedd(ctx, title, author, thumbnail_url, [member.id], limit)
            

        else:
            members = []

            for member in ctx.guild.members:
                if not member.bot:
                    members.append(member.id)

            title = f"List of the most played games on the server"
            author= f"~~ {str(ctx.guild.name)} ~~"
            thumbnail_url = ctx.guild.icon_url

            await self.stats_embedd(ctx, title, author, thumbnail_url, members, 15)  
    
    @_stats.error
    async def _stats_error(self, ctx, error):
        print("[Error] stats.py -> stats() -> Exception: {}".format(error))
        await ctx.send(
            "[Error] stats.py -> stats() -> Exception: {}".format(error))

    def start_song(self, member: discord.Member, act):
        self.current_songs[member.id] = Song(act)

    async def end_song(self, member: discord.Member):
        if member.id not in self.current_songs:
            return
        
        act      = self.current_songs[member.id].song
        duration = datetime.now() - self.current_songs[member.id].start
        await self.bot.db.add_song(member.id, act.title, act.album, act.artist, act.track_id, act.duration.seconds, duration.seconds, act.album_cover_url)

    @commands.group(name='spotify', invoke_without_command=True)
    async def _spotify(self, ctx, *, arg: str):
        try:
            member = await commands.MemberConverter().convert(ctx, arg)
        except:
            member = None
            song = arg

        if isinstance(member, discord.Member):
            await ctx.send(f'[Member] Getting music stats for {member.name}...')
            
            # Search db for member info
            result2 = await self.bot.db.get_song_by_id(member.id)
        else:
            await ctx.send(f'[Song] Getting music stats for "{song}"...')
            # Search db for song name
            # ...

    @_spotify.command(name='top')
    async def _spotify_top(self, ctx, date):
        '''
        ">spotify top 1w" returns  the most played song from the last week
        ">spotify top 2020-01-01" or ">spotify top 01-01-2020" returns the most played song since 01 jan 2020  
        '''
        try:
            date = datetime.strptime(date, '%d-%m-%Y')
        except:
            try:
                date = datetime.strptime(date, '%Y-%m-%d')
            except:
                try:
                    amount = int(date[:-1])
                    unit_of_time = date[-1:]
                    if unit_of_time in ["d","w","m","y"]:
                        if unit_of_time == "d":
                            date = timedelta(days=amount)
                        elif unit_of_time == "w":
                            date = timedelta(weeks=amount)
                        elif unit_of_time == "m":
                            date = timedelta(months=amount)
                        elif unit_of_time == "y":
                            date = timedelta(years=amount)
                        date = datetime.now() - date
                except:
                    pass

        if date:
            try:
                members = []
                for member in ctx.guild.members:
                    if not member.bot:
                        members.append(member.id)

                title_print  = ""
                artist_print = ""
                played_print = ""

                result = await self.bot.db.get_most_played_song(tuple(members), date)
                for row in result:
                    title       = row["title"]
                    artist      = row["artist"]
                    song_length = row["song_length"]
                    play_time   = row["play_time"]
                    
                    if round(play_time/song_length) > 0:
                        title_print  += f"{embedify(title)}\n"
                        artist_print += f"{embedify(artist)}\n"
                        played_print += f"{round(play_time/song_length)}\n"

                if not title_print:
                    await ctx.send("No data corresponding to the input")
                    return
            
                title           = f"List of the most played songs"
                author          = f"~~ {str(ctx.guild.name)} ~~"
                description     = f"Based on saved data from \n{date.strftime('%Y-%m-%d %H:%M:%S')}"
                try:
                    thumbnail_url = result[0]["album_cover_url"]
                except expression as identifier:
                    thumbnail_url = ctx.guild.icon_url
                
                embed = discord.Embed   (title= title, description=description, color=0x1DB954)
                embed.set_author        (name = author)
                embed.set_thumbnail     (url  = thumbnail_url)
                embed.add_field(name="Song",       value=title_print,    inline=True)
                embed.add_field(name="Artist",     value=artist_print,   inline=True)
                embed.add_field(name="Played",     value=played_print,   inline=True)
                embed.timestamp = datetime.now()
                embed.set_footer(text="~ Thats it for this time ~")
                await ctx.send(embed=embed)
            except Exception as e:
                print(e)

    @_spotify.error
    async def _spotify_error(self, ctx, error):
        print("[Error] stats.py -> stats() -> _spotify_error -> Exception: {}".format(error))
        await ctx.send("[Error] stats.py -> stats()  -> _spotify_error -> Exception: {}".format(error))

def embedify(text, len = 23):
    text = text[:len] + (text[len:] and '..')
    return text

class Song():
    def __init__(self, act):
        self.song = act
        self.start = datetime.now()

def get_activity_by_type(list1, type : discord.ActivityType):
    for act in list1:
        if act.type == type:
            return act
            
def activity_same(list1, list2):
    try:
        list1_names = []
        for act in list1:
            if int(act.type) != 4:
                if int(act.type) == 2:
                    list1_names.append(act.track_id)
                else:
                    list1_names.append(act.name)
        list2_names = []
        for act in list2:
            if int(act.type) != 4:
                if int(act.type) == 2:
                    list2_names.append(act.track_id)
                else:
                    list2_names.append(act.name)

        if list1_names == list2_names: 
            return True
        return False
    except Exception as e:
        print(f"[ERROR] - [activity_diff] - {e}")
        return False

# based on names
def activity_diff(list1, list2):
    try:
        # Get names from the items
        list1_names = []
        for act in list1:
            if int(act.type) != 4:
                list1_names.append(act.name)
        list2_names = []
        for act in list2:
            if int(act.type) != 4:
                list2_names.append(act.name)


        # Get unique items
        diff_names = list(set(list2_names) - set(list1_names))
        compare_list = list2
        
        if not diff_names:
            compare_list = list1
            diff_names = list(set(list1_names) - set(list2_names))
        
        # Get information about the unique items
        diff = None
        for act in compare_list:
            if act.name in diff_names:
                diff = act
                break

        return diff
    except Exception as e:
        print(f"[ERROR] - [activity_diff] - {e}")
        return None

def setup(bot):
    bot.add_cog(Stats(bot))
