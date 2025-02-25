import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@ExtendWith(MockitoExtension.class)
public class ConsistentHashRouterTest {

    private List<QueueDto> mockQueues;
    private Map<String, List<QueueDto>> countryQueues;
    private ConsistentHashRouter usRouter;
    private Random random;

    @Mock
    private CountryQueueMapper queueMapper;

    @BeforeEach
    void setup() {
        // Initialize random with a fixed seed for reproducible tests
        random = new Random(42);
        
        // Create queues for multiple countries
        countryQueues = new HashMap<>();
        
        // US gets 4 queues
        List<QueueDto> usQueues = Arrays.asList(
            createQueueDto("US", "us-east", "https://sqs.../us-queue-1", 1),
            createQueueDto("US", "us-east", "https://sqs.../us-queue-2", 2),
            createQueueDto("US", "us-east", "https://sqs.../us-queue-3", 3),
            createQueueDto("US", "us-east", "https://sqs.../us-queue-4", 4)
        );
        countryQueues.put("US", usQueues);
        
        // 10 other countries with 1 queue each
        String[] countries = {"IN", "UK", "CA", "AU", "JP", "KR", "DE", "FR", "BR", "MX"};
        for (String country : countries) {
            List<QueueDto> singleQueue = Collections.singletonList(
                createQueueDto(country, "region", "https://sqs.../" + country.toLowerCase() + "-queue", 1)
            );
            countryQueues.put(country, singleQueue);
        }
        
        // Set up the US router for specific tests
        usRouter = new ConsistentHashRouter(countryQueues.get("US"));
        
        // Create a flat list of all queues for some tests
        mockQueues = countryQueues.values().stream()
                                  .flatMap(List::stream)
                                  .collect(Collectors.toList());
    }
    
    private QueueDto createQueueDto(String countryCode, String region, String queueUrl, int queueNumber) {
        return QueueDto.builder()
                .id((long)(countryCode.hashCode() + queueNumber))
                .countryCode(countryCode)
                .region(region)
                .queueUrl(queueUrl)
                .queueNumber(queueNumber)
                .isActive(true)
                .build();
    }
    
    private String generateProgramId(String countryCode) {
        String[] contentTypes = {"Movie", "Series", "Episode", "Clip"};
        String[] titles = {"Friends", "Titanic", "Batman", "Superman", "Inception", "Matrix", "Avatar", 
                          "GameOfThrones", "BreakingBad", "Squid", "Korean", "Bollywood", "Cricket"};
        
        String contentType = contentTypes[random.nextInt(contentTypes.length)];
        String title = titles[random.nextInt(titles.length)];
        String suffix = contentType.equals("Episode") ? "_S0" + (random.nextInt(5) + 1) + "E" + (random.nextInt(20) + 1) : "";
        
        return countryCode + "_" + contentType.substring(0, 2).toUpperCase() + "_" + title + suffix;
    }
    
    private String generateProviderId() {
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        StringBuilder builder = new StringBuilder();
        for (int i = 0; i < 7; i++) {
            builder.append(chars.charAt(random.nextInt(chars.length())));
        }
        return builder.toString();
    }

    @Test
    void testConsistentRouting() {
        // Test that same asset always routes to the same queue
        for (int i = 0; i < 100; i++) {
            String programId = generateProgramId("US");
            String providerId = generateProviderId();
            
            String queue1 = usRouter.getTargetQueue(programId, providerId, "US");
            String queue2 = usRouter.getTargetQueue(programId, providerId, "US");
            
            assertEquals(queue1, queue2, "Same asset should always route to same queue: " + programId);
        }
    }
    
    @Test
    void testDistributionForAllCountries() {
        // Test distribution across all countries
        Map<String, Map<String, Integer>> distributions = new HashMap<>();
        
        // Initialize distribution maps
        for (String country : countryQueues.keySet()) {
            Map<String, Integer> countryDist = new HashMap<>();
            for (QueueDto queue : countryQueues.get(country)) {
                countryDist.put(queue.getQueueUrl(), 0);
            }
            distributions.put(country, countryDist);
        }
        
        // Generate assets and track distribution
        int assetsPerCountry = 50000 / countryQueues.size();
        for (String country : countryQueues.keySet()) {
            ConsistentHashRouter router = new ConsistentHashRouter(countryQueues.get(country));
            Map<String, Integer> countryDist = distributions.get(country);
            
            for (int i = 0; i < assetsPerCountry; i++) {
                String programId = generateProgramId(country);
                String providerId = generateProviderId();
                
                String queue = router.getTargetQueue(programId, providerId, country);
                countryDist.merge(queue, 1, Integer::sum);
            }
        }
        
        // Print and verify distribution
        for (String country : countryQueues.keySet()) {
            Map<String, Integer> countryDist = distributions.get(country);
            int queueCount = countryQueues.get(country).size();
            int totalAssets = countryDist.values().stream().mapToInt(Integer::intValue).sum();
            double idealPercentage = 100.0 / queueCount;
            
            System.out.println("\nDistribution for " + country + " (" + queueCount + " queues, " + totalAssets + " assets):");
            for (Map.Entry<String, Integer> entry : countryDist.entrySet()) {
                double percentage = (entry.getValue() * 100.0) / totalAssets;
                System.out.printf("  %s: %d assets (%.2f%%)\n", 
                    entry.getKey(), entry.getValue(), percentage);
                
                // If multiple queues, check distribution is reasonable (within 25% of ideal)
                if (queueCount > 1) {
                    double deviation = Math.abs(percentage - idealPercentage);
                    assertTrue(deviation < idealPercentage * 0.25, 
                        "Distribution for " + entry.getKey() + " is outside acceptable range: " + percentage + "%");
                }
            }
        }
    }
    
    @Test
    void testQueueAdditionRedistribution() {
        // Test minimal redistribution when adding queues
        // We'll focus on US since it has multiple queues
        
        int numAssets = 10000;
        List<String> programIds = new ArrayList<>();
        List<String> providerIds = new ArrayList<>();
        
        // Generate test assets
        for (int i = 0; i < numAssets; i++) {
            programIds.add(generateProgramId("US"));
            providerIds.add(generateProviderId());
        }
        
        // Original routing with 4 queues
        Map<String, String> originalRouting = new HashMap<>();
        for (int i = 0; i < numAssets; i++) {
            String targetQueue = usRouter.getTargetQueue(programIds.get(i), providerIds.get(i), "US");
            originalRouting.put(programIds.get(i), targetQueue);
        }
        
        // Add a 5th queue
        List<QueueDto> newQueues = new ArrayList<>(countryQueues.get("US"));
        newQueues.add(createQueueDto("US", "us-east", "https://sqs.../us-queue-5", 5));
        ConsistentHashRouter newRouter = new ConsistentHashRouter(newQueues);
        
        // Check redistribution
        int changes = 0;
        Map<String, Integer> newDistribution = new HashMap<>();
        
        for (int i = 0; i < numAssets; i++) {
            String programId = programIds.get(i);
            String providerId = providerIds.get(i);
            
            String newQueue = newRouter.getTargetQueue(programId, providerId, "US");
            newDistribution.merge(newQueue, 1, Integer::sum);
            
            if (!newQueue.equals(originalRouting.get(programId))) {
                changes++;
            }
        }
        
        // Calculate redistribution percentage
        double changePercentage = (changes * 100.0) / numAssets;
        System.out.println("\nRedistribution when adding 5th queue to US:");
        System.out.printf("  %d assets changed queues (%.2f%%)\n", changes, changePercentage);
        
        // Print new distribution
        System.out.println("New distribution:");
        for (Map.Entry<String, Integer> entry : newDistribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / numAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Theoretical expectation: ~20% redistribution (1/5 of assets)
        // Allow some deviation
        assertTrue(changePercentage > 15.0 && changePercentage < 25.0,
            "Expected ~20% redistribution, got " + changePercentage + "%");
    }
    
    @Test
    void testQueueRemovalRedistribution() {
        // Test redistribution when removing a queue
        int numAssets = 10000;
        List<String> programIds = new ArrayList<>();
        List<String> providerIds = new ArrayList<>();
        
        // Generate test assets
        for (int i = 0; i < numAssets; i++) {
            programIds.add(generateProgramId("US"));
            providerIds.add(generateProviderId());
        }
        
        // Original routing with 4 queues
        Map<String, String> originalRouting = new HashMap<>();
        Map<String, Integer> originalDistribution = new HashMap<>();
        
        for (int i = 0; i < numAssets; i++) {
            String targetQueue = usRouter.getTargetQueue(programIds.get(i), providerIds.get(i), "US");
            originalRouting.put(programIds.get(i), targetQueue);
            originalDistribution.merge(targetQueue, 1, Integer::sum);
        }
        
        // Remove one queue (queue-2)
        List<QueueDto> reducedQueues = countryQueues.get("US").stream()
            .filter(q -> !q.getQueueUrl().endsWith("queue-2"))
            .collect(Collectors.toList());
        
        ConsistentHashRouter reducedRouter = new ConsistentHashRouter(reducedQueues);
        
        // Track redistribution
        int changes = 0;
        Map<String, Integer> newDistribution = new HashMap<>();
        Map<String, Integer> redistributionMap = new HashMap<>();
        
        for (int i = 0; i < numAssets; i++) {
            String programId = programIds.get(i);
            String providerId = providerIds.get(i);
            
            String originalQueue = originalRouting.get(programId);
            String newQueue = reducedRouter.getTargetQueue(programId, providerId, "US");
            
            newDistribution.merge(newQueue, 1, Integer::sum);
            
            if (!newQueue.equals(originalQueue)) {
                changes++;
                redistributionMap.merge(originalQueue + " -> " + newQueue, 1, Integer::sum);
            }
        }
        
        // Calculate and print redistribution
        double changePercentage = (changes * 100.0) / numAssets;
        System.out.println("\nRedistribution when removing queue-2 from US:");
        System.out.printf("  %d assets changed queues (%.2f%%)\n", changes, changePercentage);
        
        // Print original distribution
        System.out.println("Original distribution:");
        for (Map.Entry<String, Integer> entry : originalDistribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / numAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Print new distribution
        System.out.println("New distribution:");
        for (Map.Entry<String, Integer> entry : newDistribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / numAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Print redistribution details
        System.out.println("Redistribution details:");
        for (Map.Entry<String, Integer> entry : redistributionMap.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / numAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Verify that the removed queue's assets were evenly redistributed
        int removedQueueAssets = originalDistribution.getOrDefault("https://sqs.../us-queue-2", 0);
        assertTrue(changes >= removedQueueAssets * 0.9, 
            "Expected at least 90% of removed queue's assets to be redistributed");
    }
    
    @Test
    void testGlobalDistribution() {
        // Test global distribution across all assets and queues
        int totalAssets = 50000;
        Map<String, Integer> globalDistribution = new HashMap<>();
        Map<String, List<String>> assetsByCountry = new HashMap<>();
        
        // Initialize distribution tracking
        for (QueueDto queue : mockQueues) {
            globalDistribution.put(queue.getQueueUrl(), 0);
        }
        
        // Assign assets proportionally to countries
        int totalCountries = countryQueues.size();
        List<String> allAssets = new ArrayList<>();
        
        for (String country : countryQueues.keySet()) {
            List<String> countryAssets = new ArrayList<>();
            int countryAssetCount = totalAssets / totalCountries;
            
            for (int i = 0; i < countryAssetCount; i++) {
                String assetId = generateProgramId(country);
                countryAssets.add(assetId);
                allAssets.add(assetId);
            }
            
            assetsByCountry.put(country, countryAssets);
        }
        
        // Route assets and track distribution
        for (String country : countryQueues.keySet()) {
            ConsistentHashRouter router = new ConsistentHashRouter(countryQueues.get(country));
            List<String> countryAssets = assetsByCountry.get(country);
            
            for (String assetId : countryAssets) {
                String providerId = generateProviderId();
                String queue = router.getTargetQueue(assetId, providerId, country);
                globalDistribution.merge(queue, 1, Integer::sum);
            }
        }
        
        // Print global distribution
        System.out.println("\nGlobal distribution across all queues:");
        for (Map.Entry<String, Integer> entry : globalDistribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / totalAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
    }
    
    @Test
    void testSimilarIdsDistribution() {
        // Test distribution for similar asset IDs (like TV series episodes)
        int numSeries = 10;
        int episodesPerSeries = 500; // 5000 total assets
        Map<String, Integer> distribution = new HashMap<>();
        
        // Initialize distribution map
        for (QueueDto queue : countryQueues.get("US")) {
            distribution.put(queue.getQueueUrl(), 0);
        }
        
        // Generate series and episodes
        for (int series = 1; series <= numSeries; series++) {
            String seriesName = "Series" + series;
            
            for (int episode = 1; episode <= episodesPerSeries; episode++) {
                String programId = "US_EP_" + seriesName + "_S01E" + String.format("%02d", episode);
                String providerId = "PROVIDER1";
                
                String queue = usRouter.getTargetQueue(programId, providerId, "US");
                distribution.merge(queue, 1, Integer::sum);
            }
        }
        
        // Print distribution for series episodes
        System.out.println("\nDistribution for TV series episodes:");
        int totalAssets = numSeries * episodesPerSeries;
        for (Map.Entry<String, Integer> entry : distribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / totalAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Check that distribution is reasonably balanced
        double idealPercentage = 100.0 / countryQueues.get("US").size();
        for (int count : distribution.values()) {
            double percentage = (count * 100.0) / totalAssets;
            double deviation = Math.abs(percentage - idealPercentage);
            
            assertTrue(deviation < idealPercentage * 0.3, 
                "Distribution for similar IDs is outside acceptable range: " + percentage + "%");
        }
    }
    
    @Test
    void testPerformanceBenchmark() {
        // Performance test for a large number of lookups
        int numAssets = 100000;
        List<String> programIds = new ArrayList<>();
        List<String> providerIds = new ArrayList<>();
        
        // Generate assets first to avoid timing the generation
        for (int i = 0; i < numAssets; i++) {
            programIds.add(generateProgramId("US"));
            providerIds.add(generateProviderId());
        }
        
        // Time the lookups
        long startTime = System.nanoTime();
        
        for (int i = 0; i < numAssets; i++) {
            usRouter.getTargetQueue(programIds.get(i), providerIds.get(i), "US");
        }
        
        long endTime = System.nanoTime();
        double totalTimeMs = (endTime - startTime) / 1_000_000.0;
        double avgLookupTimeMs = totalTimeMs / numAssets;
        
        System.out.println("\nPerformance benchmark:");
        System.out.printf("  %d lookups in %.2f ms (%.5f ms per lookup)\n", 
            numAssets, totalTimeMs, avgLookupTimeMs);
        
        // Verify performance is acceptable
        assertTrue(avgLookupTimeMs < 0.05, 
            "Average lookup time exceeds target: " + avgLookupTimeMs + " ms");
    }
    
    @Test
    void testConcurrentLookups() {
        // Test concurrent lookups to verify thread safety
        int numThreads = 10;
        int lookupsPerThread = 5000;
        Map<String, Integer> distribution = new ConcurrentHashMap<>();
        
        // Initialize distribution map
        for (QueueDto queue : countryQueues.get("US")) {
            distribution.put(queue.getQueueUrl(), 0);
        }
        
        // Create and start threads
        List<Thread> threads = new ArrayList<>();
        for (int t = 0; t < numThreads; t++) {
            Thread thread = new Thread(() -> {
                for (int i = 0; i < lookupsPerThread; i++) {
                    String programId = generateProgramId("US");
                    String providerId = generateProviderId();
                    
                    String queue = usRouter.getTargetQueue(programId, providerId, "US");
                    distribution.merge(queue, 1, Integer::sum);
                }
            });
            threads.add(thread);
            thread.start();
        }
        
        // Wait for all threads to complete
        for (Thread thread : threads) {
            try {
                thread.join();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                fail("Thread interrupted");
            }
        }
        
        // Print distribution
        System.out.println("\nDistribution with concurrent lookups:");
        int totalAssets = numThreads * lookupsPerThread;
        for (Map.Entry<String, Integer> entry : distribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / totalAssets;
            System.out.printf("  %s: %d assets (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Verify all expected lookups were performed
        assertEquals(totalAssets, distribution.values().stream().mapToInt(Integer::intValue).sum(),
            "Not all lookups were counted in the distribution");
    }
}