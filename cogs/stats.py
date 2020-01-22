import time
import asyncpg
import discord
from discord.ext import tasks, commands
from datetime import datetime, timedelta
import sys
from pympler.asizeof import asizeof

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler("stats.log", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", "%Y-%m-%d"))
logger.addHandler(handler)

class Stats(commands.Cog):
    """
    Stat: handels game time and stats
    """

    def __init__(self, bot):
        try:
            self.bot = bot
            self.current_activities = {}
        except Exception as e:
            print(f"Could not run __init__. Error: {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        print(
            f"[{member.guild.name}] New member connected. Name: {member.name}\n"
            f"Adding to database...")
        await self.add_user(member, member.guild.id)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        print(f"[on_user_update] {before} -> {after}")
        if before.discriminator != after.discriminator:
            self.bot.db.set_user_name(after.id, str(after))

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
                    activities = [item for item in member.activities if int(item.type) != 4]
                    self.current_activities[member.id] = activities

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

        # Started something
        if len(member_before.activities) < len(member_after.activities):
            if len(member_after.activities) != len(self.current_activities.get(member_id, [])):
                self.current_activities[member_id] = member_after.activities

                # diff
                new_act = activity_diff(member_before.activities, member_after.activities)

                clock = datetime.now().strftime("%H:%M:%S") #local time
                if new_act:
                    if int(new_act.type) == discord.ActivityType.streaming:
                        print()
                        pass
                    if not isinstance(new_act.start, datetime):
                        print("not isinstance(new_act.start, datetime)")
                    else:
                        try:
                            logger.info(f"[{clock}] {str(member_after):<20} {'':<30} -> {new_act.name} ")
                        except Exception as e:
                            pass

        # Stopped something
        elif len(member_before.activities) > len(member_after.activities):
            if len(member_after.activities) != len(self.current_activities.get(member_id, [])):
                self.current_activities[member_id] = member_after.activities

                # diff
                stopped_act = activity_diff(member_before.activities, member_after.activities)

                if stopped_act:                  
                    if int(stopped_act.type) == discord.ActivityType.streaming:
                        print(f"{member_before} Stopped Streaming.")
                        pass
                    if not isinstance(stopped_act.start, datetime):
                        clock = datetime.now().strftime("%H:%M:%S")
                        print(f"[{clock}] [ERROR] No 'act.start': {stopped_act}")
                    else:
                        clock = datetime.now().strftime("%H:%M:%S")
                        if stopped_act.start > datetime.utcnow():
                            print(f"[{clock}] [ERROR] act.start > datetime.utcnow() : {stopped_act.start} > {datetime.utcnow()}")
                            print(stopped_act)
                        duration = datetime.utcnow()-stopped_act.start
                        
                        if stopped_act.type == discord.ActivityType.playing:
                            await self.bot.db.add_game(member_id, stopped_act.name, duration.seconds)

                           
                else:
                    get_activity_by_type()
                    stopped_act.type == discord.ActivityType.listening:
                    print(f"start:    {stopped_act.start.hour}:{stopped_act.start.minute}:{stopped_act.start.second}")
                    print(f"end:      {stopped_act.end.hour}:{stopped_act.end.minute}:{stopped_act.end.second}")
                    print(f"length:   {stopped_act.duration.seconds} s")
                    print(f"duration: {duration.seconds} s")
                    print()
                    pass
                    #await self.bot.db.add_song(stopped_act.title, stopped_act.album, stopped_act.artist, stopped_act.track_id, stopped_act.duration.seconds, duration)

                        logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} <- {'':<30} (Duration: {duration.seconds:>6} s)")
        # Something Changed
        elif len(member_before.activities) == len(member_after.activities):

            if activity_same(self.current_activities.get(member_id, []), member_before.activities):
                self.current_activities[member_id] = member_after.activities
                # old activity
                stopped_act = activity_diff(member_after.activities, member_before.activities)
                # new activity
                started_act = activity_diff(member_before.activities, member_after.activities)

                if stopped_act and started_act:

                    clock = datetime.now().strftime("%H:%M:%S")
                    stop_start_clock = stopped_act.start.strftime("%H:%M:%S")
                    start_start_clock= started_act.start.strftime("%H:%M:%S")

                    if int(stopped_act.type) == 0:
                        if stopped_act.start > datetime.utcnow():
                            print("wtf is going on")
                            print(stopped_act)
                        duration = datetime.utcnow()-stopped_act.start
                        await self.bot.db.add_game(member_id, stopped_act.name, duration.seconds)
                    logger.info(f"[{clock}] {str(member_after):<20} {stopped_act.name:<30} -> {started_act.name:<30} (Duration: {duration.seconds:>6} s)")

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
                            print()
                            pass

                        pass
                    if False: #listening to song: if spotify before and after -> if song name changes -> save finished
                        pass
                    else:
                        pass
                    #print(f"Updated something.")
                pass

        else:
            print(f"What happened??. {member_before.activities} - {member_after.activities}")

        self.current_activities[member_id] = member_after.activities

    async def update_status(self, member_before, member_after):
        return

        if member_after.status == discord.Status.offline:
            if member_before.id in self.current_activities:
                print(f"{member_before.name} went offline, Saving...")

                for activity in member_before.activities:
                    # playing
                    if activity_before.type is discord.ActivityType.playing:
                        time = (datetime.utcnow() -
                                activity_before.start).seconds

                        app_id = self.current_activities[member_before.id][int(
                            discord.ActivityType.playing)]

                        await self.bot.db.add_game(member_before.id, app_id,
                                                   time)

                del self.current_activities[member_before.id]

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

def get_activity_by_type(list1, type : discord.ActivityType):
    for act in list1:
        if act.type == type:
            return act

    return None

def activity_same(list1, list2):
    try:
        list1_names = []
        for act in list1:
            if int(act.type) != 4:
                list1_names.append(act.name)
        list2_names = []
        for act in list2:
            if int(act.type) != 4:
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
