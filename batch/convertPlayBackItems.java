// Replace the existing convertPlaybackItems method with this refactored version:

//Playback Item: Convert to type of dynamodb before saving to db
public List<Map<String, Object>> convertPlaybackItems(Program program, String country) {
    List<Map<String, Object>> playbackItemList = new ArrayList<>();
    
    try {
        if (program.getPlaybackItems() == null || country == null) {
            log.info("Program PlaybackItem is empty!");
            return playbackItemList;
        }

        PlaybackItem matchedItem = findPlaybackItemForCountry(program.getPlaybackItems(), country);
        
        if (matchedItem != null) {
            Map<String, Object> playbackItemMap = buildPlaybackItemMap(matchedItem, program, country);
            playbackItemList.add(playbackItemMap);
            log.info("Program PlaybackItem : {}", playbackItemList.stream().toString());
        } else {
            log.info("Program Country code does not match with any of the playback items");
        }
        
    } catch (ElementValueCheckException e) {
        log.error("Date time element value check failed! {}", e.getMessage());
        throw new ElementValueCheckException(e.getMessage());
    } catch (DateTimeCheckFailedException e) {
        log.error("Date time check failed! {}", e.getMessage());
        throw new DateTimeCheckFailedException(e.getMessage());
    } catch (Exception e) {
        log.error("Exception occurred while converting PlaybackItem! {}", e.getMessage());
        throw new ConversionToItemException(
                "Exception occurred while converting PlaybackItem! " + e.getMessage());
    }

    return playbackItemList;
}

// New helper method: Find the playback item matching the country code
private PlaybackItem findPlaybackItemForCountry(List<PlaybackItem> playbackItems, String country) {
    for (PlaybackItem item : playbackItems) {
        if (country.equals(item.getCountryCode())) {
            return item;
        }
    }
    return null;
}

// New helper method: Build the complete playback item map
private Map<String, Object> buildPlaybackItemMap(PlaybackItem playbackItem, Program program, String country) {
    Map<String, Object> playbackItemMap = new HashMap<>();
    
    // Add mandatory fields
    playbackItemMap.put(DEEPLINK_PAYLOAD, playbackItem.getDeeplinkPayload());
    playbackItemMap.put(COUNTRY_CODE, playbackItem.getCountryCode());
    playbackItemMap.put(STREAM_URL, playbackItem.getStreamUrl());
    playbackItemMap.put(LICENSE, playbackItem.getLicense());
    playbackItemMap.put(QUALITY, playbackItem.getQuality());
    playbackItemMap.put(AVAILABLE_STARTING, playbackItem.getAvailableStarting());
    playbackItemMap.put(AVAILABLE_ENDING, playbackItem.getAvailableEnding());
    
    // Add optional fields
    addOptionalPlaybackFields(playbackItemMap, playbackItem);
    
    // Find the index for helper methods (maintain compatibility)
    int itemIndex = program.getPlaybackItems().indexOf(playbackItem);
    
    // Generate complex nested structures using existing helper methods
    generateAttribute(program, itemIndex, playbackItemMap);
    generateSubtitle(program, itemIndex, new ArrayList<>(), playbackItemMap);
    generateLicenseWindow(program, itemIndex, new ArrayList<>(), playbackItemMap);
    generateEventWindow(program, itemIndex, new ArrayList<>(), playbackItemMap);
    generateDrm(program, itemIndex, new ArrayList<>(), playbackItemMap);
    
    // Add geo restrictions if present
    if (playbackItem.getGeoRestrictions() != null) {
        playbackItemMap.put(GEO_RESTRICTIONS, 
            convertGeoRestrictions(playbackItem.getGeoRestrictions()));
    }
    
    return playbackItemMap;
}

// New helper method: Add optional fields to playback item map
private void addOptionalPlaybackFields(Map<String, Object> playbackItemMap, PlaybackItem playbackItem) {
    if (playbackItem.getAudioLanguages() != null) {
        playbackItemMap.put(AUDIO_LANGUAGES, playbackItem.getAudioLanguages());
    }
    if (playbackItem.getSubtitleLanguages() != null) {
        playbackItemMap.put(SUBTITLE_LANGUAGES, playbackItem.getSubtitleLanguages());
    }
    if (playbackItem.getPrice() != null) {
        playbackItemMap.put(PRICE, playbackItem.getPrice());
    }
    if (playbackItem.getCurrency() != null) {
        playbackItemMap.put(CURRENCY, playbackItem.getCurrency());
    }
    if (playbackItem.getStreamType() != null) {
        playbackItemMap.put(STREAM_TYPE, playbackItem.getStreamType());
    }
}