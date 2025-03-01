<?php
function calculateEntropy($arr){
    $total = array_sum($arr);
    if ($total == 0)
        return 0;

    $entropy = 0;
    $probabilities = [];

    foreach ($arr as $rating) {
        $probabilities[] = $rating / $total;
    }

    foreach ($probabilities as $probability) {
        if ($probability > 0) {
            $entropy -= $probability * log($probability, 2);
        }
    }

    return $entropy;
}
$time_start = microtime(true);
set_time_limit(300);


$servername = "";
$username = "";
$password = "";
$dbname = "";

// chart update script
// this isn't good for sure but hooray. ok like really why is this in php. was i smoking crack_check
// actually no i remember i attempted to convert to python and i was like ughh
// this ran on a once-every-day cron

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

echo (microtime(true) - $time_start) . ": calculating user weighting\n";

$ratingsQuery = $conn->prepare("SELECT `UserID`, `Score`, COUNT(*) as count FROM `ratings` GROUP BY `UserID`, `Score`");
$ratingsQuery->execute();
$ratingsResult = $ratingsQuery->get_result();

$ratingsData = [];
while ($row = $ratingsResult->fetch_assoc()) {
    $ratingsData[$row['UserID']][$row['Score']] = $row['count'];
}

$deweightedUsers = []; // i used this for users who were abusing rating / clearly going against the spirit of the site. redacted for vibes here

$userQueryStatement = $conn->prepare("SELECT `UserID`, `LastAccessedSite` FROM `users`");
$userQueryStatement->execute();
$userQueryResult = $userQueryStatement->get_result();

$updateStatement = $conn->prepare("UPDATE `users` SET `Weight` = ? WHERE `UserID` = ?");

$blacklistQueryStatement = $conn->prepare("SELECT `UserID` FROM `blacklist`");
$blacklistQueryStatement->execute();
$blacklistedUsers = $blacklistQueryStatement->get_result()->fetch_all(MYSQLI_ASSOC);
$blacklistedUsers = array_column($blacklistedUsers, 'UserID');

while ($row = $userQueryResult->fetch_assoc()) {
    $userID = $row["UserID"];
    $totalWeight = 0;

    if (in_array($userID, $deweightedUsers)) {
        $totalWeight = 0;
    } else {
        $entropy = calculateEntropy($ratingsData[$userID] ?? []);
        $total = array_sum($ratingsData[$userID] ?? []);
        $countWeight = min(1, $total / 50);

        $lastAccessedTimestamp = strtotime($row["LastAccessedSite"]);
        $inactiveWeight = ($lastAccessedTimestamp < strtotime('-90 days')) ? 0.7 : 1;
		$blacklistedWeight = (in_array($userID, $blacklistedUsers)) ? 0.01 : 1.0;

        $totalWeight = max(0.1, pow(min(1, $entropy / 2.3), 3) * $countWeight * $inactiveWeight) * $blacklistedWeight;
    }

    $updateStatement->bind_param("di", $totalWeight, $userID);
    $updateStatement->execute();
}

for($mode = 0; $mode <= 3; $mode++){
    echo (microtime(true) - $time_start) . ": calculating ratings for gamemode " . strval($mode) . "\n";

    $m = $conn->query("SELECT AVG(r.Score) AS AverageRating FROM ratings r;")->fetch_row()[0]; // average of all beatmaps

    if($mode == 0){
        $MinimumRatingCount = 5;
        $confidence = 24;
    }
    else {
        $MinimumRatingCount = 2;
        $confidence = 5;
    }

    $stmt1 = $conn->prepare("SELECT b.BeatmapID FROM beatmaps b WHERE Blacklisted = 0 AND Mode = ?;");
    $stmt1->bind_param("i", $mode);
    $stmt1->execute();
    $resultBeatmaps = $stmt1->get_result();

    $query = "SELECT SUM(r.Score * u.Weight) / SUM(u.Weight) AS weighted_avg, SUM(u.Weight) AS weight_sum, COUNT(*) AS rating_count FROM ratings r INNER JOIN users u ON r.UserID = u.UserID WHERE r.BeatmapID = ?";
    $stmt = $conn->prepare($query);
    $query4 = "UPDATE beatmaps SET Rating = ?, WeightedAvg = ?, RatingCount = ? WHERE BeatmapID = ?";
    $stmt4 = $conn->prepare($query4);

    while ($rowBeatmap = $resultBeatmaps->fetch_assoc()) {
        $bID = $rowBeatmap['BeatmapID'];
        $stmt->bind_param("i", $bID);
        $stmt->execute();
        $result = $stmt->get_result();

        $row = $result->fetch_assoc();
        $avg = $row['weighted_avg'];
        $weightedCount = $row['weight_sum'];
        $count = $row['rating_count'];

        if ($weightedCount < 1.5) {
            $bayesian = null;
        } else {
            $bayesian = (($weightedCount * $avg) + ($m * $confidence)) / ($weightedCount + $confidence);
			
			if ($weightedCount < 20 && $mode == 0) {
				$interp_factor = pow((max(1, min($weightedCount, 20)) - 1) / 19.0, 3);
				$bayesian = 2.9 + $interp_factor * ($bayesian - 2.9);
			}
        }

        $stmt4->bind_param("ddii", $bayesian, $avg, $count, $bID);
        $stmt4->execute();
    }

    $stmt5 = $conn->prepare("SELECT BeatmapID, YEAR(DateRanked) as Year FROM beatmaps b JOIN beatmapsets s ON s.SetID = b.SetID WHERE Rating IS NOT NULL AND Blacklisted = 0 AND RatingCount >= $MinimumRatingCount AND Mode = ? ORDER BY Rating DESC;");
    $stmt5->bind_param("i", $mode);
    $stmt5->execute();
    $result = $stmt5->get_result();

    $RankCounter = 1;
    $YearRankCounter = array(
        "2007" => 1,
        "2008" => 1,
        "2009" => 1,
        "2010" => 1,
        "2011" => 1,
        "2012" => 1,
        "2013" => 1,
        "2014" => 1,
        "2015" => 1,
        "2016" => 1,
        "2017" => 1,
        "2018" => 1,
        "2019" => 1,
        "2020" => 1,
        "2021" => 1,
        "2022" => 1,
        "2023" => 1,
        "2024" => 1,
		"2025" => 1,
    );

    echo (microtime(true) - $time_start) . ": caching chart information\n";

    $query6 = "UPDATE beatmaps SET ChartRank = ?, ChartYearRank = ? WHERE BeatmapID = ?";
    $stmt6 = $conn->prepare($query6);

    while ($row = $result->fetch_assoc()) {
        $beatmapYear = $row["Year"];
        $beatmapId = $row["BeatmapID"];

        $rankValue = $RankCounter;
        if ($RankCounter >= 10000) {
            $rankValue = null;
        }

        $yearRankValue = $YearRankCounter[$beatmapYear];
        if ($YearRankCounter[$beatmapYear] >= 10000) {
            $yearRankValue = null;
			break;
        }

        $stmt6->bind_param("iii", $rankValue, $YearRankCounter[$beatmapYear], $beatmapId);
        $stmt6->execute();

        $RankCounter += 1;
        $YearRankCounter[$beatmapYear] += 1;
    }

    echo (microtime(true) - $time_start) . ": removing unrated beatmaps from charts\n";
    $conn->query("UPDATE `beatmaps` SET `ChartRank` = NULL, `ChartYearRank` = NULL WHERE `RatingCount` <= $MinimumRatingCount;");

    echo (microtime(true) - $time_start) . ": calculating controversy\n";

    $query = $conn->query("UPDATE beatmaps
    SET controversy = (
        SELECT -SUM(ratings.Count / total_count * LOG(ratings.Count / total_count)) AS entropy
        FROM (
            SELECT BeatmapID, Score, COUNT(*) AS Count
            FROM ratings
            GROUP BY BeatmapID, Score
        ) ratings
        JOIN (
            SELECT BeatmapID, COUNT(*) AS total_count
            FROM ratings
            GROUP BY BeatmapID
        ) total_counts ON ratings.BeatmapID = total_counts.BeatmapID
        WHERE ratings.BeatmapID = beatmaps.BeatmapID
        GROUP BY ratings.BeatmapID
    )
    WHERE BeatmapID IN (
        SELECT BeatmapID
        FROM (
            SELECT BeatmapID, COUNT(*) AS total_count
            FROM ratings
            GROUP BY BeatmapID
        ) total_counts
        WHERE total_count > {$MinimumRatingCount}
    );");
}

echo (microtime(true) - $time_start) . ": caching best maps for each mode\n";

$conn->query("DELETE FROM cache_home_best_map;");
$fetch_stmt = $conn->prepare("SELECT BeatmapID, DateRanked, Rating FROM beatmaps b
									JOIN beatmapsets s ON s.SetID = b.SetID
								   WHERE
										DateRanked >= DATE_SUB(NOW(), INTERVAL WEEKDAY(NOW()) + 7 DAY) 
										AND DateRanked < DATE_SUB(NOW(), INTERVAL WEEKDAY(NOW()) DAY)
										AND Rating IS NOT NULL
										AND Mode = ?
								   ORDER BY
										Rating DESC
								   LIMIT 1;");
$insert_stmt = $conn->prepare("INSERT INTO cache_home_best_map (BeatmapID, Mode) VALUES (?, ?);");

for ($mode = 0; $mode < 4; $mode++) {
	$fetch_stmt->bind_param("i", $mode);
	$fetch_stmt->execute();
	$result = $fetch_stmt->get_result();
	$beatmap = $result->fetch_assoc();

	if (is_null($beatmap))
		continue;

	$insert_stmt->bind_param("ii", $beatmap["BeatmapID"], $mode);
	$insert_stmt->execute();
}
$insert_stmt->close();
$fetch_stmt->close();

echo 'Total execution time in seconds: ' . (microtime(true) - $time_start);