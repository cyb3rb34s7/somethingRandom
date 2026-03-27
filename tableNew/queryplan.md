You're absolutely right. Semaphore is overcomplicating it. If the thread pool core size is 5, at most 5 tasks run at a time naturally — no semaphore needed. Let me read the current config one more time to make sure I get the thread pool change right.Good. Now here's the complete, final, detailed plan with all code changes.

---

## Complete Implementation Plan — Final Version

---

### 1. `ThreadPoolConfig.java`

Change `corePoolSize` from 20 to 5, `maxPoolSize` from 50 to 5. This means at most 5 partitions ever run concurrently. No semaphore, no extra logic — the thread pool itself is the throttle.

```java
executor.setCorePoolSize(5);
executor.setMaxPoolSize(5);
```

---

### 2. `application.properties`

```properties
# FROM:
spring.datasource.hikari.maxLifetime=2000000
# TO:
spring.datasource.hikari.maxLifetime=600000
```

---

### 3. `LicenseWindowDto.java`

Add two fields. Everything else stays exactly as-is.

```java
private String currentAvailableStarting;
private String currentAvailableEnding;
```

---

### 4. New file — `DeeplinkPayloadDto.java`

Create inside `cms-slot-updater` at `model/DeeplinkPayloadDto.java`. Four fields only — no `event`, no `event_info`.

```java
@Builder
@Getter
@Setter
@JsonInclude(Include.NON_NULL)
public class DeeplinkPayloadDto {

    @JsonProperty("content_type")
    private String contentType;

    @JsonProperty("content_id")
    private String contentId;

    @JsonProperty("series_id")
    private String seriesId;

    @JsonProperty("ratings")
    private String ratings;
}
```

---

### 5. New file — `DeeplinkUpdateDto.java`

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DeeplinkUpdateDto {
    private String contentId;         // SHOW or SEASON content ID
    private String countryCode;
    private String providerId;
    private String currentDeeplinkId; // currently stored DEEPLINK_ID
    private String newDeeplinkId;     // correct first available episode ID
    private String ratings;           // ratings of the new episode
    private String deeplinkPayload;   // built JSON string, set in Java before update
}
```

---

### 6. `SlotBatchMapper.xml` — All query changes

#### 6.1 Modify `findAssetWithMultipleSlots`

Add `VOD.AVAILABLE_STARTING` and `VOD.EXP_DATE` to SELECT and GROUP BY. Both already available from existing `VOD` join — no new join. Return type changes to `LicenseWindowDto`.

```xml
<select id="findAssetWithMultipleSlots"
    resultType="com.cms.slotupdater.batchprocessor.model.LicenseWindowDto"
    parameterType="map">
  SELECT
    SLOT.PROGRAM_ID                as contentId,
    VOD.AVAILABLE_STARTING         as currentAvailableStarting,
    VOD.EXP_DATE                   as currentAvailableEnding
  FROM
    ITVSTD_O.STD_CMS_VOD_ASSET_LICENSE SLOT
  JOIN
    ITVSTD_O.STD_VC_VOD_CONTENT VOD ON SLOT.PROGRAM_ID = VOD.CONTENT_ID
  JOIN
    ITVSTD_O.STD_VC_VOD_CP CP
    ON VOD.CNTY_CD = CP.COUNTRY_CD AND VOD.VC_CP_ID = CP.VC_CP_ID
  WHERE
    UPPER(SLOT.FEED_WORKER) IN
      <foreach collection="feedWorkers" item="item" open="(" separator="," close=")">
        UPPER(#{item})
      </foreach>
    AND VOD."TYPE" NOT IN ('SEASON', 'SHOW')
    AND CP."GROUP" = #{countryGroup}
  GROUP BY
    SLOT.PROGRAM_ID,
    VOD.AVAILABLE_STARTING,
    VOD.EXP_DATE
  HAVING COUNT(SLOT.PROGRAM_ID) > 1
</select>
```

#### 6.2 Modify `findAssetByType`

Add same two columns. Already on the same table being queried.

```xml
<select id="findAssetByType"
    resultType="com.cms.slotupdater.batchprocessor.model.LicenseWindowDto"
    parameterType="map">
  SELECT
    VOD.CONTENT_ID             as contentId,
    VOD.AVAILABLE_STARTING     as currentAvailableStarting,
    VOD.EXP_DATE               as currentAvailableEnding
  FROM
    ITVSTD_O.STD_VC_VOD_CONTENT VOD
  JOIN
    ITVSTD_O.STD_VC_VOD_CP CP
    ON VOD.CNTY_CD = CP.COUNTRY_CD AND VOD.VC_CP_ID = CP.VC_CP_ID
  WHERE
    UPPER(VOD.FEED_WORKER) IN
      <foreach collection="feedWorkers" item="item" open="(" separator="," close=")">
        UPPER(#{item})
      </foreach>
    AND VOD."TYPE" = #{assetType}
    AND CP."GROUP" = #{countryGroup}
</select>
```

#### 6.3 Modify `findLicenseSlotsByProgramId`

Add `currentAvailableStarting` and `currentAvailableEnding` by joining `STD_VC_VOD_CONTENT`. This is the fix for Issue 5 — current values flow naturally through the slot rows, no map needed.

```xml
<select id="findLicenseSlotsByProgramId"
    resultType="com.cms.slotupdater.batchprocessor.model.LicenseWindowDto"
    parameterType="map">
  SELECT
    SLOT.PROGRAM_ID            as contentId,
    SLOT.AVAILABLE_STARTING    as availableStarting,
    SLOT.EXP_DATE              as availableEnding,
    VOD.AVAILABLE_STARTING     as currentAvailableStarting,
    VOD.EXP_DATE               as currentAvailableEnding
  FROM
    ITVSTD_O.STD_CMS_VOD_ASSET_LICENSE SLOT
  JOIN
    ITVSTD_O.STD_VC_VOD_CONTENT VOD ON SLOT.PROGRAM_ID = VOD.CONTENT_ID
  WHERE
    SLOT.PROGRAM_ID IN
      <foreach collection="programIds" item="programId" open="(" close=")" separator=",">
        #{programId}
      </foreach>
  ORDER BY
    SLOT.PROGRAM_ID, SLOT.AVAILABLE_STARTING
</select>
```

#### 6.4 New — `findShowDeeplinkUpdates`

```xml
<select id="findShowDeeplinkUpdates"
    resultType="com.cms.slotupdater.batchprocessor.model.DeeplinkUpdateDto"
    parameterType="map">
  SELECT
    S.CONTENT_ID    AS contentId,
    S.CNTY_CD       AS countryCode,
    S.VC_CP_ID      AS providerId,
    S.DEEPLINK_ID   AS currentDeeplinkId,
    E.CONTENT_ID    AS newDeeplinkId,
    E.RATINGS       AS ratings
  FROM ITVSTD_O.STD_VC_VOD_CONTENT S
  JOIN (
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
      WHERE LOWER(E.TYPE) = 'episode'
        AND UPPER(E.FEED_WORKER) IN
          <foreach collection="feedWorkers" item="worker" open="(" separator="," close=")">
            UPPER(#{worker})
          </foreach>
    ) WHERE RN = 1
  ) E ON S.CONTENT_ID = E.SHOW_ID
  JOIN ITVSTD_O.STD_VC_VOD_CP CP
    ON S.CNTY_CD = CP.COUNTRY_CD AND S.VC_CP_ID = CP.VC_CP_ID
  WHERE LOWER(S."TYPE") = 'show'
    AND CP."GROUP" = #{countryGroup}
</select>
```

#### 6.5 New — `findSeasonDeeplinkUpdates`

Same structure as above, three differences only:

- `PARTITION BY E.SEASON_ID`
- `ORDER BY E.EPISODE_NO`
- `ON S.CONTENT_ID = E.SEASON_ID`
- `WHERE LOWER(S."TYPE") = 'season'`

#### 6.6 New — `updateDeeplinks` (STD_VC_VOD_CONTENT)

```xml
<update id="updateDeeplinks">
  <foreach collection="assets" item="asset" open="begin " close=";end;" separator=";">
    UPDATE ITVSTD_O.STD_VC_VOD_CONTENT
    SET
      DEEPLINK_ID      = #{asset.newDeeplinkId, jdbcType=VARCHAR},
      DEEPLINK_PAYLOAD = #{asset.deeplinkPayload, jdbcType=VARCHAR}
    WHERE
      CONTENT_ID = #{asset.contentId, jdbcType=VARCHAR}
      AND CNTY_CD   = #{asset.countryCode, jdbcType=VARCHAR}
      AND VC_CP_ID  = #{asset.providerId, jdbcType=VARCHAR}
  </foreach>
</update>
```

#### 6.7 New — `updateDeeplinksCP` (STD_CMS_VOD_CP_CONTENT)

Identical to above, just `STD_CMS_VOD_CP_CONTENT` instead.

---

### 7. `SlotBatchMapper.java`

```java
// Modified return types
List<LicenseWindowDto> findAssetWithMultipleSlots(
    @Param("countryGroup") int countryGroup,
    @Param("feedWorkers") List<String> feedWorkers);

List<LicenseWindowDto> findAssetByType(
    @Param("countryGroup") int countryGroup,
    @Param("feedWorkers") List<String> feedWorkers,
    @Param("assetType") String assetType);

// Unchanged
List<LicenseWindowDto> findLicenseSlotsByProgramId(List<String> programIds);
List<LicenseWindowDto> findEpisodeSlotsBySeasonId(List<String> seasonIds);
List<LicenseWindowDto> findSeasonSlotsByShowId(List<String> showIds);
void updateAssetLicenseWindow(List<LicenseWindowDto> assets);
void updateAssetLicenseWindowCP(List<LicenseWindowDto> assets);

// New
List<DeeplinkUpdateDto> findShowDeeplinkUpdates(
    @Param("countryGroup") int countryGroup,
    @Param("feedWorkers") List<String> feedWorkers);

List<DeeplinkUpdateDto> findSeasonDeeplinkUpdates(
    @Param("countryGroup") int countryGroup,
    @Param("feedWorkers") List<String> feedWorkers);

void updateDeeplinks(@Param("assets") List<DeeplinkUpdateDto> assets);
void updateDeeplinksCP(@Param("assets") List<DeeplinkUpdateDto> assets);
```

---

### 8. `LicenseUpdateStrategy.java`

One change — `fetchAssetIds` return type:

```java
// FROM:
List<String> fetchAssetIds(SlotBatchMapper mapper, int countryGroup, List<String> feedWorkers);

// TO:
List<LicenseWindowDto> fetchAssets(SlotBatchMapper mapper, int countryGroup, List<String> feedWorkers);
```

All other method signatures that reference `List<String> assetIds` change to `List<LicenseWindowDto> assets`.

---

### 9. Three strategy implementations

Each changes `fetchAssets` to return `List<LicenseWindowDto>` from the mapper. Wherever `assetIds` was used as a list of strings (for `getSlotFetcherFunction`, `getFetchSlotsLogMessage`, `getProcessingLogMessage`, `processGroupedSlots`), extract `contentId` from the DTO:

```java
// In NonSeasonNonShowUpdateStrategy.fetchAssets:
return mapper.findAssetWithMultipleSlots(countryGroup, feedWorkers);

// Wherever asset IDs as strings are needed:
List<String> ids = assets.stream()
    .map(LicenseWindowDto::getContentId)
    .toList();
```

`processGroupedSlots` in Season and Show strategies fills in missing assets from `assetIds` — this now uses the extracted string IDs the same way as before, just extracted from the DTO list first.

---

### 10. `LicenseWindowService.java`

Both methods carry through `currentAvailableStarting/Ending` from the input list's first element into the returned DTO.

**`findUpdateSlot`** — at every return point, set current values onto the result:

```java
// All existing return statements change to carry through current values.
// Example — the direct active slot return:
LicenseWindowDto result = licenseWindows.get(resInd);
return LicenseWindowDto.builder()
    .contentId(result.getContentId())
    .availableStarting(result.getAvailableStarting())
    .availableEnding(result.getAvailableEnding())
    .currentAvailableStarting(licenseWindows.get(0).getCurrentAvailableStarting())
    .currentAvailableEnding(licenseWindows.get(0).getCurrentAvailableEnding())
    .partitionCt(result.getPartitionCt())
    .build();
```

Same pattern for the merged window return and the fallback return. All three return points get the same `currentAvailableStarting/Ending` carried through from `licenseWindows.get(0)`.

**`findMinStartAndMaxEnd`** — add current values to the builder:

```java
return LicenseWindowDto.builder()
    .availableStarting(minTime)
    .availableEnding(maxTime)
    .contentId(licenseWindows.get(0).getContentId())
    .currentAvailableStarting(licenseWindows.get(0).getCurrentAvailableStarting())
    .currentAvailableEnding(licenseWindows.get(0).getCurrentAvailableEnding())
    .partitionCt(licenseWindows.get(0).getPartitionCt())
    .build();
```

---

### 11. `SlotBatchService.java`

**Inject `TransactionTemplate`:**
```java
private final TransactionTemplate transactionTemplate;
```

**`executeUpdateStrategy`** — change `assetIds` from `List<String>` to `List<LicenseWindowDto>`. Extract string IDs where needed. Add filter after `processGroupedSlots`:

```java
private void executeUpdateStrategy(LicenseUpdateStrategy strategy, String operationName) {
    log.info(strategy.getLogMessageStart());

    List<LicenseWindowDto> assets = strategy.fetchAssets(slotBatchMapper, countryGroup, feedWorkerList);

    if (CollectionUtils.isEmpty(assets)) {
        log.info("No assets found for: {}", operationName);
        return;
    }

    List<String> assetIds = assets.stream()
        .map(LicenseWindowDto::getContentId)
        .toList();

    log.info(strategy.getFetchSlotsLogMessage(assets));

    Function<List<String>, List<LicenseWindowDto>> slotFetcher =
        strategy.getSlotFetcherFunction(slotBatchMapper);
    List<LicenseWindowDto> allSlots = fetchSlotsInBatch(assetIds, slotFetcher);

    log.info(strategy.getProcessingLogMessage(assets, allSlots.size()));

    Map<String, List<LicenseWindowDto>> slotsByAsset = allSlots.stream()
        .collect(Collectors.groupingBy(LicenseWindowDto::getContentId));

    List<LicenseWindowDto> computedWindows = strategy.processGroupedSlots(
        slotsByAsset, licenseWindowService, assets);

    List<LicenseWindowDto> actualChanges = computedWindows.stream()
        .filter(w -> !Objects.equals(w.getAvailableStarting(), w.getCurrentAvailableStarting())
                  || !Objects.equals(w.getAvailableEnding(), w.getCurrentAvailableEnding()))
        .toList();

    log.info("{}: {} fetched, {} need update, {} skipped",
        operationName, computedWindows.size(), actualChanges.size(),
        computedWindows.size() - actualChanges.size());

    updateWindowsInBatch(actualChanges);
}
```

**`fetchSlotsInBatch`** — remove `CompletableFuture`, plain sequential loop:

```java
private List<LicenseWindowDto> fetchSlotsInBatch(
    List<String> assetIds,
    Function<List<String>, List<LicenseWindowDto>> slotFetcherFunction) {

    List<LicenseWindowDto> allSlots = new ArrayList<>();
    for (List<String> partition : ListUtils.partitionList(assetIds, Math.min(1000, batchSize))) {
        allSlots.addAll(slotFetcherFunction.apply(partition));
    }
    return allSlots;
}
```

**`updateWindowsInBatch`** — unchanged logic, just now naturally limited to 5 concurrent tasks by the thread pool:

```java
public void updateWindowsInBatch(List<LicenseWindowDto> updateWindows) {
    if (CollectionUtils.isEmpty(updateWindows)) {
        log.info("No windows to update, skipping.");
        return;
    }

    log.info("Updating {} assets in batches of {}", updateWindows.size(), batchSize);
    List<List<LicenseWindowDto>> partitions =
        ListUtils.partitionLicenseList(updateWindows, batchSize);
    List<CompletableFuture<Void>> futures = new ArrayList<>();

    for (List<LicenseWindowDto> partition : partitions) {
        CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {
            try {
                log.info("Updating chunk {}", partition.get(0).getPartitionCt());
                updateBothTables(partition);
            } catch (Exception ex) {
                String errDesc = "Partition " + partition.get(0).getPartitionCt();
                log.error("Error updating {}: {}", errDesc, ErrorMessageUtil.extractError(ex));
                notificationUtil.sendAlarm(ex,
                    HttpStatus.INTERNAL_SERVER_ERROR.name(),
                    String.valueOf(HttpStatus.INTERNAL_SERVER_ERROR.value()),
                    errDesc, " DB Connection Error");
            }
        }, taskExecutor);
        futures.add(future);
    }

    CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
    log.info("All batch updates completed.");
}
```

**`updateBothTables`** — remove `@Transactional`, use `TransactionTemplate`:

```java
public void updateBothTables(List<LicenseWindowDto> assets) {
    transactionTemplate.executeWithoutResult(status -> {
        slotBatchMapper.updateAssetLicenseWindow(assets);
        slotBatchMapper.updateAssetLicenseWindowCP(assets);
    });
}
```

**`slotUpdater`** — add deeplink calls and summary log:

```java
@Scheduled(fixedRateString = "#{@schedulerConfig.getBatchSchedulerRate()}")
public void slotUpdater() {
    log.info("Starting slot updater batch");
    Instant start = Instant.now();

    try {
        executeUpdateStrategy(nonSeasonNonShowStrategy,
            "License Update - Non-Season Non-Show");
        Instant t1 = Instant.now();

        executeUpdateStrategy(seasonStrategy,
            "License Update - Season");
        Instant t2 = Instant.now();

        executeUpdateStrategy(showStrategy,
            "License Update - Show");
        Instant t3 = Instant.now();

        deeplinkSyncService.syncShowDeeplinks(countryGroup, feedWorkerList);
        Instant t4 = Instant.now();

        deeplinkSyncService.syncSeasonDeeplinks(countryGroup, feedWorkerList);
        Instant end = Instant.now();

        logExecutionTime("License Update - Non-Season Non-Show", start, t1);
        logExecutionTime("License Update - Season", t1, t2);
        logExecutionTime("License Update - Show", t2, t3);
        logExecutionTime("Deeplink Sync - Show", t3, t4);
        logExecutionTime("Deeplink Sync - Season", t4, end);
        logExecutionTime("Total Batch", start, end);

    } catch (Exception ex) {
        String errMsg = "Batch failed: " + ErrorMessageUtil.extractError(ex);
        notificationUtil.sendAlarm(ex,
            HttpStatus.INTERNAL_SERVER_ERROR.name(),
            String.valueOf(HttpStatus.INTERNAL_SERVER_ERROR.value()),
            errMsg, " Batch job failed");
        log.error(errMsg);
    }

    log.info("Batch completed. Group ID: {}", countryGroup);
}
```

---

### 12. New `DeeplinkSyncService.java`

```java
@Service
@Slf4j
public class DeeplinkSyncService {

    private static final String DEEPLINK_BODY_START = "{\"deeplink_data\":";
    private static final String DEEPLINK_BODY_END = "}";

    private final SlotBatchMapper slotBatchMapper;
    private final TransactionTemplate transactionTemplate;
    private final NotificationUtil notificationUtil;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${BATCH_SIZE:1000}")
    private int batchSize;

    public void syncShowDeeplinks(int countryGroup, List<String> feedWorkers) {
        log.info("Starting SHOW deeplink sync");

        List<DeeplinkUpdateDto> all =
            slotBatchMapper.findShowDeeplinkUpdates(countryGroup, feedWorkers);

        List<DeeplinkUpdateDto> stale = all.stream()
            .filter(u -> u.getNewDeeplinkId() != null)
            .filter(u -> !Objects.equals(u.getCurrentDeeplinkId(), u.getNewDeeplinkId()))
            .peek(u -> u.setDeeplinkPayload(buildPayload(u)))
            .toList();

        updateDeeplinksInBatch(stale);

        log.info("SHOW deeplink sync: {} checked, {} updated, {} skipped",
            all.size(), stale.size(), all.size() - stale.size());
    }

    public void syncSeasonDeeplinks(int countryGroup, List<String> feedWorkers) {
        log.info("Starting SEASON deeplink sync");

        List<DeeplinkUpdateDto> all =
            slotBatchMapper.findSeasonDeeplinkUpdates(countryGroup, feedWorkers);

        List<DeeplinkUpdateDto> stale = all.stream()
            .filter(u -> u.getNewDeeplinkId() != null)
            .filter(u -> !Objects.equals(u.getCurrentDeeplinkId(), u.getNewDeeplinkId()))
            .peek(u -> u.setDeeplinkPayload(buildPayload(u)))
            .toList();

        updateDeeplinksInBatch(stale);

        log.info("SEASON deeplink sync: {} checked, {} updated, {} skipped",
            all.size(), stale.size(), all.size() - stale.size());
    }

    private void updateDeeplinksInBatch(List<DeeplinkUpdateDto> updates) {
        if (CollectionUtils.isEmpty(updates)) {
            log.info("No deeplink updates needed.");
            return;
        }

        List<List<DeeplinkUpdateDto>> partitions =
            ListUtils.partitionList(updates, batchSize);

        for (List<DeeplinkUpdateDto> partition : partitions) {
            try {
                transactionTemplate.executeWithoutResult(status -> {
                    slotBatchMapper.updateDeeplinks(partition);
                    slotBatchMapper.updateDeeplinksCP(partition);
                });
                log.info("Updated {} deeplinks", partition.size());
            } catch (Exception ex) {
                log.error("Error updating deeplinks: {}", ErrorMessageUtil.extractError(ex));
                notificationUtil.sendAlarm(ex,
                    HttpStatus.INTERNAL_SERVER_ERROR.name(),
                    String.valueOf(HttpStatus.INTERNAL_SERVER_ERROR.value()),
                    "Deeplink batch update failed");
            }
        }
    }

    private String buildPayload(DeeplinkUpdateDto u) {
        try {
            DeeplinkPayloadDto payload = DeeplinkPayloadDto.builder()
                .contentType("tvshow")
                .contentId(u.getNewDeeplinkId())
                .seriesId(u.getContentId())
                .ratings(StringUtils.defaultIfBlank(u.getRatings(), ""))
                .build();
            return DEEPLINK_BODY_START + objectMapper.writeValueAsString(payload) + DEEPLINK_BODY_END;
        } catch (JsonProcessingException e) {
            log.error("Failed to build deeplink payload for contentId {}: {}",
                u.getContentId(), e.getMessage());
            throw new RuntimeException("Deeplink payload build failed for " + u.getContentId(), e);
        }
    }
}
```

---

## Summary of All Files

| File | Change |
|---|---|
| `ThreadPoolConfig.java` | corePoolSize 20→5, maxPoolSize 50→5 |
| `application.properties` | maxLifetime 2000000→600000 |
| `LicenseWindowDto.java` | Add `currentAvailableStarting`, `currentAvailableEnding` |
| `DeeplinkPayloadDto.java` | New — 4 fields |
| `DeeplinkUpdateDto.java` | New — 7 fields |
| `SlotBatchMapper.xml` | Modify 3 queries, add 4 new queries |
| `SlotBatchMapper.java` | 2 return type changes, 4 new methods |
| `LicenseUpdateStrategy.java` | `fetchAssetIds` → `fetchAssets`, return `List<LicenseWindowDto>` |
| `NonSeasonNonShowUpdateStrategy.java` | Updated signature + extract string IDs |
| `SeasonUpdateStrategy.java` | Updated signature + extract string IDs |
| `ShowUpdateStrategy.java` | Updated signature + extract string IDs |
| `LicenseWindowService.java` | Carry current values through all return points |
| `SlotBatchService.java` | Filter, sequential fetch, TransactionTemplate, deeplink calls, timing |
| `DeeplinkSyncService.java` | New — sequential deeplink sync |

Ready to implement?
