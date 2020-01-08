import asyncio
import asyncpg
import datetime

import config


async def main():
    # Establish a connection to an existing database named "test"
    # as a "postgres" user.
    try:
        conn = await asyncpg.connect(database="Awot", user='postgres', password="ad.*FRc`%;&W*2sZ")
        # Execute a statement to create a new table.

        await conn.execute('''
            DROP TABLE IF EXISTS usera;
            CREATE TABLE usera (
            user_id integer NOT NULL,
            current_name text,
            PRIMARY KEY (user_id)
            );
        ''')

        # Insert a record into the created table.
        await conn.execute('''
            INSERT INTO "Awot"."public"."usera" (current_name, user_id)
            VALUES
            ('current_name:text', user_id:integer);

            INSERT INTO usera(user_id, current_name) 
            VALUES
            ($1, $2)
        ''', 1, 'Bob')

        # Select a row from the table.
        row = await conn.fetchrow(
            'SELECT * FROM usera WHERE current_name = $1', 'Bob')
        # *row* now contains
        # asyncpg.Record(id=1, name='Bob', dob=datetime.date(1984, 3, 1))
    except Exception as e:
        print(f"{e}")

    # Close the connection.
    await conn.close()


asyncio.get_event_loop().run_until_complete(main())
