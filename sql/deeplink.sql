-- Step 1: Create a CTE to find the first available episode for each show
WITH FirstEpisodes AS (
    SELECT 
        show_id,
        MIN(season_no) AS first_season_no,
        MIN(episode_no) OVER (PARTITION BY show_id, season_no) AS first_episode_no,
        content_id AS episode_content_id,
        ROW_NUMBER() OVER (PARTITION BY show_id ORDER BY season_no, episode_no) AS row_num
    FROM 
        master_asset_table
    WHERE 
        type = 'Episode'
        AND country = 'US' -- Filter for the specific country
    GROUP BY 
        show_id, season_no, episode_no, content_id
),

-- Select only the first episode of the first season for each show
FirstAvailableEpisodes AS (
    SELECT 
        show_id,
        first_season_no,
        first_episode_no,
        episode_content_id
    FROM 
        FirstEpisodes
    WHERE 
        row_num = 1
),

-- Find shows with incorrect deeplink_payload
IncorrectShowDeeplinks AS (
    SELECT 
        s.content_id AS show_content_id,
        s.title AS show_title,
        s.deeplink_payload AS current_deeplink_payload,
        f.episode_content_id AS correct_episode_id,
        JSON_VALUE(s.deeplink_payload, '$.deeplink_data.content_id') AS current_deeplink_episode_id
    FROM 
        master_asset_table s
    JOIN 
        FirstAvailableEpisodes f ON s.content_id = f.show_id
    WHERE 
        s.type = 'Show'
        AND s.country = 'US'
        AND JSON_VALUE(s.deeplink_payload, '$.deeplink_data.content_id') != f.episode_content_id
),

-- Find seasons with incorrect deeplink_payload
IncorrectSeasonDeeplinks AS (
    SELECT 
        sea.content_id AS season_content_id,
        sea.title AS season_title,
        sea.show_id,
        sea.season_no,
        sea.deeplink_payload AS current_deeplink_payload,
        -- Find the first episode of this specific season
        (SELECT e.content_id 
         FROM master_asset_table e 
         WHERE e.type = 'Episode' 
         AND e.season_id = sea.content_id 
         AND e.country = 'US'
         ORDER BY e.episode_no ASC 
         FETCH FIRST 1 ROW ONLY) AS correct_episode_id,
        JSON_VALUE(sea.deeplink_payload, '$.deeplink_data.content_id') AS current_deeplink_episode_id
    FROM 
        master_asset_table sea
    WHERE 
        sea.type = 'Season'
        AND sea.country = 'US'
)

-- Oracle uses a different syntax for UPDATE with joins
-- Update Show deeplink_payload
MERGE INTO master_asset_table s
USING IncorrectShowDeeplinks i
ON (s.content_id = i.show_content_id AND s.country = 'US')
WHEN MATCHED THEN
UPDATE SET 
    deeplink_payload = JSON_TRANSFORM(
        s.deeplink_payload, 
        SET '$.deeplink_data.content_id' = i.correct_episode_id
    ),
    deeplink_id = i.correct_episode_id;

-- Update Season deeplink_payload
MERGE INTO master_asset_table s
USING (SELECT * FROM IncorrectSeasonDeeplinks WHERE correct_episode_id IS NOT NULL) i
ON (s.content_id = i.season_content_id AND s.country = 'US')
WHEN MATCHED THEN
UPDATE SET 
    deeplink_payload = JSON_TRANSFORM(
        s.deeplink_payload, 
        SET '$.deeplink_data.content_id' = i.correct_episode_id
    ),
    deeplink_id = i.correct_episode_id;

-- Generate a report of what was updated
SELECT 
    'Shows' AS entity_type,
    COUNT(*) AS records_updated
FROM 
    IncorrectShowDeeplinks
UNION ALL
SELECT 
    'Seasons' AS entity_type,
    COUNT(*) AS records_updated
FROM 
    IncorrectSeasonDeeplinks
WHERE 
    correct_episode_id IS NOT NULL;