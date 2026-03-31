Good question. Let me trace through all three flows carefully.

**NonSeasonNonShow** — handled. `findAssetWithMultipleSlots` returns current values, map lookup sets them on computed windows, filter works correctly.

**Season** — handled. `findAssetByType(SEASON)` returns current values on the DTO. `processGroupedSlots` in `SeasonUpdateStrategy` passes `assets` (which have current values) into the fill-in logic. `findMinStartAndMaxEnd` in `LicenseWindowService` carries `currentAvailableStarting/Ending` from `licenseWindows.get(0)` through to the result. The slots fetched by `findEpisodeSlotsBySeasonId` don't carry current values — but they don't need to, because `findMinStartAndMaxEnd` picks them up from the first element of the list, which comes from the `slotsByAsset` map. 

Wait — actually there's a problem here. `slotsByAsset` is built from `allSlots` which comes from `findEpisodeSlotsBySeasonId`. Those slot rows have no `currentAvailableStarting/Ending` — they're episode rows. So when `findMinStartAndMaxEnd` reads `licenseWindows.get(0).getCurrentAvailableStarting()`, it gets null. The current values from `findAssetByType` are on the `assets` list, but that's not what gets passed into `findMinStartAndMaxEnd`.

So Season and Show have **the same problem** as NonSeasonNonShow — current values don't flow through to the computed result naturally. The map lookup in `executeUpdateStrategy` handles it uniformly for all three. Since the map is built from `assets` in all cases, it works for Season and Show too — no special handling needed per strategy.

So the answer is: **all three are handled by the same map lookup in `executeUpdateStrategy`**. The Season and Show strategies don't need any special treatment in `processGroupedSlots` for current values. The fill-in logic for no-episode/no-season assets in Season and Show strategies still needs `currentAvailableStarting/Ending` on the placeholder DTO — but the map lookup in `executeUpdateStrategy` will set it there too after `processGroupedSlots` returns.

This actually simplifies the plan slightly — `SeasonUpdateStrategy` and `ShowUpdateStrategy` don't need to carry current values in their fill-in logic. The placeholder DTO can stay simple as it is today, and the map lookup in `executeUpdateStrategy` handles setting current values uniformly across all three strategies after `processGroupedSlots` returns. Cleaner and consistent.

Does that answer your question?

Yes, one change to the plan.

**Remove this from `SeasonUpdateStrategy` and `ShowUpdateStrategy`** — the part where we carry current values onto the placeholder DTO in `processGroupedSlots`:

```java
// REMOVE THIS — not needed
slotsByAsset.put(asset.getContentId(),
    List.of(LicenseWindowDto.builder()
        .contentId(asset.getContentId())
        .currentAvailableStarting(asset.getCurrentAvailableStarting())  // remove
        .currentAvailableEnding(asset.getCurrentAvailableEnding())      // remove
        .build()));
```

**Keep it as it is today** — the placeholder stays simple:

```java
slotsByAsset.put(contentId,
    List.of(LicenseWindowDto.builder().contentId(contentId).build()));
```

The map lookup in `executeUpdateStrategy` handles setting `currentAvailableStarting/Ending` on the computed results uniformly for all three strategies after `processGroupedSlots` returns. So Season and Show strategies need zero changes to their `processGroupedSlots` logic — they stay exactly as they are today.

**The only signature changes needed in Season and Show strategies are:**
- `fetchAssetIds` → `fetchAssets`, return type `List<LicenseWindowDto>`
- `getFetchSlotsLogMessage` parameter `List<String>` → `List<LicenseWindowDto>`
- `getProcessingLogMessage` parameter `List<String>` → `List<LicenseWindowDto>`
- `processGroupedSlots` last parameter `List<String>` → `List<LicenseWindowDto>`, but internally still just extract `contentId` as string where needed

Everything else in the plan stays exactly as described. Ready to write code?
