import mysql.connector
from datetime import datetime
import time
from ossapi import *

# ok, so this script goes through all graveyarded sets and basically checks to see if they have been updated or removed, and then removes them from omdb.
# in theory it'd be better if this check was done whenever a rating is made on a graveyarded maps.
# also if u add notifications then a beatmap/set being removed from omdb should be a notification for sure.,

def is_within_last_six_months(date_object):
    current_date = datetime.now(date_object.tzinfo)
    time_difference = current_date - date_object
    return time_difference.total_seconds() <= 180 * 24 * 60 * 60

rulesets = {
    "osu": 0,
    "taiko": 1,
    "fruits": 2,
    "mania": 3,
}

def delete_data(cursor, cnx, beatmapset_id):
    vals = (beatmapset_id,)
    print("DELETING", vals)
    
    cursor.execute(sql_delete_ratings, vals)
    cursor.execute(sql_delete_beatmap_creators, vals)
    cursor.execute(sql_delete_descriptor_votes, vals)
    cursor.execute(sql_delete_list_item_beatmaps, vals)
    
    cnx.commit()

    cursor.execute(sql_delete_list_item_beatmapsets, vals)
    cursor.execute(sql_delete_comments, vals)
    cursor.execute(sql_delete_beatmaps, vals)
    cursor.execute(sql_delete_beatmapsets, vals)
    
    cnx.commit()

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

sql_delete_ratings = "DELETE FROM ratings WHERE BeatmapID IN (SELECT BeatmapID FROM beatmaps WHERE SetID = %s);"
sql_delete_beatmap_creators = "DELETE FROM beatmap_creators WHERE BeatmapID IN (SELECT BeatmapID FROM beatmaps WHERE SetID = %s);"
sql_delete_descriptor_votes = "DELETE FROM descriptor_votes WHERE BeatmapID IN (SELECT BeatmapID FROM beatmaps WHERE SetID = %s);"
sql_delete_list_item_beatmaps = "DELETE FROM list_items WHERE SubjectID IN (SELECT BeatmapID FROM beatmaps WHERE SetID = %s) AND Type = 'beatmap';"
sql_delete_list_item_beatmapsets = "DELETE FROM list_items WHERE SubjectID = %s AND Type = 'beatmapset';"
sql_delete_comments = "DELETE FROM comments WHERE SetID = %s;"
sql_delete_beatmapsets = "DELETE FROM beatmapsets WHERE SetID = %s"
sql_delete_beatmaps = "DELETE FROM beatmaps WHERE SetID = %s"

sql_update_beatmaps = "UPDATE beatmaps SET SetID=%s, SR=%s, DifficultyName=%s, Mode=%s, Status=%s, Blacklisted=%s, BlacklistReason=%s WHERE BeatmapID=%s;"
sql_update_beatmapsets = "UPDATE beatmapsets SET DateRanked=%s, Artist=%s, CreatorID=%s, Genre=%s, Lang=%s, Title=%s, Status=%s, HasStoryboard=%s, HasVideo=%s WHERE SetID=%s;"

cursor.execute("SELECT SetID FROM beatmapsets WHERE Status = -2 AND Timestamp < '2022-11-21 00:00:00' ORDER BY Timestamp DESC;")
beatmapsets = cursor.fetchall()

for beatmapset in beatmapsets:
    try:
        print("====")
        set = api.beatmapset(beatmapset_id=beatmapset[0])
        print(set.id, set.last_updated, set.status)
        if (set.status.value == -1 or set.status.value == 0):
            print("Moved out of graveyard!")
            delete_data(cursor, cnx, beatmapset[0])
        if (set.status.value == 4 or set.status.value == 1):
            print("Loved! Or Ranked!")
            display_date = set.ranked_date
            if set.status.value == 4:
                display_date = set.submitted_date

            set_val = (display_date.strftime('%Y-%m-%d %H:%M:%S'), # DateRanked,
               set.artist, # Artist
               set.user_id, # SetCreatorID
               set.genre["id"], # Genre
               set.language["id"], # Lang
               set.title, # Title
               set.status.value, # Status
               set.storyboard,
               set.video,
               set.id,
               )

            try:
                cursor.execute(sql_update_beatmapsets, set_val)
                cnx.commit()
                print(f"Updated set {set.id}")
            except Exception as error:
                print(f"Error occurred with set {set.id}", error)

            for map in set.beatmaps:
                cursor.execute("SELECT * FROM blacklist WHERE UserID = '" + str(map.user_id) + "';")
                result = cursor.fetchone()
                
                if result:
                    blacklisted = 1
                    blacklist_reason = "mapper has requested blacklist"
                else:
                    blacklisted = 0
                    blacklist_reason = None

                # Insert data into beatmap_creators
                creator_val = (map.id, map.user_id)
                try:
                    cursor.execute(sql_beatmap_creators, creator_val)
                    cnx.commit()
                except:
                    print(f"Error occurred with inserting set creators set {set.id} map {map.id}")

                map_val = (set.id, # SetID
                       map.difficulty_rating, # SR
                       map.version, # Difficulty Name
                       map.mode_int, # Mode
                       map.status.value, # Status
                       blacklisted, # Blacklisted
                       blacklist_reason, # BlacklistReason
                       map.id # BeatmapID
                       )

                try:
                    cursor.execute(sql_update_beatmaps, map_val)
                    cnx.commit()
                    print(f"Inserted set {set.id} => map {map.id}")
                except Exception as error:
                    print(f"Error occurred with set {set.id} => map {map.id}", error)
                
    except ValueError as e:
        if ("api returned an error of `None`" in str(e)):
            print("Has been deleted from osu!")
            delete_data(cursor, cnx, beatmapset[0])
        else:
            print(e)
        continue
    time.sleep(0.8)
    
print("done")

cursor.close()
cnx.close()
