<?php
	$servername = "";
	$username = "";
	$password = "";
	$dbname = "";
	
	// this blacklists a user from omdb
	// i added a thing to the admin dashboard for blacklisting later so this became unused

	$conn = new mysqli($servername, $username, $password, $dbname);
	if ($conn->connect_error) {
	  die("Connection failed: " . $conn->connect_error);
	}
	
	$userID = $argv[1];
	
	$conn->query("INSERT INTO `blacklist` VALUES ({$userID});");
	$conn->query("UPDATE `beatmaps` SET `ChartRank` = NULL, `ChartYearRank` = NULL, `Rating` = NULL, `Blacklisted` = '1', BlacklistReason = 'mapper has requested blacklist' WHERE `CreatorID`='{$userID}';");
	
	echo "Blacklisted user " . strval($userID) . "\n";
?>