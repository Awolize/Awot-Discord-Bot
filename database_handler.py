import asyncio
import asyncpg
import time
from datetime import datetime
import config


class Database():
    async def init(self):
        print("--------------------")
        try:
            self.pool = await asyncpg.create_pool(host=config.DATABASE_HOST,
                                                  database=config.DATABASE_DATABASE,
                                                  user=config.DATABASE_USER,
                                                  port=config.DATABASE_PORT,
                                                  password=config.DATABASE_PASSWORD,
                                                  command_timeout=config.DATABASE_TIMEOUT)
            print(f"[DB] Connected to database.")
            return self.pool
        except ConnectionRefusedError:
            print(f"[DB] Connection to database was denied.")
        except Exception as e:
            print(f"[DB] An error occured: {e}")

    async def add_user(self, user_id, name=None):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if name:
                    result = await conn.execute(f'''
                    INSERT INTO users (user_id, name)
                        VALUES ( $1, $2 )
                    ''', user_id, name)
                else:
                    result = await conn.execute(f'''
                    INSERT INTO users
                        VALUES ($1)
                    ''', user_id)
    
    async def get_users(self, users:tuple, guild_id = None):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                if guild_id:
                    result = await conn.fetch(f'''
                    SELECT 
                        users.user_id 
                    FROM 
                        users, servers 
                    WHERE       users.user_id = servers.user_id
                          AND   users.user_id = any($1::BIGINT[])
                          AND   servers.server_id = $2;
                    ''', users, guild_id)
                    return result
                else:
                    result = await conn.fetch(f'''
                    SELECT 
                        user_id 
                    FROM 
                        users 
                    WHERE user_id = any($1::BIGINT[])
                    ''', users)
                    return result

    async def add_server(self, user_id, server_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(f'''
                INSERT INTO servers (user_id, server_id)
                    VALUES ( $1, $2 )
                ''', user_id, server_id)

    async def add_status(self, user_id, status=None, time=None):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(f'''
                    INSERT INTO status 
                        (user_id)
                    VALUES 
                        ( $1 )

                    ON CONFLICT (user_id) DO UPDATE
                        SET 
                            {status} = status.{status} + $2
                ''', user_id, time)

    async def get_most_played_game(self, users:tuple, limit=15):
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    result = await conn.fetch('''
                    SELECT 
                        game, sum(play_time) as play_time
                    FROM games 
                        WHERE user_id = any($1::BIGINT[])
                        GROUP BY game order by sum(play_time) DESC limit $2;
                    ''', users, limit)
                    return result
        except Exception as e:
            print(e)
            pass

    async def get_game_by_id(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch('''
                    Select 
                        game, play_time 
                    FROM games 
                        where user_id = $1
                ''', user_id)
                return result

    async def add_game(self, user_id, game, time):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute('''
                    INSERT INTO games 
                        (user_id, game, play_time) 
                    VALUES 
                        ( $1, $2, $3 ) 
                    
                    ON CONFLICT (user_id, game) DO UPDATE
                        SET 
                            play_time = games.play_time + $3 
                ''', user_id, str(game), time)


    async def get_most_played_song(self, users: tuple, date):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    result = await conn.fetch('''
                        SELECT track_id, title, artist, 
                            SUM(play_time::decimal/song_length::decimal) as pt
                        FROM spotify
                        WHERE
                            t >= $2 
                            AND user_id = any($1::BIGINT[])
                        GROUP BY track_id, title, artist
                        ORDER BY pt DESC
                        LIMIT 20;
                    ''', users, date)
                    return result
                except Exception as e:
                    print(f"ERROR: {e}")

    async def get_song_by_id(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch('''
                    SELECT 
                        track_id, title, artist, 
                        SUM(play_time::decimal/song_length::decimal) as pt
                    FROM spotify 
                    WHERE user_id = $1 
                    GROUP BY track_id, title, artist
                    ORDER BY pt DESC
                    LIMIT 20
                ''', user_id)
                return result

    async def get_song_by_track_id(self, users: tuple, track_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch('''
                    SELECT 
                        user_id, title, artist, album,
                        SUM(spotify.play_time::decimal/spotify.song_length::decimal) as pt
                    FROM spotify 
                    WHERE   track_id = $1
                        AND user_id = any($2::BIGINT[])
                    GROUP BY user_id, title, artist, album
                    ORDER BY pt DESC
                    LIMIT 20
                ''', track_id, users)
                return result

    async def get_song_by_name(self, users: tuple, name):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch('''
                    SELECT DISTINCT track_id, title, album, artist
                    FROM spotify
                    WHERE 
                        lower(title) ~ lower($1)
                        AND user_id = any($2::BIGINT[]);
                ''', name, users)
                return result

    async def get_album_cover_url(self, track_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetchval('''
                    SELECT 
                        album_cover_url
                    FROM 
                        spotify 
                    WHERE 
                        track_id = $1
                ''', track_id)
                return result

    # act.title, act.album, act.artist, act.track_id, act.duration.seconds, duration
    async def add_song(self, user_id, title, album, artist, track_id, song_length, play_time, url):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute('''
                    INSERT INTO spotify 
                        (user_id, title, album, artist, track_id, song_length, play_time, album_cover_url) 
                    VALUES 
                        ( $1,     $2,    $3,    $4,     $5,       $6,          $7,        $8 ) 
                    
                    ON CONFLICT (user_id, track_id, t) DO UPDATE
                        SET 
                            play_time = spotify.play_time + $7
                ''', user_id, title, album, artist, track_id, song_length, play_time, url)

    async def set_user_name(self, user_id, name):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute('''
                UPDATE users
                SET
                    name = $1
                WHERE
                    user_id = $2
                ''', name, user_id)

    # not in use (insecure)
    async def fetch(self, select, table, where):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.fetch(f'select {select} from {table} where {where}')

    async def get_birthday_by_id(self, member_id: int, server_id: int):
        async with self.pool.acquire() as conn:
            async with conn.transaction():

                date_day = "date_part('day', CURRENT_DATE)"
                date_month = "date_part('month', CURRENT_DATE)"
                result = await conn.fetchval(f'''
                SELECT birthday FROM birthday
                WHERE
                    user_id = $1 AND server_id = $2
                ''', member_id, server_id)

                return result

    # not in user (insecure)
    async def get_birthday(self, server_id: int, date=None):
        async with self.pool.acquire() as conn:
            async with conn.transaction():

                date_day = "date_part('day', CURRENT_DATE)"
                date_month = "date_part('month', CURRENT_DATE)"
                if date:
                    if date.split("/")[0].isdigit() and date.split("/")[1].isdigit():
                        date_day = date.split("/")[0]
                        date_month = date.split("/")[1]

                result = await conn.fetch(f'''
                SELECT user_id FROM birthday
                WHERE
                    DATE_PART('day', birthday) = {date_day}
                AND
                    DATE_PART('month', birthday) = {date_month}
                AND server_id = {server_id}
                ''')

                return result

    async def set_birthday(self, user_id: int, server_id: int, birthday: datetime.date):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                try:
                    result = await conn.execute('''
                    INSERT INTO birthday 
                        (user_id, server_id, birthday)
                    VALUES ($1, $2, $3)
                    ''', user_id, server_id, birthday)
                    return result
                except asyncpg.exceptions.ForeignKeyViolationError as e:
                    return e
                except Exception as e:
                    print(f'Error:{e} \nType: {type(e)}')

    async def remove_birthday(self, user_id, server_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute('''
                DELETE FROM birthday
                WHERE
                    user_id = $1 AND server_id = $2
                ''', user_id, server_id)
                print("delete")
                print(result)
                return result


async def main(db):
    await db.init()

    # await db.insert("users (user_id, name) ", "213752019767394305, 'Sen'")
'''
Message received:
    If user in database:
        increase user.xp by X
        if user.xp == user.level.limit:
            increase user.level by 1
            if user.level.notifications:
                send annoying message
    else:
        add user in database
        set user exp to X
'''

if __name__ == "__main__":
    db = Database()
    asyncio.get_event_loop().run_until_complete(main(db))
