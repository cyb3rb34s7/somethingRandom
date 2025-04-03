// DTO for Asset Updates
@Data
@Builder
public class AssetUpdateDTO {
    private String cntyCode;
    private String contentId;
    private String episodeId;
    private String deeplinkId;
    private String deeplinkPayload;
    private String type; // "Show" or "Season"
    
    // Builder method to construct the deeplink payload JSON
    public static class AssetUpdateDTOBuilder {
        public AssetUpdateDTOBuilder withEpisodeId(String episodeId) {
            this.episodeId = episodeId;
            this.deeplinkId = episodeId; // Set deeplinkId to episodeId
            
            // Construct deeplink payload JSON with the episode ID
            JSONObject payloadJson = new JSONObject();
            JSONObject deeplinkData = new JSONObject();
            deeplinkData.put("content_id", episodeId);
            deeplinkData.put("content_type", "episode");
            // Add other required fields
            payloadJson.put("deeplink_data", deeplinkData);
            
            this.deeplinkPayload = payloadJson.toString();
            return this;
        }
    }
}

// Service to handle updates
@Service
public class AssetUpdateService {
    @Autowired
    private AssetMapper assetMapper;
    
    public void updateAssetDeeplinks(String countryCode) {
        // 1. Get assets that need updates
        List<Map<String, Object>> assetsToUpdate = assetMapper.findAssetsForDeeplinkUpdate(countryCode);
        
        // 2. Process and build update DTOs
        List<AssetUpdateDTO> updateList = new ArrayList<>();
        
        for (Map<String, Object> asset : assetsToUpdate) {
            AssetUpdateDTO updateDTO = AssetUpdateDTO.builder()
                .cntyCode(asset.get("cnty_cd").toString())
                .contentId(asset.get("content_id").toString())
                .type(asset.get("type").toString())
                .withEpisodeId(asset.get("episode_id").toString())
                .build();
                
            updateList.add(updateDTO);
        }
        
        // 3. Perform batch update
        if (!updateList.isEmpty()) {
            int batchSize = 100;
            for (int i = 0; i < updateList.size(); i += batchSize) {
                int endIndex = Math.min(i + batchSize, updateList.size());
                List<AssetUpdateDTO> batch = updateList.subList(i, endIndex);
                assetMapper.batchUpdateDeeplinks(batch);
                log.info("Updated batch of {} assets", batch.size());
            }
        }
    }
}





<update id="batchUpdateDeeplinks" parameterType="java.util.List">
    <foreach collection="list" item="item" separator=";">
        UPDATE master_asset_table
        SET deeplink_payload = #{item.deeplinkPayload},
            deeplink_id = #{item.deeplinkId}
        WHERE content_id = #{item.contentId}
        AND country = #{item.cntyCode}
    </foreach>
</update>