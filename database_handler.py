import asyncio
import asyncpg
import time
from datetime import datetime
import config


class Database():
    async def init(self):
        print("--------------------")
        try:
            self.pool = await asyncpg.create_pool(database=config.DATABASE_DATABASE,
                                                  user=config.DATABASE_USER,
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

    async def add_server(self, user_id, server_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(f'''
                INSERT INTO servers (user_id, server_id)
                    VALUES ( $1, $2 )
                ''', user_id, server_id)

    async def add_status(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(f'''
                INSERT INTO status (user_id)
                    VALUES ( $1 )
                ''', user_id)

    async def add_games(self, user_id, game):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(f'''
                INSERT INTO games (user_id, game)
                    VALUES ( $1, $2 )
                ''', user_id, game)

    # not in use (insecure)
    async def set_user_name(self, user_id, name):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(f'''
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