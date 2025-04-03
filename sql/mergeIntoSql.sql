-- Oracle-compatible solution for updating show deeplink payloads

-- Method 1: Using a temporary table approach (most reliable in Oracle)
-- Step 1: Create a temporary table for first episodes
CREATE GLOBAL TEMPORARY TABLE temp_first_episodes (
    show_id VARCHAR2(100),
    episode_content_id VARCHAR2(100)
) ON COMMIT PRESERVE ROWS;

-- Step 2: Insert the data into the temporary table
INSERT INTO temp_first_episodes
SELECT 
    show_id,
    content_id AS episode_content_id
FROM (
    SELECT 
        show_id, content_id,
        ROW_NUMBER() OVER (PARTITION BY show_id ORDER BY season_no, episode_no) AS row_num
    FROM master_asset_table
    WHERE type = 'Episode' AND country = 'US'
)
WHERE row_num = 1;

-- Step 3: Update the shows using the temporary table
UPDATE master_asset_table s
SET 
    deeplink_payload = JSON_TRANSFORM(
        s.deeplink_payload, 
        SET '$.deeplink_data.content_id' = (
            SELECT fe.episode_content_id 
            FROM temp_first_episodes fe 
            WHERE s.content_id = fe.show_id
        )
    ),
    deeplink_id = (
        SELECT fe.episode_content_id 
        FROM temp_first_episodes fe 
        WHERE s.content_id = fe.show_id
    )
WHERE 
    s.type = 'Show'
    AND s.country = 'US'
    AND EXISTS (
        SELECT 1 
        FROM temp_first_episodes fe 
        WHERE s.content_id = fe.show_id
        AND JSON_VALUE(s.deeplink_payload, '$.deeplink_data.content_id') != fe.episode_content_id
    );

COMMIT;

-- Method 2: Alternative using MERGE statement (also reliable in Oracle)
MERGE INTO master_asset_table s
USING (
    SELECT 
        e.show_id,
        e.content_id AS episode_content_id
    FROM (
        SELECT 
            show_id, content_id,
            ROW_NUMBER() OVER (PARTITION BY show_id ORDER BY season_no, episode_no) AS row_num
        FROM master_asset_table
        WHERE type = 'Episode' AND country = 'US'
    ) e
    WHERE e.row_num = 1
) fe
ON (s.content_id = fe.show_id AND s.type = 'Show' AND s.country = 'US')
WHEN MATCHED THEN
    UPDATE SET 
        deeplink_payload = 
            CASE
                WHEN JSON_VALUE(s.deeplink_payload, '$.deeplink_data.content_id') != fe.episode_content_id
                THEN JSON_TRANSFORM(s.deeplink_payload, SET '$.deeplink_data.content_id' = fe.episode_content_id)
                ELSE s.deeplink_payload
            END,
        deeplink_id = 
            CASE
                WHEN s.deeplink_id != fe.episode_content_id
                THEN fe.episode_content_id
                ELSE s.deeplink_id
            END
    WHERE JSON_VALUE(s.deeplink_payload, '$.deeplink_data.content_id') != fe.episode_content_id
    OR s.deeplink_id != fe.episode_content_id;

COMMIT;