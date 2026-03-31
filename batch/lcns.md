Let me do one final read of all files before giving the plan.Good. I have a precise picture of the current state of every file. Here is the final plan.

---

## Final Implementation Plan — License Slot Changes

---

### 1. `LicenseWindowDto.java`

**Why:** The DTO needs to carry the currently stored window values from the DB so we can compare them against the computed values in Java. Without these fields, we have no way to know if an asset's window has actually changed.

Add two fields:

```java
private String currentAvailableStarting;
private String currentAvailableEnding;
```

---

### 2. `SlotBatchMapper.xml` — 2 query changes only

**Why:** These are the two queries that fetch assets scoped to our feed workers and country group. They already join or directly query `STD_VC_VOD_CONTENT` which holds the currently stored `AVAILABLE_STARTING` and `EXP_DATE`. Since the data is already there in the join, we just select it — zero extra cost.

**`findAssetWithMultipleSlots`** — add `VOD.AVAILABLE_STARTING` and `VOD.EXP_DATE` to SELECT and GROUP BY. Change `resultType` from `String` to `LicenseWindowDto`:

```xml
<select id="findAssetWithMultipleSlots"
    resultType="com.cms.slotupdater.batchprocessor.model.LicenseWindowDto"
    parameterType="map">
  SELECT
    SLOT.PROGRAM_ID         AS contentId,
    VOD.AVAILABLE_STARTING  AS currentAvailableStarting,
    VOD.EXP_DATE            AS currentAvailableEnding
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

**`findAssetByType`** — add same two columns. Already on the same table being queried, no new join. Change `resultType` from `String` to `LicenseWindowDto`:

```xml
<select id="findAssetByType"
    resultType="com.cms.slotupdater.batchprocessor.model.LicenseWindowDto"
    parameterType="map">
  SELECT
    VOD.CONTENT_ID          AS contentId,
    VOD.AVAILABLE_STARTING  AS currentAvailableStarting,
    VOD.EXP_DATE            AS currentAvailableEnding
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

No changes to `findLicenseSlotsByProgramId`, `findEpisodeSlotsBySeasonId`, `findSeasonSlotsByShowId`, or the update queries.

---

### 3. `SlotBatchMapper.java` — 2 return type changes

**Why:** Mapper interface must match the updated query return types.

```java
// FROM:
List<String> findAssetWithMultipleSlots(int countryGroup, List<String> feedWorkers);
List<String> findAssetByType(int countryGroup, List<String> feedWorkers, String assetType);

// TO:
List<LicenseWindowDto> findAssetWithMultipleSlots(
    @Param("countryGroup") int countryGroup,
    @Param("feedWorkers") List<String> feedWorkers);

List<LicenseWindowDto> findAssetByType(
    @Param("countryGroup") int countryGroup,
    @Param("feedWorkers") List<String> feedWorkers,
    @Param("assetType") String assetType);
```

---

### 4. `LicenseUpdateStrategy.java` — signature changes

**Why:** `fetchAssetIds` now returns `List<LicenseWindowDto>` instead of `List<String>` since the queries return DTOs. Log message methods and `processGroupedSlots` also update to take `List<LicenseWindowDto>` instead of `List<String>` so strategies receive the full asset context including current values.

```java
// FROM:
List<String> fetchAssetIds(SlotBatchMapper mapper, int countryGroup, List<String> feedWorkers);
String getFetchSlotsLogMessage(List<String> assetIds);
String getProcessingLogMessage(List<String> assetIds, int slotCount);
List<LicenseWindowDto> processGroupedSlots(Map<String, List<LicenseWindowDto>> slotsByAsset,
    LicenseWindowService licenseWindowService, List<String> assetIds);

// TO:
List<LicenseWindowDto> fetchAssets(SlotBatchMapper mapper, int countryGroup, List<String> feedWorkers);
String getFetchSlotsLogMessage(List<LicenseWindowDto> assets);
String getProcessingLogMessage(List<LicenseWindowDto> assets, int slotCount);
List<LicenseWindowDto> processGroupedSlots(Map<String, List<LicenseWindowDto>> slotsByAsset,
    LicenseWindowService licenseWindowService, List<LicenseWindowDto> assets);
```

---

### 5. `NonSeasonNonShowUpdateStrategy.java`

**Why:** Implements the updated interface. `processGroupedSlots` receives the full `List<LicenseWindowDto>` assets now but doesn't need to use them — it still just maps over the grouped slots. String IDs extracted where needed.

```java
@Override
public List<LicenseWindowDto> fetchAssets(SlotBatchMapper mapper,
        int countryGroup, List<String> feedWorkers) {
    return mapper.findAssetWithMultipleSlots(countryGroup, feedWorkers);
}

@Override
public String getFetchSlotsLogMessage(List<LicenseWindowDto> assets) {
    return String.format("Fetching slots for %d assets", assets.size());
}

@Override
public String getProcessingLogMessage(List<LicenseWindowDto> assets, int slotCount) {
    return String.format("Total Assets being processed: %d, Total Slots: %d",
        assets.size(), slotCount);
}

@Override
public List<LicenseWindowDto> processGroupedSlots(
        Map<String, List<LicenseWindowDto>> slotsByAsset,
        LicenseWindowService licenseWindowService,
        List<LicenseWindowDto> assets) {
    return slotsByAsset.values().stream()
        .map(licenseWindowService::findUpdateSlot)
        .toList();
}
```

---

### 6. `SeasonUpdateStrategy.java`

**Why:** Same interface update. Critically, `processGroupedSlots` now receives `List<LicenseWindowDto>` assets — each has `currentAvailableStarting/Ending`. When filling in seasons with no episodes, we carry those current values onto the placeholder DTO so the comparison in `SlotBatchService` works correctly for those assets too.

```java
@Override
public List<LicenseWindowDto> fetchAssets(SlotBatchMapper mapper,
        int countryGroup, List<String> feedWorkers) {
    return mapper.findAssetByType(countryGroup, feedWorkers, ASSET_TYPE_SEASON);
}

@Override
public String getFetchSlotsLogMessage(List<LicenseWindowDto> assets) {
    return String.format("Fetching episodes for %d seasonIds", assets.size());
}

@Override
public String getProcessingLogMessage(List<LicenseWindowDto> assets, int slotCount) {
    return String.format("Total Seasons: %d, Total Season Slots: %d",
        assets.size(), slotCount);
}

@Override
public List<LicenseWindowDto> processGroupedSlots(
        Map<String, List<LicenseWindowDto>> slotsByAsset,
        LicenseWindowService licenseWindowService,
        List<LicenseWindowDto> assets) {

    assets.forEach(asset -> {
        if (!slotsByAsset.containsKey(asset.getContentId())) {
            slotsByAsset.put(asset.getContentId(),
                List.of(LicenseWindowDto.builder()
                    .contentId(asset.getContentId())
                    .currentAvailableStarting(asset.getCurrentAvailableStarting())
                    .currentAvailableEnding(asset.getCurrentAvailableEnding())
                    .build()));
        }
    });

    return slotsByAsset.values().stream()
        .map(licenseWindowService::findMinStartAndMaxEnd)
        .toList();
}
```

---

### 7. `ShowUpdateStrategy.java`

**Why:** Identical changes to `SeasonUpdateStrategy` — same reasoning.

Same as Season strategy above, just `ASSET_TYPE_SHOW` and log messages reference shows/seasons instead of seasons/episodes.

---

### 8. `LicenseWindowService.java`

**Why:** Both methods produce a new `LicenseWindowDto` but currently discard `currentAvailableStarting/Ending`. We need them on the result so the comparison in `SlotBatchService` has both sides — computed value and current stored value — on the same object.

**`findMinStartAndMaxEnd`** — add two fields to the existing builder. Current values come from first element since all slots for the same asset have the same current values:

```java
return LicenseWindowDto.builder()
    .availableStarting(minTime)
    .availableEnding(maxTime)
    .contentId(licenseWindows.get(0).getContentId())
    .partitionCt(licenseWindows.get(0).getPartitionCt())
    .currentAvailableStarting(licenseWindows.get(0).getCurrentAvailableStarting())
    .currentAvailableEnding(licenseWindows.get(0).getCurrentAvailableEnding())
    .build();
```

**`findUpdateSlot`** — four return points, all carry through current values from `licenseWindows.get(0)`. The current values are the same on every slot row for a given asset so first element is always correct:

- Return point 1 (active slot — `now.isAfter(start)`): wrap `licenseWindows.get(resInd)` in a new builder adding `currentAvailableStarting/Ending`
- Return point 2 (no future slot — `resInd == -1`): wrap `licenseWindows.get(licenseWindows.size() - 1)` in a new builder adding `currentAvailableStarting/Ending`
- Return point 3 (merge — within one hour): already builds a new DTO, just add `currentAvailableStarting/Ending`
- Return point 4 (no merge — `ind == 0` or gap > 1 hour): wrap `licenseWindows.get(ind)` in a new builder adding `currentAvailableStarting/Ending`

---

### 9. `SlotBatchService.java` — 4 changes

**Change 1 — `executeUpdateStrategy`**

**Why:** `assetIds` was `List<String>`, now `List<LicenseWindowDto>`. String IDs extracted for `fetchSlotsInBatch`. After `processGroupedSlots`, for NonSeasonNonShow the computed windows don't have `currentAvailableStarting/Ending` because `findLicenseSlotsByProgramId` doesn't carry them — so we set them from the original assets list using a simple map lookup built once, used once, scoped to this method call. For Season/Show this is not needed since current values flow through `processGroupedSlots` directly. Then filter before update.

```java
private void executeUpdateStrategy(LicenseUpdateStrategy strategy, String operationName) {
    log.info(strategy.getLogMessageStart());

    List<LicenseWindowDto> assets = strategy.fetchAssets(
        slotBatchMapper, countryGroup, feedWorkerList);

    if (CollectionUtils.isEmpty(assets)) {
        log.info("operationName={}, status=skipped, reason=no assets found", operationName);
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

    // For NonSeasonNonShow — current values come from assets list since
    // findLicenseSlotsByProgramId queries a different table with no current values.
    // For Season/Show — current values already on computed windows via processGroupedSlots.
    // Building the map here is cheap — assets list is already in memory.
    Map<String, LicenseWindowDto> currentValuesMap = assets.stream()
        .collect(Collectors.toMap(LicenseWindowDto::getContentId, a -> a));

    computedWindows.forEach(w -> {
        if (w.getCurrentAvailableStarting() == null && w.getCurrentAvailableEnding() == null) {
            LicenseWindowDto current = currentValuesMap.get(w.getContentId());
            if (current != null) {
                w.setCurrentAvailableStarting(current.getCurrentAvailableStarting());
                w.setCurrentAvailableEnding(current.getCurrentAvailableEnding());
            }
        }
    });

    List<LicenseWindowDto> actualChanges = computedWindows.stream()
        .filter(w -> !StringUtils.equals(
            w.getAvailableStarting(), w.getCurrentAvailableStarting())
            || !StringUtils.equals(
            w.getAvailableEnding(), w.getCurrentAvailableEnding()))
        .toList();

    log.info("operationName={}, totalFetched={}, toUpdate={}, skipped={}",
        operationName, computedWindows.size(), actualChanges.size(),
        computedWindows.size() - actualChanges.size());

    updateWindowsInBatch(actualChanges);
}
```

**Change 2 — `fetchSlotsInBatch`**

**Why:** Currently uses `CompletableFuture.supplyAsync` which fires all partition fetches simultaneously against the connection pool. Since reads are fast and sequential processing still fits well within the 10-minute schedule window, parallel fetching adds connection pressure with no meaningful time benefit.

```java
private List<LicenseWindowDto> fetchSlotsInBatch(
        List<String> assetIds,
        Function<List<String>, List<LicenseWindowDto>> slotFetcherFunction) {

    List<LicenseWindowDto> allSlots = new ArrayList<>();
    for (List<String> partition :
            ListUtils.partitionList(assetIds, Math.min(1000, batchSize))) {
        allSlots.addAll(slotFetcherFunction.apply(partition));
    }
    return allSlots;
}
```

**Change 3 — `updateWindowsInBatch`**

**Why:** Add empty list guard to avoid unnecessary processing. Improve logging to key=value format for easier log querying.

```java
public void updateWindowsInBatch(List<LicenseWindowDto> updateWindows) {
    if (CollectionUtils.isEmpty(updateWindows)) {
        log.info("No license window updates needed, skipping.");
        return;
    }

    log.info("Starting batch update: totalAssets={}, batchSize={}",
        updateWindows.size(), batchSize);

    List<List<LicenseWindowDto>> partitions =
        ListUtils.partitionLicenseList(updateWindows, batchSize);
    List<CompletableFuture<Void>> futures = new ArrayList<>();

    for (List<LicenseWindowDto> partition : partitions) {
        CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {
            try {
                log.info("chunkNumber={}, chunkSize={}",
                    partition.get(0).getPartitionCt(), partition.size());
                updateBothTables(partition);
            } catch (Exception ex) {
                log.error("chunkNumber={}, error={}",
                    partition.get(0).getPartitionCt(),
                    ErrorMessageUtil.extractError(ex));
                notificationUtil.sendAlarm(ex,
                    HttpStatus.INTERNAL_SERVER_ERROR.name(),
                    String.valueOf(HttpStatus.INTERNAL_SERVER_ERROR.value()),
                    "Partition " + partition.get(0).getPartitionCt(),
                    " DB Connection Error");
            }
        }, taskExecutor);
        futures.add(future);
    }

    CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
    log.info("Batch update completed: totalChunks={}", partitions.size());
}
```

**Change 4 — `slotUpdater`**

**Why:** Add per-strategy timing captures and a final structured summary log so every run produces one line that shows the full picture — duration per strategy and total. Makes debugging and monitoring significantly easier.

```java
@Scheduled(fixedRateString = "#{@schedulerConfig.getBatchSchedulerRate()}")
public void slotUpdater() {
    log.info("Batch started: groupId={}", countryGroup);
    Instant startTime = Instant.now();

    try {
        executeUpdateStrategy(nonSeasonNonShowStrategy,
            "License Update - NonSeasonNonShow");
        Instant t1 = Instant.now();

        executeUpdateStrategy(seasonStrategy,
            "License Update - Season");
        Instant t2 = Instant.now();

        executeUpdateStrategy(showStrategy,
            "License Update - Show");
        Instant endTime = Instant.now();

        log.info("Batch completed: groupId={}, status=success, "
            + "nonSeasonNonShowMs={}, seasonMs={}, showMs={}, totalMs={}",
            countryGroup,
            Duration.between(startTime, t1).toMillis(),
            Duration.between(t1, t2).toMillis(),
            Duration.between(t2, endTime).toMillis(),
            Duration.between(startTime, endTime).toMillis());

    } catch (Exception ex) {
        String errMsg = "Error: " + ErrorMessageUtil.extractError(ex);
        notificationUtil.sendAlarm(ex,
            HttpStatus.INTERNAL_SERVER_ERROR.name(),
            String.valueOf(HttpStatus.INTERNAL_SERVER_ERROR.value()),
            errMsg, " Batch job failed");
        log.error("Batch completed: groupId={}, status=failed, error={}",
            countryGroup, errMsg);
    }
}
```

---

### 10. `ThreadPoolConfig.java`

**Why:** Last night's incident was caused by 15 partitions all firing simultaneously against a Hikari pool of 20 connections with a 30-second timeout. Reducing thread pool to 5 means at most 5 partitions run concurrently, using at most 5 connections at a time. Pool of 20 has 15 in reserve — zero risk of exhaustion. No semaphore, no extra logic — the pool size itself is the throttle.

```java
executor.setCorePoolSize(5);
executor.setMaxPoolSize(5);
```

---

### Files touched — complete list

| File | Change | Reason |
|---|---|---|
| `LicenseWindowDto.java` | Add 2 fields | Carry current stored values for comparison |
| `SlotBatchMapper.xml` | Modify 2 queries | Fetch current stored values alongside asset IDs |
| `SlotBatchMapper.java` | 2 return type changes | Match updated query return types |
| `LicenseUpdateStrategy.java` | Signature updates | Propagate DTO list through strategy interface |
| `NonSeasonNonShowUpdateStrategy.java` | Implement updated signatures | Match interface |
| `SeasonUpdateStrategy.java` | Implement updated signatures + carry current values in fill-in logic | Match interface + correct comparison for no-episode seasons |
| `ShowUpdateStrategy.java` | Implement updated signatures + carry current values in fill-in logic | Match interface + correct comparison for no-season shows |
| `LicenseWindowService.java` | Carry current values through all return points | Computed result needs both sides for comparison |
| `SlotBatchService.java` | Map lookup + filter + sequential fetch + logging | Core fix — only update what changed, reduce DB pressure, improve observability |
| `ThreadPoolConfig.java` | 20/50 → 5/5 | Fix connection pool exhaustion root cause |

10 files, no new files. Ready to write code?
