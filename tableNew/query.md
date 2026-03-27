SELECT
    S.CONTENT_ID        AS contentId,
    S.CNTY_CD           AS countryCode,
    S.VC_CP_ID          AS providerId,
    S.DEEPLINK_ID       AS currentDeeplinkId,
    E.CONTENT_ID        AS newDeeplinkId
FROM ITVSTD_O.STD_VC_VOD_CONTENT S
JOIN (
    SELECT *
    FROM (
        SELECT
            E.SEASON_ID,
            E.CONTENT_ID,
            ROW_NUMBER() OVER (
                PARTITION BY E.SEASON_ID
                ORDER BY E.EPISODE_NO
            ) AS RN
        FROM ITVSTD_O.STD_VC_VOD_CONTENT E
        WHERE LOWER(E.TYPE) = 'episode'
          AND E.AVAILABLE_STARTING <= SYSDATE
          AND E.EXP_DATE > SYSDATE
    )
    WHERE RN = 1
) E
ON S.CONTENT_ID = E.SEASON_ID
WHERE LOWER(S.TYPE) = 'season'
  AND S.CNTY_CD = #{countryCode}
  AND S.VC_CP_ID = #{providerId}



------------------------------------------------------------------
SELECT
    S.CONTENT_ID        AS contentId,
    S.CNTY_CD           AS countryCode,
    S.VC_CP_ID          AS providerId,
    S.DEEPLINK_ID       AS currentDeeplinkId,
    E.CONTENT_ID        AS newDeeplinkId
FROM ITVSTD_O.STD_VC_VOD_CONTENT S
JOIN (
    SELECT *
    FROM (
        SELECT
            E.SHOW_ID,
            E.CONTENT_ID,
            ROW_NUMBER() OVER (
                PARTITION BY E.SHOW_ID
                ORDER BY E.SEASON_NO, E.EPISODE_NO
            ) AS RN
        FROM ITVSTD_O.STD_VC_VOD_CONTENT E
        WHERE LOWER(E.TYPE) = 'episode'
    )
    WHERE RN = 1
) E
ON S.CONTENT_ID = E.SHOW_ID
WHERE LOWER(S.TYPE) = 'show'
  AND S.CNTY_CD = #{countryCode}
  AND S.VC_CP_ID = #{providerId}
