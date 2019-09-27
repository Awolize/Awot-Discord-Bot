import sqlite3

DATABASE_NAME = "sqlite_stats.db"

class GameStatsDB(object):
    
    def __init__(self):
        self.connection = sqlite3.connect(DATABASE_NAME)
        self.cursor = self.connection.cursor()

    def __del__(self):
        self.cursor.close()
        self.connection.close()
        
    def commit(self):
        self.connection.commit() 

    def DROP_RECREATE_TABLES(self):
        # Open and read the file as a single buffer
        fin = open('stats_script.sql', 'r')
        sqlFile = fin.read()
        fin.close()

        # all SQL commands (split on ';')
        sqlCommands = sqlFile.split(';')
        for command in sqlCommands:
            try:
                self.cursor.execute(command)
            except Exception as e:
                print("Command skipped: {}".format(e))

        self.connection.commit()

    # -------------------------------------------------------------------------------
    #                                   Save data
    # -------------------------------------------------------------------------------
    def add_user(self, user_id: int, server_id: int, current_name: str) -> bool:

        # Set Current name in database
        success = True
        try:
            # Add user to users table
            sql = '''
                INSERT INTO users (user_id, current_name) 
                VALUES
                    (?, ?)'''
            task = (user_id, current_name)
            self.cursor.execute(sql, task)

            # Add user to server table
            sql = '''
                INSERT INTO servers (user_id, server_id) 
                VALUES
                    (?, ?)'''
            task = (user_id, server_id)
            self.cursor.execute(sql, task)

            # Add user to status table
            sql = '''
                INSERT INTO status (user_id) 
                VALUES
                    (?)'''
            task = (user_id, )
            self.cursor.execute(sql, task)

            # Add user to names table
            sql = '''
                INSERT INTO names (user_id, name) 
                VALUES
                    (?, ?)'''
            task = (user_id, current_name)
            self.cursor.execute(sql, task)

            

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> add_user() -> Exception: {}".format(e))
            success = False
        
        return success

    def get_user(self, user_id: int) -> tuple:
        
        # Set Current name in database
        success = True
        result = list()

        try:
            # SQL QUERY:
            sql = '''       
                SELECT * FROM users 
                WHERE 
                    user_id = ?'''
            # Variables:
            task = (user_id,)

            self.cursor.execute(sql, task)
            result = self.cursor.fetchall()

            if len(result) is 0:
                success = False

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> get_user() -> Exception: {}".format(e))
            success = False
        
        return (success, result)

    def add_nicknames_to_user(self, user_id: int, nicknames: list) -> bool:

        success = True
        try:
            for name in nicknames:
                sql = '''
                INSERT OR IGNORE INTO names (user_id, name)
                VALUES 
                    (?, ?);'''
                task = (user_id, name)
                self.cursor.execute(sql, task)

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> add_nicknames_to_user() -> Exception: {}".format(e))
            success = False

        return success

    def add_server_to_user(self, user_id: int, server_id: int) -> bool:
        
        success = True
        try:
            sql = '''
            INSERT OR REPLACE INTO servers (user_id, server_id)
            VALUES 
                (?, ?);'''
            task = (user_id, server_id)
            self.cursor.execute(sql, task)

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> add_server_to_user() -> Exception: {}".format(e))
            success = False

        return success

    def update_games_by_user_id(self, user_id: int, gamesNameList: list) -> bool:

        success = True
        try:
            for gameName, gameTime in gamesNameList:
                sql = '''
                INSERT OR REPLACE INTO games (user_id, game_name, time)
                VALUES 
                    (?, ?, ?);'''
                task = (user_id, gameName, gameTime)
                self.cursor.execute(sql, task)

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> update_games_by_user_id() -> Exception: {}".format(e))
            success = False

        return success

    def add_status_time_to_user_id(self, user_id: int, status: list) -> bool:

        success = True
        try:

            # SQL QUERY:
            sql = '''
            UPDATE status SET
                online = ?, 
                idle = ?, 
                busy = ?, 
                offline = ?
            WHERE
                user_id = ?'''
            # Variables:
            task = (status[0], status[1], status[2], status[3], user_id)

            self.cursor.execute(sql, task)

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> add_status_time_to_user_id() -> Exception: {}".format(e))
            success = False

        return success

    # -------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------
    #                                   Load data
    # -------------------------------------------------------------------------------

    def get_all_users(self) -> tuple:
        success = True
        result = list()
        try:
            self.cursor.execute("SELECT user_id FROM users")
            result = self.cursor.fetchall()

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> add_status_time_to_user_id() -> Exception: {}".format(e))
            success = False

        return (success, result)

    def get_all_nicknames(self, user_id) -> tuple:
        success = True
        result = list()
        try:
            sql = "SELECT name FROM names WHERE user_id = ?"
            task = (user_id, )
            self.cursor.execute(sql, task)
            result = self.cursor.fetchall()

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> get_all_nicknames() -> Exception: {}".format(e))
            success = False

        return (success, result)

    def get_all_games(self, user_id) -> tuple:
        success = True
        result = list()

        try:
            sql = "SELECT game_name, time FROM games WHERE user_id = ?"
            task = (user_id, )

            self.cursor.execute(sql, task)
            result = self.cursor.fetchall()

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> get_all_games() -> Exception: {}".format(e))
            success = False

        return (success, result)

    def get_all_status(self, user_id) -> tuple:
        success = True

        try:
            sql = "SELECT online, idle, busy, offline FROM status WHERE user_id = ?"
            task = (user_id, )

            self.cursor.execute(sql, task)
            result = self.cursor.fetchone()

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> get_all_status() -> Exception: {}".format(e))
            success = False

        return (success, result)

    def get_all_servers(self, user_id) -> tuple:
        success = True

        try:
            sql = "SELECT server_id FROM servers WHERE user_id = ?"
            task = (user_id, )

            self.cursor.execute(sql, task)
            result = self.cursor.fetchall()

        except Exception as e:
            print("[Error] game_stats_db_handler.py -> get_all_servers() -> Exception: {}".format(e))
            success = False

        return (success, result)

'''
CREATE TABLE games (
  user_id integer NOT NULL,
  game_name text NOT NULL,
  time integer NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, game_name),
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
'''

# recreate table
if __name__ == "__main__":
    '''
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = self.connection.cursor()
    self.cursor.execute()
    '''
    
    mydb = GameStatsDB()
    mydb.DROP_RECREATE_TABLES()
    #add_user()
