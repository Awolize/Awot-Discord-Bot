import time
import asyncpg
import asyncio
import discord
import textwrap
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
        self.bot = bot
        self.current_songs = {}
        self.current_status = {}
        self.member_main_guild = {}

        for member in self.bot.get_all_members():
            if member.bot:
                continue

            song_act = discord.utils.get(member.activities, type=discord.ActivityType.listening)
            if song_act:
                self.start_song(member, song_act)
                
            #  Add current Status data
            self.current_status[member.id] = (member.status, datetime.now())

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        await self.init([guild])

    @commands.Cog.listener()
    async def on_error(self, event):
        print(event)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        clock = datetime.now().strftime("%H:%M:%S") #local time
        print(f"[{clock}] [{str(member)}] Member joined guild [{member.guild.name}]\n")
        await self.add_user(member, member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # was the guild that the user left the main guild of this member?
        clock = datetime.now().strftime("%H:%M:%S") #local time
        print(f"[{clock}] [{str(member)}] Member left guild [{member.guild.name}]\n")
        if self.member_main_guild[member.id] == member.guild.id:
            del self.member_main_guild[member.id]

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        clock = datetime.now().strftime("%H:%M:%S")
        if before.discriminator != after.discriminator:
            print(f"[{clock}] [on_user_update] Discriminator update: {before} -> {after}")
            await self.bot.db.set_user_name(after.id, str(after))
        elif before.name != after.name:
            print(f"[{clock}] [on_user_update] Name update: {before} -> {after}")
            await self.bot.db.set_user_name(after.id, str(after))
        else:
            print(f"[{clock}] [on_user_update] {before} -> {after} profile pic update? najs")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        clock = datetime.now().strftime("%H:%M:%S") #local time
        print(f"[{clock}] Bot connected to guild: {guild.name}")
        print(guild)
        await self.init([guild])

    @commands.Cog.listener()
    async def on_disconnect(self):
        print("Disconnected Unexpectidly")
        # Dont! init doesnt run when the connection comes back -> crash.
        # self.current_status = {}
        # self.current_songs  = {}

    @commands.Cog.listener()
    async def on_ready(self): 
        print("[Stats] Ready")

    async def init(self, guilds: list):
        for guild in guilds:
            try:
                guild_start = time.time()

                members = []
                for member in guild.members:
                    if member.bot:
                        continue
                    members.append(member.id)

                    song_act = discord.utils.get(member.activities, type=discord.ActivityType.listening)
                    if song_act:
                        self.start_song(member, song_act)
                        
                    #  Add current Status data
                    self.current_status[member.id] = (member.status, datetime.now())

                result = await self.bot.db.get_users(tuple(members), guild.id)

                known_users = []
                for row in result:
                    known_users.append(row["user_id"])

                new_members = list(set(members) - set(known_users))

                for member_id in new_members:
                    member = guild.get_member(member_id)
                    await self.add_user(member, guild.id)

                print(f"[Stats] [Init] - {guild.name:<20} {round(time.time()-guild_start, 3)} s")
            except Exception as e:
                    print(f"[Error] [Stats] [Init] {guild.name}, Error: {e}")

    async def add_user(self, member: discord.Member, server_id):
        # Add user to DB
        try:
            await self.bot.db.add_user(member.id, member.name)
        except asyncpg.exceptions.UniqueViolationError as e:
            pass
        
        # Map server to user
        try:
            await self.bot.db.add_server(member.id, server_id)
        except asyncpg.exceptions.UniqueViolationError as e:
            pass

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

        # Activity 
        if member_before.activities != member_after.activities:
            await self.update_activity(member_before, member_after)
        
        # Status
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

                elif new_act.type == discord.ActivityType.streaming:
                    print(f"[{clock}] {str(member_before):<30} Started Streaming: {new_act.name}")
                    pass

                elif new_act.type == discord.ActivityType.playing:
                    try:
                        stat_logger.info(f"[{clock}] {str(member_after):<20} {'':<30} -> {new_act.name} ")
                    except Exception as e:
                        pass
            else:
                new_act = get_activity_by_type(member_after.activities, discord.ActivityType.listening)
                if new_act:
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
                pass

        # Something Changed
        elif len(member_before.activities) == len(member_after.activities):

            # old activity
            stopped_act = activity_diff(member_after.activities, member_before.activities)
            # new activity
            started_act = activity_diff(member_before.activities, member_after.activities)

            if stopped_act and started_act:
                if int(stopped_act.type) == 0:
                    if stopped_act.start > datetime.utcnow():
                        print("wtf is going on")
                        print(stopped_act)
                    duration = datetime.utcnow()-stopped_act.start
                    await self.bot.db.add_game(member_id, stopped_act.name, duration.seconds)
                stat_logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} -> {started_act.name:<30}")

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
                    if act1.type == discord.ActivityType.listening and act2.type == discord.ActivityType.listening:
                        try:
                            song_logger.info(f"[{clock}] {str(member_after):<20} {act1.title:<30} -> {act2.title:<30}")
                            
                            await self.end_song(member_after)
                            self.start_song(member_after, act2)
                        except:
                            pass

                #print(f"Updated something.")

        else:
            print(f"What happened??. {member_before.activities} - {member_after.activities}")

    async def update_status(self, member_before, member_after):
        clock = datetime.now().strftime("%H:%M:%S") #local time
        status_logger.info(f"[{clock}] {str(member_before)} went {member_after.status}")

        await self.end_status(member_before)
        self.start_status(member_after)

    def start_status(self, member):
        self.current_status[member.id] = (member.status, datetime.now())

    async def end_status(self, member):
        status, start_time = self.current_status[member.id]
        time = (datetime.now() - start_time).seconds
        await self.bot.db.add_status(member.id, status, time)

    async def stats_embed(self, ctx, title:str, author:str, thumbnail_url:str, members: list, limit = 10):

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

            await self.stats_embed(ctx, title, author, thumbnail_url, [member.id], limit)
            

        else:
            members = []

            for member in ctx.guild.members:
                if not member.bot:
                    members.append(member.id)

            title = f"List of the most played games on the server"
            author= f"~~ {str(ctx.guild.name)} ~~"
            thumbnail_url = ctx.guild.icon_url

            await self.stats_embed(ctx, title, author, thumbnail_url, members, 15)  
    
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

    async def spotify_embed(self, ctx, date, result):

        title_print  = ""
        artist_print = ""
        played_print = ""
        for row in result:
            track_id        = row["track_id"]
            title           = row["title"]
            artist          = row["artist"]
            play_time       = row["pt"]
            
            title_print  += f"{embedify(title)}\n"
            artist_print += f"{embedify(artist)}\n"
            played_print += f"{round(play_time)}\n"

        if not title_print:
            await ctx.send("No data corresponding to the input")
            return

        title           = f"List of the most played songs"
        author          = f"~~ Spotify ~~"
        description     = f"Based on data from \n{date.strftime('%Y-%m-%d %H:%M:%S')}"
        thumbnail_url   = await self.bot.db.get_album_cover_url(result[0]["track_id"]) 
        
        embed = discord.Embed   (title= title, description=description, color=0x1DB954)
        embed.set_author    (name = author)
        embed.set_thumbnail (url  = thumbnail_url)
        embed.add_field     (name="Song",       value=title_print,    inline=True)
        embed.add_field     (name="Artist",     value=artist_print,   inline=True)
        embed.add_field     (name="Played",     value=played_print,   inline=True)
        embed.set_footer    (text="~ Thats it for this time ~")
        embed.timestamp   = datetime.now()
        await ctx.send      (embed=embed)

    @commands.group(name='spotify', invoke_without_command=True)
    async def _spotify(self, ctx, *, arg: str):
        try:
            member = await commands.MemberConverter().convert(ctx, arg)
        except:
            member = None
            song = arg

        if isinstance(member, discord.Member):
            msg = await ctx.send(f'[Member] Getting music stats for {member.name}...')
            
            # Search db for member info
            result = await self.bot.db.get_song_by_id(member.id)
            await self.spotify_embed(ctx, datetime.strptime("2020-01-25", '%Y-%m-%d'), result)

            await msg.edit(delete_after=5)

        else:
            try:
                og_msg = await ctx.send(content=f'[Song] Getting music stats for "{song}"...', delete_after=60)

                members = []
                for member in ctx.guild.members:
                    if not member.bot:
                        members.append(member.id)

                result = await self.bot.db.get_song_by_name(tuple(members), song)

                if len(result) == 0:
                    await og_msg.delete()
                    await ctx.send(f"Could not find anything (searched for: {song})")
                    return
                elif (len(result) == 1):
                    selected_song = result[0]["track_id"]
                else:
                    print_string = f'''Found multiple results based on "{song}".\nSelect one by typing the associated index (1 - {len(result)}).\n\n'''
                    index_list = list(range(1, len(result)+1))
                    for index, row in enumerate(result):
                        title = row["title"]
                        artist = row["artist"]
                        print_string += f"{index+1}. {title} by {artist}\n"
                    await ctx.send(print_string)

                    def check(m):
                        return m.content.isdigit() and int(m.content) in index_list
                    try:
                        msg = await self.bot.wait_for('message', timeout=60.0, check=check)
                    except asyncio.TimeoutError:
                        ctx.send("Time out.")
                        return
                    selected_song = result[int(msg.content)-1]["track_id"]

                await og_msg.delete()
                members = []
                for member in ctx.guild.members:
                    if not member.bot:
                        members.append(member.id)
                result = await self.bot.db.get_song_by_track_id(members, selected_song)
                artist = result[0]["artist"]
                title = result[0]["title"]
                album = result[0]["album"]
                print_string = f"**{title}** by {artist} (Album: {album})\n"

                for index, row in enumerate(result):
                    member = ctx.guild.get_member(row["user_id"])
                    print_string += f"{index+1}. {str(member)} played the song {round(row['pt'],1)} times\n"

                await ctx.send(print_string)

            except Exception as e:
                await ctx.send(e)
                pass

    @_spotify.group(name='top', invoke_without_command=True)
    async def _spotify_top(self, ctx, date = None):
        await ctx.send('">spotify top songs" to list songs\n">spotify top members" to list users')

    @_spotify_top.command(name='members', aliases=["users"])
    async def _spotify_top_members(self, ctx, date = None):
        await ctx.send("To be implemented.")

    @_spotify_top.command(name='songs')
    async def _spotify_top_songs(self, ctx, date = None):
        '''
        ">help spotify top" for examples
        
        ">spotify top" returns the most played songs since the bot started to track.
        ">spotify top 1w" returns the most played songs from the last week. 
        ">spotify top 2020-01-01" or ">spotify top 01-01-2020" returns the most played songs since 01 jan 2020.
        '''

        # Get date from input
        if date == None:
            date = "2020-01-25"
        
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

        # Get user data from the selected date
        if date:
            try:
                members = []
                for member in ctx.guild.members:
                    if not member.bot:
                        members.append(member.id)

                msg = await ctx.send(f'Gather information from the database and building an embed..')

                result = await self.bot.db.get_most_played_song(tuple(members), date)
                await self.spotify_embed(ctx, date, result)

                await msg.edit(delete_after=5)

            except Exception as e:
                print(e)

    @_spotify.error
    async def _spotify_error(self, ctx, error):
        print(
            f"{ctx.author} wrote the command: {ctx.message.content}\n"
            f"[Error] stats.py -> _spotify_error:\n"
            f"[Error] Error type: {type(error)}\n"
            f"[Error] Error:      {error}\n")

        await ctx.send('Type ">help spotify" for more information')
        return
       
    @commands.command(name='info', aliases=["about", "profile"])
    async def _info(self, ctx: Context, member: discord.Member = None):
        if member is None:
            member = ctx.author

        try:
            # Get most played song, title and time
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    spotify_most_played_song = await conn.fetchval(f'''
                        SELECT 
                            title, artist, album_cover_url, sum(play_time) as pt
                        FROM 
                            spotify 
                        WHERE 
                            user_id = $1
                        GROUP BY 
                            title, artist, album_cover_url
                        ORDER BY
                            pt desc
                    ''', member.id)
            # Get total spotify time
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    spotify_play_time = await conn.fetchval(f'''
                        SELECT 
                            sum(play_time) as pt
                        FROM 
                            spotify 
                        WHERE 
                            user_id = $1
                        ORDER BY
                            pt desc
                    ''', member.id)
                    # result is in seconds
            # Get most played game
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    most_played_game = await conn.fetchval(f'''
                        SELECT 
                            game, sum(play_time) as pt
                        FROM 
                            games 
                        WHERE 
                            user_id = $1
                        GROUP BY 
                            game
                        ORDER BY
                            pt desc
                    ''', member.id)
            
            # Get total game time
            async with self.bot.db.pool.acquire() as conn:
                async with conn.transaction():
                    game_play_time = await conn.fetchval(f'''
                        SELECT 
                            sum(play_time) as pt
                        FROM 
                            games 
                        WHERE 
                            user_id = $1
                        ORDER BY
                            pt desc
                    ''', member.id)
                    # result is in seconds
        except Exception as e:
            print(e)

        joined      = member.joined_at.strftime('%Y-%m-%d - %H:%M:%S')
        username    = str(member)
        avatar_url  = member.avatar_url_as(static_format="png")
        nickname    = member.nick
        roles       = ""
        for role in member.roles:
            roles += f"{discord.utils.escape_mentions(role.name)} "
        
        status      = member.status
        activity    = "N/A"
        if member.activity.name:
            activity = member.activity.name

        spotify_song = "N/A"
        spotify_time = "N/A"
        game_name    = "N/A"
        game_time    = "N/A"

        if spotify_most_played_song:
            spotify_song = spotify_most_played_song

        if spotify_play_time:
            spotify_time = f"{round(spotify_play_time/60/60)} h"

        if most_played_game:
            game_name = most_played_game

        if game_play_time:
            game_time = f"{round(game_play_time/60/60)} h"

        print_str = (
            f"{username} Summary"
            f"```"
            f"Most played: \n"
            f"Song: {spotify_song}\n"
            f"Game: {game_name}\n\n"
            f"Total time: \n"
            f"Spotify: {spotify_time}\n"
            f"Gaming:  {game_time}\n"
            f"{username}, {joined}, {nickname}, {roles}, {status}, {activity}"
            f"```"
            f"{avatar_url}"
        )
        await ctx.send(print_str)

        return

        try:
            date = datetime.strptime("2020-01-25", '%Y-%m-%d')

            title           = f"A summary of Lolisen#2158"
            author          = f"~~ Awot ~~"
            description     = "" #f"Based on data from \n{date.strftime('%Y-%m-%d')}"
            thumbnail_url   = member.avatar_url
            
            #await self.bot.db.get_album_cover_url(result[0]["track_id"]) 

            description=textwrap.dedent(f"""
                **{username} information**
                Created: {created}
                Voice region: {region}
                Features: {features}
                **Counts**
                Members: {member_count:,}
                Roles: {roles}
                Text: {text_channels}
                Voice: {voice_channels}
                Channel categories: {category_channels}
                **Members**
                {constants.Emojis.status_online} {online}
                {constants.Emojis.status_idle} {idle}
                {constants.Emojis.status_dnd} {dnd}
                {constants.Emojis.status_offline} {offline}
            """)

            embed = discord.Embed   (title= title, description=description, color=discord.Color.gold())
            embed.set_author    (name = author, url = self.bot.user.avatar_url, icon_url = self.bot.user.avatar_url)
            embed.set_thumbnail (url  = thumbnail_url)

            embed.set_footer    (text=f"ID: {member.id} • Based on data from {date.strftime('%Y-%m-%d')}")
            await ctx.send      (embed=embed)
        except Exception as e:
            print(e)

    @commands.command(name='server', aliases=["serverinfo"])
    async def _server(self, ctx):
        '''
            Members
        :status_online: 1598
        :status_idle: 2361
        :status_dnd: 862
        :status_offline: 28661
        '''
        pass            
    
    
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
    stats = Stats(bot)
    bot.add_cog(stats)

def teardown(bot):
    pass
