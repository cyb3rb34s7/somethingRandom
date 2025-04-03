-- Create temporary table with first episodes (more efficient than CTEs)
CREATE GLOBAL TEMPORARY TABLE temp_first_episodes AS
SELECT 
    show_id,
    MIN(season_no) AS first_season_no,
    content_id AS episode_content_id
FROM (
    SELECT 
        show_id, season_no, episode_no, content_id,
        ROW_NUMBER() OVER (PARTITION BY show_id ORDER BY season_no, episode_no) AS row_num
    FROM master_asset_table
    WHERE type = 'Episode' AND country = 'US'
)
WHERE row_num = 1
GROUP BY show_id, content_id;

-- Update shows (more targeted than MERGE)
UPDATE master_asset_table s
SET 
    deeplink_payload = JSON_TRANSFORM(s.deeplink_payload, SET '$.deeplink_data.content_id' = e.episode_content_id),
    deeplink_id = e.episode_content_id
WHERE s.type = 'Show'
AND s.country = 'US'
AND EXISTS (
    SELECT 1 
    FROM temp_first_episodes e 
    WHERE s.content_id = e.show_id
    AND JSON_VALUE(s.deeplink_payload, '$.deeplink_data.content_id') != e.episode_content_id
);

-- Similar approach for seasons