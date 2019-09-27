import sqlite3

'''
connection = sqlite3.connect('sqlite3_calender.db')
cursor = connection.cursor()

#cursor.execute('DROP TABLE IF EXISTS dates')
#cursor.execute('CREATE TABLE dates (id INTEGER PRIMARY KEY AUTOINCREMENT, d date, name TEXT)')

cursor.execute('INSERT INTO dates(d, name) VALUES(?, ?)', ('1997-09-03', 'Alexander'))

connection.commit()
connection.close()
'''

'''
if __name__ == "__main__":
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    #cursor.execute('DROP TABLE IF EXISTS dates')
    cursor.execute('CREATE TABLE dates (member TEXT PRIMARY KEY')
'''


# recreate table
if __name__ == "__main__":
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()
    cursor.execute('DROP TABLE IF EXISTS dates')
    cursor.execute('CREATE TABLE dates (serverid INTEGER , userid INTEGER, day INTEGER, month INTEGER, year INTEGER, primary key (serverid, userid))')
    connection.commit()
    connection.close()


def addBirthdayToDatabase(serverid: int, userid: int, day: int, month: int, year: int):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = '''
        INSERT INTO dates (serverid, userid, day, month, year) 
        VALUES
            (?, ?, ?, ?, ?)'''
        
    task = (serverid, userid, day, month, year)

    success = True
    try:
        cursor.execute(sql, task)
    except Exception as e:
        print(e)
        success = False

    connection.commit()
    connection.close()
    return success

def getBirthdayByID(userid, serverid):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = "SELECT day, month, year FROM dates WHERE userid = ? AND serverid = ?"
    task = (userid, serverid)
    cursor.execute(sql, task)
    result = cursor.fetchall()
    connection.close()
    return result

def getBirthdayByDate(serverid: int, day: int, month: int):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = "SELECT userid, day, month, year FROM dates WHERE day = ? and month = ? AND serverid = ?"
    task = (day, month, serverid)
    cursor.execute(sql, task)
    result = cursor.fetchall() 

    connection.close()
    return result

def removeBirthdayByID(userid, serverid):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = "DELETE FROM dates WHERE userid = ? AND serverid = ?"
    task = (userid, serverid)
    cursor.execute(sql, task)
    result = cursor.fetchall()
    connection.commit()
    connection.close()
    return result

def testit():
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = "SELECT * FROM dates"
    task = ("",)
    cursor.execute(sql)
    result = cursor.fetchall() 

    connection.close()
    return result
