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
    cursor.execute('CREATE TABLE dates (id INTEGER PRIMARY KEY, day int, month int, year int)')
    connection.commit()
    connection.close()


def addBirthdayToDatabase(date, id: int):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = '''
        INSERT INTO dates (day, month, year, id) 
        VALUES
        (?, ?, ?, ?)'''
        
    task = (date.day, date.month, date.year, id)

    success = True
    try:
        cursor.execute(sql, task)
    except Exception as e:
        print(e)
        success = False

    connection.commit()
    connection.close()
    return success

def getBirthdayByID(id):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = "SELECT day, month, year FROM dates WHERE id = ?"
    task = (id,)
    cursor.execute(sql, task)
    result = cursor.fetchall()
    connection.close()
    return result

def getBirthdayByDate(day: int, month: int):
    connection = sqlite3.connect('sqlite3_calender.db')
    cursor = connection.cursor()

    sql = "SELECT id, day, month, year FROM dates WHERE day = ? and month = ?"
    task = (day, month)
    cursor.execute(sql, task)
    result = cursor.fetchall() 

    connection.close()
    return result