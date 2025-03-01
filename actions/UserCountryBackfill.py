import mysql.connector
import datetime
import time
from ossapi import *

rulesets = {
    "osu": 0,
    "taiko": 1,
    "fruits": 2,
    "mania": 3,
}

# this one backfills the country field on user profiles

DatabaseUser=''
DatabasePassword=''
DatabaseHost=''
DatabaseTable=''

cnx = mysql.connector.connect(user=DatabaseUser,
                              password=DatabasePassword,
                              host=DatabaseHost,
                              database=DatabaseTable)
cursor = cnx.cursor()


api = Ossapi("", "")

cursor.execute("SELECT UserID FROM mappernames WHERE Country is NULL;")
users = cursor.fetchall()

sql_country = "UPDATE mappernames SET Country = %s WHERE UserID = %s;"

def update_user_countries(user_ids, cursor, cnx):
    user_objects = api.users(user_ids)
    for osuUser in user_objects:
        try:
            cursor.execute(sql_country, (osuUser.country_code, osuUser.id))
            print("ID " + str(osuUser.id) + " country: " + osuUser.country_code)
        except Exception as error:
            print(error)
            pass
    cnx.commit()

batch_size = 50
for i in range(0, len(users), batch_size):
    batch_users = [user[0] for user in users[i:i+batch_size]]
    update_user_countries(batch_users, cursor, cnx)
    time.sleep(2)

print("done")

cursor.close()
cnx.close()
