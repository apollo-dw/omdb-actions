<?php
	$servername = "";
	$username = "";
	$password = "";
	$dbname = "";
	
	// this script seems to manually add a set to omdb
	// i cant remember the context of why this exists

	$conn = new mysqli($servername, $username, $password, $dbname);
	if ($conn->connect_error) {
	  die("Connection failed: " . $conn->connect_error);
	}
	
	$mapsetID = $argv[1];
	
	$MyApiKey = "";
	$lastSince = "";
	$since = $conn->query("SELECT `LastDate` FROM `setretrieveinfo`;")->fetch_row()[0];
	$until = date("Y-m-d", strtotime('tomorrow'));
	
	$curl = curl_init();

	curl_setopt_array($curl, array(
	  CURLOPT_URL => "https://osu.ppy.sh/api/get_beatmaps?k=${MyApiKey}&s=${mapsetID}",
	  CURLOPT_HTTPHEADER => ['Accept: application/json', 'Content-Type: application/json'],
	  CURLOPT_RETURNTRANSFER => true,
	  CURLOPT_ENCODING => '',
	  CURLOPT_MAXREDIRS => 10,
	  CURLOPT_TIMEOUT => 0,
	  CURLOPT_FOLLOWLOCATION => true,
	  CURLOPT_HTTP_VERSION => CURL_HTTP_VERSION_1_1,
	  CURLOPT_CUSTOMREQUEST => 'GET',
	));

	$response = curl_exec($curl);
	curl_close($curl);

	$array = json_decode($response, true);
	
	$stmt = $conn->prepare("INSERT INTO `beatmaps` (DateRanked, Artist, BeatmapID, SetID, CreatorID, SR, CS, OD, AR, HP, Source, Genre, Lang, Title, DifficultyName, Mode, Timestamp)
	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);");
	$stmt->bind_param("ssiiidddddsiissis", $dateRanked, $artist, $beatmapID, $setID, $creatorID, $SR, $CS, $OD, $AR, $HP, $source, $genre, $lang, $title, $difficultyName, $mode, $timestamp);
	
	foreach($array as $diff){
		if($diff["approved"] == 3){
			echo "Map ${diff["beatmap_id"]} is not ranked/approved/loved, skipping...\n";
			continue;
		}
		
		if($conn->query("SELECT * FROM `beatmaps` WHERE `BeatmapID`='${diff["beatmap_id"]}';")->num_rows > 0){
			echo "Map ${diff["beatmap_id"]} is already in database, skipping...\n";
			continue;
		}
		
		$dateRanked = date("Y-m-d", strtotime($diff["approved_date"]));
		$artist = $diff["artist"];
		$beatmapID = $diff["beatmap_id"];
		$setID = $diff["beatmapset_id"];
		$creatorID = $diff["creator_id"];
		$SR = $diff["difficultyrating"];
		$CS = $diff["diff_size"];
		$OD = $diff["diff_overall"];
		$AR = $diff["diff_approach"];
		$HP = $diff["diff_drain"];
		$source = $diff["source"];
		$genre = $diff["genre_id"];
		$lang = $diff["language_id"];
		$title = $diff["title"];
		$difficultyName = $diff["version"];
		$mode = $diff["mode"];
		$timestamp = $diff["approved_date"];
		$stmt->execute();
		echo "Added beatmap ${beatmapID} successfully!\n";
	}
	
	$stmt->close();
?>