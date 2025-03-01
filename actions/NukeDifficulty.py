import mysql.connector
from datetime import datetime
import time
from ossapi import *
import sys

# this script literally removes a beatmap
# usually this was done cuz graveyard->ranked maps had some stupid differences and i was too lazy to fix

def delete_data(cursor, cnx, beatmapset_id):
    vals = (beatmapset_id,)
    print("DELETING", vals)
    
    cursor.execute(sql_delete_ratings, vals)
    cursor.execute(sql_delete_beatmap_creators, vals)
    cursor.execute(sql_delete_descriptor_votes, vals)
    cursor.execute(sql_delete_list_item_beatmaps, vals)
    cursor.execute(sql_delete_beatmap, vals)
    
    cnx.commit()

# Sensitive strings - database stuff and APIv2 stuff.
DatabaseUser=''
DatabasePassword=''
DatabaseHost=''
DatabaseTable=''

# Set up the connection to the database
cnx = mysql.connector.connect(user=DatabaseUser,
                              password=DatabasePassword,
                              host=DatabaseHost,
                              database=DatabaseTable)
cursor = cnx.cursor()


api = Ossapi("", "")

sql_delete_ratings = "DELETE FROM ratings WHERE BeatmapID = %s;"
sql_delete_beatmap_creators = "DELETE FROM beatmap_creators WHERE BeatmapID = %s;"
sql_delete_descriptor_votes = "DELETE FROM descriptor_votes WHERE BeatmapID = %s;"
sql_delete_list_item_beatmaps = "DELETE FROM list_items WHERE SubjectID = %s AND Type = 'beatmap';"
sql_delete_beatmap = "DELETE FROM beatmaps WHERE BeatmapID = %s"

arguments = sys.argv

if len(sys.argv) <= 1:
    print('need more than 1 arg')
    sys.exit(0)
    
beatmapId = sys.argv[1]

try:
    beatmap = api.beatmap(beatmap_id=beatmapId)
    if (beatmap.status.value == 2 or beatmap.status.value == 1 or beatmap.status.value == 4):
        print('not deleting')
        sys.exit(0)
        
    delete_data(cursor, cnx, beatmapId)
except ValueError as e:
    if ("api returned an error of `None`" in str(e)):
        print("Has been deleted from osu!")
        delete_data(cursor, cnx, beatmapId)
    else:
        print(e)
        sys.exit(0)