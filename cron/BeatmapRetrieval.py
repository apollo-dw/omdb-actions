import mysql.connector
import datetime
from ossapi import *

rulesets = {
    "osu": 0,
    "taiko": 1,
    "fruits": 2,
    "mania": 3,
}

DatabaseUser=''
DatabasePassword=''
DatabaseHost=''
DatabaseTable=''

# retrieves new ranked/loved beatmaps
# this ran on a once-every-hour cron

cnx = mysql.connector.connect(user=DatabaseUser,
                              password=DatabasePassword,
                              host=DatabaseHost,
                              database=DatabaseTable)
cursor = cnx.cursor()


api = Ossapi("", "")

cursor.execute("SELECT Timestamp FROM beatmaps ORDER BY Timestamp DESC LIMIT 0, 1;")
LatestDbMap = cursor.fetchall()[0]
LatestAddedDate = LatestDbMap[0]

sql_beatmap_creators = "INSERT INTO beatmap_creators (BeatmapID, CreatorID) VALUES (%s, %s);"
sql_beatmaps = "REPLACE INTO beatmaps (BeatmapID, SetID, SR, DifficultyName, Mode, Status, Blacklisted, BlacklistReason) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
sql_beatmapsets = "REPLACE INTO beatmapsets (DateRanked, Artist, SetID, CreatorID, Genre, Lang, Title, Status, HasStoryboard, HasVideo) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"
sql_beatmapset_nominators = "INSERT INTO beatmapset_nominators (SetID, NominatorID, Mode) VALUES (%s, %s, %s);" 

while True:
    print("Latest date is..." + str(LatestAddedDate))
    beatmapsets = api.search_beatmapsets(query=f"ranked>\"{LatestAddedDate}\"", sort="ranked_asc", explicit_content="show").beatmapsets
    if len(beatmapsets) == 0:
        print("we are done sir")
        break
    
    for set in beatmapsets:
        display_date = set.ranked_date
        if str(set.ranked) == "RankStatus.LOVED":
            display_date = set.submitted_date
            
        fullSet = api.beatmapset(set)
        
        for nomination in fullSet.current_nominations:
            userID = nomination.user_id
            for ruleset in nomination.rulesets:
                try:
                    vals = (fullSet.id, userID, rulesets[ruleset])
                    cursor.execute(sql_beatmapset_nominators, vals)
                    cnx.commit()
                except Exception as e:
                    print(f"Error occurred with inserting set {fullSet.id}: {e}")
                    
        #DateRanked, Artist, SetID, CreatorID, Genre, Lang, Title, Status, HasStoryboard, HasVideo
        val = (display_date.strftime('%Y-%m-%d %H:%M:%S'), # DateRanked,
               set.artist, # Artist
               set.id, # SetID
               set.user_id, # SetCreatorID
               fullSet.genre["id"], # Genre
               fullSet.language["id"], # Lang
               set.title, # Title
               set.status.value, # Status
               fullSet.storyboard,
               fullSet.video
               )
               
        try:
            cursor.execute(sql_beatmapsets, val)
            cnx.commit()
            print(f"Inserted set {set.id}")
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

            creator_val = (map.id, map.user_id)
            try:
                cursor.execute(sql_beatmap_creators, creator_val)
                cnx.commit()
            except:
                print(f"Error occurred with inserting set creators set {set.id} map {map.id}")

            #BeatmapID, SetID, SR, DifficultyName, Mode, Status, Blacklisted, BlacklistReason
            val = (map.id, # BeatmapID
                   set.id, # SetID
                   map.difficulty_rating, # SR
                   map.version, # Difficulty Name
                   map.mode_int, # Mode
                   map.status.value, # Status
                   blacklisted, # Blacklisted
                   blacklist_reason # BlacklistReason
                   )

            try:
                cursor.execute(sql_beatmaps, val)
                cnx.commit()
                print(f"Inserted set {set.id} => map {map.id}")
            except Exception as error:
                print(f"Error occurred with set {set.id} => map {map.id}", error)
                
            LatestAddedDate = set.ranked_date.strftime('%Y-%m-%d %H:%M:%S')

    
clear_cache_query = "DELETE FROM cache_home_recent_maps;"
cursor.execute(clear_cache_query)
cnx.commit()

for mode in range(4):
    used_sets = []
    cursor.execute("SELECT s.SetID, Artist, Title, CreatorID, DateRanked, b.Timestamp FROM beatmaps b JOIN beatmapsets s ON b.SetID = s.SetID WHERE Mode = %s ORDER BY b.Timestamp DESC LIMIT 200;", (mode,))

    for row in cursor.fetchall():
        if row[0] in used_sets:
            continue
        if len(used_sets) >= 8:
            break

        metadata = f"{row[1]} - {row[2]}"
        cache_insert_query = "INSERT INTO cache_home_recent_maps (SetID, Timestamp, Metadata, CreatorID, Mode) VALUES (%s, %s, %s, %s, %s);"
        cache_data = (row[0], row[5], metadata, row[3], mode)
        cursor.execute(cache_insert_query, cache_data)
        used_sets.append(row[0])

cnx.commit()   

print("done")

cursor.close()
cnx.close()
