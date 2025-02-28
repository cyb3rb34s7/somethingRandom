package com.yourcompany.dbapi.test;

import com.yourcompany.dbapi.model.QueueDto;
import com.yourcompany.dbapi.router.RobustConsistentHashRouter;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Simple test class to evaluate the distribution quality of the router.
 */
public class RouterTest {

    /**
     * Test the router with random asset IDs and new router instances for each asset.
     */
    public static void main(String[] args) {
        // Create test queues for US region
        List<QueueDto> usQueues = createTestQueues(4, "US");
        
        // Number of test assets to create
        final int NUM_ASSETS = 1000;
        
        // Map to track how many assets go to each queue
        Map<String, Integer> queueCounts = new HashMap<>();
        for (QueueDto queue : usQueues) {
            queueCounts.put(queue.getAssetSqsUrl(), 0);
        }
        
        // Test distribution by routing random assets
        System.out.println("Testing router with " + NUM_ASSETS + " random assets...");
        System.out.println("-----------------------------------------------");
        
        for (int i = 0; i < NUM_ASSETS; i++) {
            // Generate a random asset ID (similar to your real-world IDs)
            String assetId = generateRandomAssetId("US");
            
            // Create a new router instance for each asset
            // This simulates your Lambda environment where a new router is created per request
            RobustConsistentHashRouter router = new RobustConsistentHashRouter(usQueues);
            
            // Get the selected queue URL
            String selectedQueueUrl = router.getQueueForAsset(assetId);
            
            // Update counts
            queueCounts.put(selectedQueueUrl, queueCounts.get(selectedQueueUrl) + 1);
            
            // Print first 10 assets for visibility
            if (i < 10) {
                System.out.println("Asset " + assetId + " → " + selectedQueueUrl);
            }
        }
        
        // Print distribution results
        System.out.println("\nFinal Distribution:");
        System.out.println("------------------");
        
        int total = 0;
        for (Map.Entry<String, Integer> entry : queueCounts.entrySet()) {
            total += entry.getValue();
            double percentage = (entry.getValue() * 100.0) / NUM_ASSETS;
            System.out.printf("%s: %d assets (%.2f%%)\n", 
                    entry.getKey(), entry.getValue(), percentage);
        }
        
        // Calculate ideal and deviation
        double idealCount = (double) NUM_ASSETS / usQueues.size();
        double maxDeviation = 0;
        
        for (int count : queueCounts.values()) {
            double deviation = Math.abs(count - idealCount);
            maxDeviation = Math.max(maxDeviation, deviation);
        }
        
        double maxDeviationPercent = (maxDeviation / idealCount) * 100;
        
        System.out.println("\nIdeal distribution: " + idealCount + " assets per queue");
        System.out.printf("Maximum deviation: %.2f assets (%.2f%%)\n", 
                maxDeviation, maxDeviationPercent);
    }
    
    /**
     * Create a list of test QueueDto objects.
     */
    private static List<QueueDto> createTestQueues(int count, String country) {
        List<QueueDto> queues = new ArrayList<>();
        
        for (int i = 1; i <= count; i++) {
            QueueDto queue = new QueueDto();
            String queueUrl = "https://sqs." + country.toLowerCase() + 
                    ".amazonaws.com/" + country + "_QUEUE_" + i;
            
            queue.setAssetSqsUrl(queueUrl);
            queue.setCountry(country);
            queue.setRegion("DEFAULT");
            queue.setActive(true);
            queue.setQueueNumber(i);
            
            queues.add(queue);
        }
        
        return queues;
    }
    
    /**
     * Generate a random asset ID similar to real-world format.
     */
    private static String generateRandomAssetId(String country) {
        String[] types = {"MP", "TV", "DOC", "NEWS", "SPORTS"};
        String[] titles = {"GODFATHER", "AVATAR", "FRIENDS", "OFFICE", "MATRIX", 
                         "BATMAN", "SIMPSONS", "BREAKING", "THRONES"};
        String[] seasonNums = {"S01", "S02", "S03", "S04", "S05"};
        
        Random random = new Random();
        
        String type = types[random.nextInt(types.length)];
        String title = titles[random.nextInt(titles.length)];
        String season = seasonNums[random.nextInt(seasonNums.length)];
        
        // Add some randomness to ensure uniqueness
        int randomNum = random.nextInt(10000);
        
        return country + "_" + type + "_" + title + "_EP_" + season + "_" + randomNum;
    }
    
    /**
     * Simple QueueDto implementation for testing.
     */
    private static class QueueDto {
        private String assetSqsUrl;
        private String country;
        private String region;
        private boolean active;
        private int queueNumber;
        
        public String getAssetSqsUrl() {
            return assetSqsUrl;
        }
        
        public void setAssetSqsUrl(String assetSqsUrl) {
            this.assetSqsUrl = assetSqsUrl;
        }
        
        public String getCountry() {
            return country;
        }
        
        public void setCountry(String country) {
            this.country = country;
        }
        
        public String getRegion() {
            return region;
        }
        
        public void setRegion(String region) {
            this.region = region;
        }
        
        public boolean isActive() {
            return active;
        }
        
        public void setActive(boolean active) {
            this.active = active;
        }
        
        public int getQueueNumber() {
            return queueNumber;
        }
        
        public void setQueueNumber(int queueNumber) {
            this.queueNumber = queueNumber;
        }
    }
}