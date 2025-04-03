WITH ShowsWithNearestEpisode AS (
    SELECT 
        s.Cnty_cd,
        s.vc_cp_id,
        s.content_id,
        s.deeplink_payload,
        s.deeplink_id,
        COALESCE(JSON_VALUE(s.deeplink_payload, '$.deeplink_data.ratings'), '') AS ratings,
        e.content_id AS episode_id,
        ROW_NUMBER() OVER (PARTITION BY s.content_id ORDER BY e.season_no, e.episode_no) AS rn
    FROM 
        master_asset_table s
    JOIN 
        master_asset_table e ON e.show_id = s.content_id
    WHERE 
        s.type = 'Show'
        AND e.type = 'Episode'
        AND s.Cnty_cd = :countryCode
        AND e.Cnty_cd = :countryCode
)
SELECT 
    Cnty_cd AS countryCode,
    vc_cp_id AS vcCpId,
    content_id AS contentID,
    episode_id AS episodeId,
    deeplink_payload AS DEEPLINKPAYLOAD,
    deeplink_id AS DEEPlinkid,
    ratings
FROM 
    ShowsWithNearestEpisode
WHERE 
    rn = 1;