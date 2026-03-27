Let me re-read the exact update query and payload structure one final time to be precise.Good. Now I have everything I need. Here is the exact, final plan — nothing more, nothing less.

---

## Final Plan — Exact Changes Required

---

### 1. New DTO — `DeeplinkUpdateDto`

New file. Fields:
- `contentId` — the show or season ID
- `countryCode`
- `providerId`
- `currentDeeplinkId` — what's currently stored in `DEEPLINK_ID` column (fetched from DB, used for comparison)
- `newDeeplinkId` — the correct first available episode ID (computed, used for update)
- `deeplinkPayload` — the JSON string built in Java (used for update)

---

### 2. `LicenseWindowDto` — Add 2 fields

Add `currentAvailableStarting` and `currentAvailableEnding`. These carry the currently stored window values so Java can compare after computing the new window and skip assets where nothing changed.

---

### 3. `SlotBatchMapper.xml` — Changes to existing queries + new queries

**Change 1 — `findAssetWithMultipleSlots`**

Add `VOD.AVAILABLE_STARTING as currentAvailableStarting` and `VOD.EXP_DATE as currentAvailableEnding` to SELECT. Both columns already exist on the `VOD` join — no new join. Add them to `GROUP BY`. Return type changes from `String` to `LicenseWindowDto`.

**Change 2 — `findAssetByType`**

Add `VOD.AVAILABLE_STARTING as currentAvailableStarting` and `VOD.EXP_DATE as currentAvailableEnding` to SELECT. Already on the same table being queried. Return type changes from `String` to `LicenseWindowDto`.

**New Query 1 — `findShowsForDeeplinkSync`**

```sql
SELECT
  VOD.CONTENT_ID      as contentId,
  VOD.CNTY_CD         as countryCode,
  VOD.VC_CP_ID        as providerId,
  VOD.DEEPLINK_ID     as currentDeeplinkId
FROM ITVSTD_O.STD_VC_VOD_CONTENT VOD
JOIN ITVSTD_O.STD_VC_VOD_CP CP
  ON VOD.CNTY_CD = CP.COUNTRY_CD AND VOD.VC_CP_ID = CP.VC_CP_ID
WHERE VOD."TYPE" = 'SHOW'
  AND UPPER(VOD.FEED_WORKER) IN (...)
  AND CP."GROUP" = #{countryGroup}
```

Returns `List<DeeplinkUpdateDto>`.

**New Query 2 — `findSeasonsForDeeplinkSync`**

Identical to above but `VOD."TYPE" = 'SEASON'`. Returns `List<DeeplinkUpdateDto>`.

**New Query 3 — `findFirstEpisodeForShows`**

Batched version of `getDeeplinkId` from VOD importer. For each showId in the list, fetch the first available episode ordered by `SEASON_NO, EPISODE_NO`. Returns `(showId, episodeContentId, episodeRatings)`.

```sql
SELECT
  A.SHOW_ID     as contentId,
  A.CONTENT_ID  as newDeeplinkId,
  A.RATINGS     as ratings
FROM ITVSTD_O.STD_VC_VOD_CONTENT A
WHERE A.CNTY_CD = #{countryCode}
  AND LOWER(A.TYPE) = 'episode'
  AND A.SHOW_ID IN (...)
  AND A.ROWID IN (
    SELECT FIRST_VALUE(ROWID) OVER (
      PARTITION BY SHOW_ID
      ORDER BY SEASON_NO, EPISODE_NO
    )
    FROM ITVSTD_O.STD_VC_VOD_CONTENT
    WHERE SHOW_ID IN (...)
      AND CNTY_CD = #{countryCode}
      AND LOWER(TYPE) = 'episode'
  )
```

Returns `List<DeeplinkUpdateDto>` with `contentId=showId`, `newDeeplinkId=episodeContentId`, and a separate `ratings` field on the DTO.

**New Query 4 — `findFirstEpisodeForSeasons`**

Same pattern but `PARTITION BY SEASON_ID ORDER BY EPISODE_NO`. Returns `contentId=seasonId`, `newDeeplinkId=episodeContentId`, `ratings`.

**New Query 5 — `updateDeeplinks`** (for `STD_VC_VOD_CONTENT`)

```sql
<foreach collection="assets" item="asset" open="begin " close=";end;" separator=";">
  UPDATE ITVSTD_O.STD_VC_VOD_CONTENT
  SET
    DEEPLINK_ID      = #{asset.newDeeplinkId, jdbcType=VARCHAR},
    DEEPLINK_PAYLOAD = #{asset.deeplinkPayload, jdbcType=VARCHAR}
  WHERE
    CONTENT_ID = #{asset.contentId, jdbcType=VARCHAR}
    AND CNTY_CD = #{asset.countryCode, jdbcType=VARCHAR}
    AND VC_CP_ID = #{asset.providerId, jdbcType=VARCHAR}
</foreach>
```

**New Query 6 — `updateDeeplinksCP`** (for `STD_CMS_VOD_CP_CONTENT`)

Identical but targets `STD_CMS_VOD_CP_CONTENT`. Same `BEGIN...END` foreach pattern.

---

### 4. `SlotBatchMapper.java` — Interface changes

- `findAssetWithMultipleSlots` return type: `List<String>` → `List<LicenseWindowDto>`
- `findAssetByType` return type: `List<String>` → `List<LicenseWindowDto>`
- Add: `List<DeeplinkUpdateDto> findShowsForDeeplinkSync(int countryGroup, List<String> feedWorkers)`
- Add: `List<DeeplinkUpdateDto> findSeasonsForDeeplinkSync(int countryGroup, List<String> feedWorkers)`
- Add: `List<DeeplinkUpdateDto> findFirstEpisodeForShows(@Param("showIds") List<String> showIds, @Param("countryCode") String countryCode)`
- Add: `List<DeeplinkUpdateDto> findFirstEpisodeForSeasons(@Param("seasonIds") List<String> seasonIds, @Param("countryCode") String countryCode)`
- Add: `void updateDeeplinks(List<DeeplinkUpdateDto> assets)`
- Add: `void updateDeeplinksCP(List<DeeplinkUpdateDto> assets)`

---

### 5. `LicenseUpdateStrategy` interface — Signature change

`fetchAssetIds` → renamed to `fetchAssets`, return type `List<String>` → `List<LicenseWindowDto>`. All three strategy implementations update accordingly.

---

### 6. `LicenseWindowService` — Carry through current values

`findUpdateSlot` — the returned `LicenseWindowDto` must carry `currentAvailableStarting` and `currentAvailableEnding` from the input list's first element (same value on all slots for the same asset).

`findMinStartAndMaxEnd` — same, carry through `currentAvailableStarting` and `currentAvailableEnding` from first element of list.

---

### 7. `SlotBatchService` — Core changes

**`executeUpdateStrategy`** — after `processGroupedSlots` returns computed windows, add Java filter before calling `updateWindowsInBatch`:

```java
List<LicenseWindowDto> actualChanges = updateWindows.stream()
    .filter(w -> !Objects.equals(w.getAvailableStarting(), w.getCurrentAvailableStarting())
              || !Objects.equals(w.getAvailableEnding(), w.getCurrentAvailableEnding()))
    .toList();

log.info("{}: {} fetched, {} need update, {} skipped",
    operationName, updateWindows.size(), actualChanges.size(),
    updateWindows.size() - actualChanges.size());

updateWindowsInBatch(actualChanges);
```

**`fetchSlotsInBatch`** — remove `CompletableFuture.supplyAsync`. Plain sequential loop on the scheduling thread.

**`updateWindowsInBatch`** — replace unbounded `CompletableFuture.runAsync` with `Semaphore(5)` controlling how many partitions run concurrently against the thread pool.

**`updateBothTables`** — remove `@Transactional`. Replace with `TransactionTemplate` injected into `SlotBatchService`. Wrap the two mapper calls inside `transactionTemplate.execute()`.

**`slotUpdater`** — add two new calls after the three existing strategies:
```java
deeplinkSyncService.syncShowDeeplinks(countryGroup, feedWorkerList);
deeplinkSyncService.syncSeasonDeeplinks(countryGroup, feedWorkerList);
```
Add timing for both. Add one structured summary log at the end covering all five operations.

---

### 8. New `DeeplinkSyncService`

Single responsibility — deeplink sync. Contains `syncShowDeeplinks` and `syncSeasonDeeplinks`. Each method:

1. Fetch all shows/seasons with `currentDeeplinkId` via `findShowsForDeeplinkSync` / `findSeasonsForDeeplinkSync`
2. Extract IDs, call `findFirstEpisodeForShows` / `findFirstEpisodeForSeasons` in chunks of `batchSize` — sequential, same thread
3. Build a map of `contentId → (newDeeplinkId, ratings)`
4. Java filter — keep only assets where:
   - `currentDeeplinkId` is null, OR
   - `newDeeplinkId` is null (no episodes exist — skip entirely, don't update), OR
   - `currentDeeplinkId != newDeeplinkId`
5. For filtered assets, build `DEEPLINK_PAYLOAD` JSON:
   ```json
   {"deeplink_data": {"content_type": "tvshow", "content_id": "<newDeeplinkId>", "series_id": "<contentId>", "ratings": "<episodeRatings>"}}
   ```
   Set `newDeeplinkId` and `deeplinkPayload` on each `DeeplinkUpdateDto`
6. Call `updateDeeplinksInBatch(assets)` — same `Semaphore(5)` + `TransactionTemplate` pattern as license window updates
7. Log summary: `"Deeplink sync [SHOW/SEASON]: X checked, Y updated, Z skipped, W failed"`

---

### 9. `application.properties`

Change `spring.datasource.hikari.maxLifetime` from `2000000` to `600000` to match ECS.

---

### Files touched — complete list

| File | Type |
|---|---|
| `LicenseWindowDto` | Add 2 fields |
| `DeeplinkUpdateDto` | New |
| `SlotBatchMapper.xml` | 2 query changes, 6 new queries |
| `SlotBatchMapper.java` | 2 return type changes, 6 new methods |
| `LicenseUpdateStrategy` | Signature change |
| `NonSeasonNonShowUpdateStrategy` | Updated signature |
| `SeasonUpdateStrategy` | Updated signature |
| `ShowUpdateStrategy` | Updated signature |
| `LicenseWindowService` | Carry through current values |
| `SlotBatchService` | Filter, sequential fetch, Semaphore, TransactionTemplate, deeplink calls, summary log |
| `DeeplinkSyncService` | New |
| `application.properties` | Fix maxLifetime |

---

Does this look right to you? Ready to start writing code?
