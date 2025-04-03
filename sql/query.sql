WITH FirstEpisodes AS (
    -- Find the first episode of each show based on season_no and episode_no
    SELECT 
        e.country AS country_code,
        e.vc_cp_id AS vc_cp_id,
        s.content_id AS content_id,
        e.content_id AS episode_id,
        s.deeplink_payload AS deeplink_payload,
        s.deeplink_id AS deeplink_id,
        COALESCE(JSON_VALUE(e.deeplink_payload, '$.deeplink_data.ratings'), '') AS ratings,
        'Show' AS asset_type,
        ROW_NUMBER() OVER (PARTITION BY s.content_id ORDER BY e.season_no, e.episode_no) AS rn
    FROM 
        master_asset_table s
    JOIN 
        master_asset_table e ON e.show_id = s.content_id
    WHERE 
        s.type = 'Show'
        AND e.type = 'Episode'
        AND s.country = :countryCode
        AND e.country = :countryCode
),

SeasonFirstEpisodes AS (
    -- Find the first episode of each season based on episode_no
    SELECT 
        e.country AS country_code,
        e.vc_cp_id AS vc_cp_id,
        sea.content_id AS content_id,
        e.content_id AS episode_id,
        sea.deeplink_payload AS deeplink_payload,
        sea.deeplink_id AS deeplink_id,
        COALESCE(JSON_VALUE(e.deeplink_payload, '$.deeplink_data.ratings'), '') AS ratings,
        'Season' AS asset_type,
        ROW_NUMBER() OVER (PARTITION BY sea.content_id ORDER BY e.episode_no) AS rn
    FROM 
        master_asset_table sea
    JOIN 
        master_asset_table e ON e.season_id = sea.content_id
    WHERE 
        sea.type = 'Season'
        AND e.type = 'Episode'
        AND sea.country = :countryCode
        AND e.country = :countryCode
)

-- Combine results for shows and seasons
SELECT 
    country_code AS countryCode,
    vc_cp_id AS vcCpId,
    content_id AS contentID,
    episode_id AS episodeId,
    deeplink_payload AS DEEPLINKPAYLOAD,
    deeplink_id AS DEEPlinkid,
    ratings,
    asset_type
FROM 
    (
        -- Get first episode of each show
        SELECT * FROM FirstEpisodes WHERE rn = 1
        
        UNION ALL
        
        -- Get first episode of each season
        SELECT * FROM SeasonFirstEpisodes WHERE rn = 1
    )
-- Optional: Filter only those that need to be updated (deeplink doesn't match first episode)
WHERE 
    JSON_VALUE(deeplink_payload, '$.deeplink_data.content_id') != episode_id
    OR deeplink_id != episode_id
ORDER BY
    asset_type, content_id;