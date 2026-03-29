Good point on the separate mapper. Let me verify what's currently in the slot updater before giving the final list.Good. Now I have the exact package structure. Here are all the changes required — nothing more.

---

## All Changes for Deeplink Phase

---

### New Files — 4

---

**1. `src/main/java/com/cms/slotupdater/batchprocessor/model/DeeplinkUpdateDto.java`**

```java
package com.cms.slotupdater.batchprocessor.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeeplinkUpdateDto {
    private String contentId;
    private String countryCode;
    private String providerId;
    private String currentDeeplinkId;
    private String newDeeplinkId;
    private String ratings;
    private String deeplinkPayload;
}
```

---

**2. `src/main/java/com/cms/slotupdater/batchprocessor/mapper/DeeplinkMapper.java`**

```java
package com.cms.slotupdater.batchprocessor.mapper;

import com.cms.slotupdater.batchprocessor.model.DeeplinkUpdateDto;
import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface DeeplinkMapper {

    List<DeeplinkUpdateDto> findShowDeeplinkUpdates(
        @Param("countryGroup") int countryGroup,
        @Param("feedWorkers") List<String> feedWorkers);

    List<DeeplinkUpdateDto> findSeasonDeeplinkUpdates(
        @Param("countryGroup") int countryGroup,
        @Param("feedWorkers") List<String> feedWorkers);

    void updateDeeplinks(@Param("assets") List<DeeplinkUpdateDto> assets);

    void updateDeeplinksCP(@Param("assets") List<DeeplinkUpdateDto> assets);
}
```

---

**3. `src/main/resources/com/cms/slotupdater/batchprocessor/mapper/DeeplinkMapper.xml`**

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="com.cms.slotupdater.batchprocessor.mapper.DeeplinkMapper">

  <select id="findShowDeeplinkUpdates"
      resultType="com.cms.slotupdater.batchprocessor.model.DeeplinkUpdateDto"
      parameterType="map">
    SELECT
      S.CONTENT_ID  AS contentId,
      S.CNTY_CD     AS countryCode,
      S.VC_CP_ID    AS providerId,
      S.DEEPLINK_ID AS currentDeeplinkId,
      E.CONTENT_ID  AS newDeeplinkId,
      E.RATINGS     AS ratings
    FROM ITVSTD_O.STD_VC_VOD_CONTENT S
    LEFT JOIN (
      SELECT * FROM (
        SELECT
          E.SHOW_ID,
          E.CONTENT_ID,
          E.RATINGS,
          ROW_NUMBER() OVER (
            PARTITION BY E.SHOW_ID
            ORDER BY E.SEASON_NO, E.EPISODE_NO
          ) AS RN
        FROM ITVSTD_O.STD_VC_VOD_CONTENT E
        WHERE E."TYPE" = 'EPISODE'
          AND UPPER(E.FEED_WORKER) IN
            <foreach collection="feedWorkers" item="worker" open="(" separator="," close=")">
              UPPER(#{worker})
            </foreach>
      ) WHERE RN = 1
    ) E ON S.CONTENT_ID = E.SHOW_ID
    JOIN ITVSTD_O.STD_VC_VOD_CP CP
      ON S.CNTY_CD = CP.COUNTRY_CD
      AND S.VC_CP_ID = CP.VC_CP_ID
    WHERE S."TYPE" = 'SHOW'
      AND UPPER(S.FEED_WORKER) IN
        <foreach collection="feedWorkers" item="worker" open="(" separator="," close=")">
          UPPER(#{worker})
        </foreach>
      AND CP."GROUP" = #{countryGroup}
  </select>

  <select id="findSeasonDeeplinkUpdates"
      resultType="com.cms.slotupdater.batchprocessor.model.DeeplinkUpdateDto"
      parameterType="map">
    SELECT
      S.CONTENT_ID  AS contentId,
      S.CNTY_CD     AS countryCode,
      S.VC_CP_ID    AS providerId,
      S.DEEPLINK_ID AS currentDeeplinkId,
      E.CONTENT_ID  AS newDeeplinkId,
      E.RATINGS     AS ratings
    FROM ITVSTD_O.STD_VC_VOD_CONTENT S
    LEFT JOIN (
      SELECT * FROM (
        SELECT
          E.SEASON_ID,
          E.CONTENT_ID,
          E.RATINGS,
          ROW_NUMBER() OVER (
            PARTITION BY E.SEASON_ID
            ORDER BY E.EPISODE_NO
          ) AS RN
        FROM ITVSTD_O.STD_VC_VOD_CONTENT E
        WHERE E."TYPE" = 'EPISODE'
          AND UPPER(E.FEED_WORKER) IN
            <foreach collection="feedWorkers" item="worker" open="(" separator="," close=")">
              UPPER(#{worker})
            </foreach>
      ) WHERE RN = 1
    ) E ON S.CONTENT_ID = E.SEASON_ID
    JOIN ITVSTD_O.STD_VC_VOD_CP CP
      ON S.CNTY_CD = CP.COUNTRY_CD
      AND S.VC_CP_ID = CP.VC_CP_ID
    WHERE S."TYPE" = 'SEASON'
      AND UPPER(S.FEED_WORKER) IN
        <foreach collection="feedWorkers" item="worker" open="(" separator="," close=")">
          UPPER(#{worker})
        </foreach>
      AND CP."GROUP" = #{countryGroup}
  </select>

  <update id="updateDeeplinks">
    <foreach collection="assets" item="asset" open="begin " close=";end;" separator=";">
      UPDATE ITVSTD_O.STD_VC_VOD_CONTENT
      SET
        DEEPLINK_ID      = #{asset.newDeeplinkId, jdbcType=VARCHAR},
        DEEPLINK_PAYLOAD = #{asset.deeplinkPayload, jdbcType=VARCHAR}
      WHERE
        CONTENT_ID = #{asset.contentId, jdbcType=VARCHAR}
        AND CNTY_CD  = #{asset.countryCode, jdbcType=VARCHAR}
        AND VC_CP_ID = #{asset.providerId, jdbcType=VARCHAR}
    </foreach>
  </update>

  <update id="updateDeeplinksCP">
    <foreach collection="assets" item="asset" open="begin " close=";end;" separator=";">
      UPDATE ITVSTD_O.STD_CMS_VOD_CP_CONTENT
      SET
        DEEPLINK_ID      = #{asset.newDeeplinkId, jdbcType=VARCHAR},
        DEEPLINK_PAYLOAD = #{asset.deeplinkPayload, jdbcType=VARCHAR}
      WHERE
        CONTENT_ID = #{asset.contentId, jdbcType=VARCHAR}
        AND CNTY_CD  = #{asset.countryCode, jdbcType=VARCHAR}
        AND VC_CP_ID = #{asset.providerId, jdbcType=VARCHAR}
    </foreach>
  </update>

</mapper>
```

---

**4. `src/main/java/com/cms/slotupdater/batchprocessor/service/DeeplinkSyncService.java`**

```java
package com.cms.slotupdater.batchprocessor.service;

import com.cms.slotupdater.batchprocessor.common.ErrorMessageUtil;
import com.cms.slotupdater.batchprocessor.common.ListUtils;
import com.cms.slotupdater.batchprocessor.common.NotificationUtil;
import com.cms.slotupdater.batchprocessor.mapper.DeeplinkMapper;
import com.cms.slotupdater.batchprocessor.model.DeeplinkUpdateDto;
import com.google.gson.JsonObject;
import java.util.List;
import java.util.Objects;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.util.CollectionUtils;

@Service
@Slf4j
public class DeeplinkSyncService {

    private final DeeplinkMapper deeplinkMapper;
    private final TransactionTemplate transactionTemplate;
    private final NotificationUtil notificationUtil;

    @Value("${BATCH_SIZE:1000}")
    private int batchSize;

    public DeeplinkSyncService(DeeplinkMapper deeplinkMapper,
            TransactionTemplate transactionTemplate,
            NotificationUtil notificationUtil) {
        this.deeplinkMapper = deeplinkMapper;
        this.transactionTemplate = transactionTemplate;
        this.notificationUtil = notificationUtil;
    }

    public void syncShowDeeplinks(int countryGroup, List<String> feedWorkers) {
        log.info("Starting SHOW deeplink sync");

        List<DeeplinkUpdateDto> all =
            deeplinkMapper.findShowDeeplinkUpdates(countryGroup, feedWorkers);

        if (CollectionUtils.isEmpty(all)) {
            log.info("SHOW deeplink sync: no assets found, skipping");
            return;
        }

        List<DeeplinkUpdateDto> stale = all.stream()
            .filter(u -> u.getNewDeeplinkId() != null)
            .filter(u -> !StringUtils.equals(u.getCurrentDeeplinkId(), u.getNewDeeplinkId()))
            .peek(u -> buildDeeplinkPayload(u))
            .toList();

        updateDeeplinksInBatch(stale);

        log.info("SHOW deeplink sync: total={}, updated={}, skipped={}",
            all.size(), stale.size(), all.size() - stale.size());
    }

    public void syncSeasonDeeplinks(int countryGroup, List<String> feedWorkers) {
        log.info("Starting SEASON deeplink sync");

        List<DeeplinkUpdateDto> all =
            deeplinkMapper.findSeasonDeeplinkUpdates(countryGroup, feedWorkers);

        if (CollectionUtils.isEmpty(all)) {
            log.info("SEASON deeplink sync: no assets found, skipping");
            return;
        }

        List<DeeplinkUpdateDto> stale = all.stream()
            .filter(u -> u.getNewDeeplinkId() != null)
            .filter(u -> !StringUtils.equals(u.getCurrentDeeplinkId(), u.getNewDeeplinkId()))
            .peek(u -> buildDeeplinkPayload(u))
            .toList();

        updateDeeplinksInBatch(stale);

        log.info("SEASON deeplink sync: total={}, updated={}, skipped={}",
            all.size(), stale.size(), all.size() - stale.size());
    }

    private void buildDeeplinkPayload(DeeplinkUpdateDto asset) {
        JsonObject deeplinkPayload = new JsonObject();
        JsonObject deeplinkData = new JsonObject();
        deeplinkData.addProperty("content_type", "tvshow");
        deeplinkData.addProperty("content_id", asset.getNewDeeplinkId());
        deeplinkData.addProperty("series_id", asset.getContentId());
        deeplinkData.addProperty("ratings", asset.getRatings() == null ? "" : asset.getRatings());
        deeplinkPayload.add("deeplink_data", deeplinkData);
        asset.setDeeplinkPayload(deeplinkPayload.toString());
    }

    private void updateDeeplinksInBatch(List<DeeplinkUpdateDto> updates) {
        if (CollectionUtils.isEmpty(updates)) {
            log.info("No deeplink updates needed.");
            return;
        }

        for (List<DeeplinkUpdateDto> partition :
                ListUtils.partitionList(updates, batchSize)) {
            try {
                transactionTemplate.executeWithoutResult(status -> {
                    deeplinkMapper.updateDeeplinks(partition);
                    deeplinkMapper.updateDeeplinksCP(partition);
                });
                log.info("Deeplink batch updated: count={}", partition.size());
            } catch (Exception ex) {
                log.error("Error updating deeplinks: {}",
                    ErrorMessageUtil.extractError(ex));
                notificationUtil.sendAlarm(ex,
                    HttpStatus.INTERNAL_SERVER_ERROR.name(),
                    String.valueOf(HttpStatus.INTERNAL_SERVER_ERROR.value()),
                    "Deeplink batch update failed");
            }
        }
    }
}
```

---

### Modified Files — 1

**`SlotBatchService.java`** — inject `DeeplinkSyncService` and `TransactionTemplate`, add two calls at end of `slotUpdater()`. Only these lines change — nothing else in the file:

```java
// Add to constructor fields:
private final DeeplinkSyncService deeplinkSyncService;
private final TransactionTemplate transactionTemplate;

// Add to constructor:
public SlotBatchService(..., DeeplinkSyncService deeplinkSyncService,
        TransactionTemplate transactionTemplate) {
    ...
    this.deeplinkSyncService = deeplinkSyncService;
    this.transactionTemplate = transactionTemplate;
}

// Add at end of slotUpdater(), after the three existing strategies:
deeplinkSyncService.syncShowDeeplinks(countryGroup, feedWorkerList);
deeplinkSyncService.syncSeasonDeeplinks(countryGroup, feedWorkerList);
```

---

### Summary

| File | Type |
|---|---|
| `DeeplinkUpdateDto.java` | New |
| `DeeplinkMapper.java` | New |
| `DeeplinkMapper.xml` | New |
| `DeeplinkSyncService.java` | New |
| `SlotBatchService.java` | Modified — inject + 2 calls only |

5 files. That's the complete scope of this phase. Ready to write code?
