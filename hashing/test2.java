import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

@ExtendWith(MockitoExtension.class)
public class ConsistentHashRouterTest {

    @Mock
    private CountryQueueMapper queueMapper;

    // The router will be created and injected in the setup method
    private ConsistentHashRouter usRouter;
    
    private List<QueueDto> mockQueues;
    private Map<String, List<QueueDto>> countryQueues;
    private Random random;

    @BeforeEach
    void setup() {
        // Initialize random with a fixed seed for reproducible tests
        random = new Random(42);
        
        // Create queues for multiple countries
        countryQueues = new HashMap<>();
        
        // US gets 4 queues
        List<QueueDto> usQueues = Arrays.asList(
            createQueueDto("US", "us-east", "https://sqs.../us-asset-queue-1", 1),
            createQueueDto("US", "us-east", "https://sqs.../us-asset-queue-2", 2),
            createQueueDto("US", "us-east", "https://sqs.../us-asset-queue-3", 3),
            createQueueDto("US", "us-east", "https://sqs.../us-asset-queue-4", 4)
        );
        countryQueues.put("US", usQueues);
        
        // 10 other countries with 1 queue each
        String[] countries = {"IN", "UK", "CA", "AU", "JP", "KR", "DE", "FR", "BR", "MX"};
        for (String country : countries) {
            List<QueueDto> singleQueue = Collections.singletonList(
                createQueueDto(country, "region", "https://sqs.../" + country.toLowerCase() + "-asset-queue", 1)
            );
            countryQueues.put(country, singleQueue);
        }
        
        // Create a flat list of all queues for some tests
        mockQueues = countryQueues.values().stream()
                               .flatMap(List::stream)
                               .collect(Collectors.toList());

        // Create the US router manually for testing
        usRouter = new ConsistentHashRouter(countryQueues.get("US"));
    }
    
    private QueueDto createQueueDto(String countryCode, String region, String assetQueueUrl, int queueNumber) {
        QueueDto dto = new QueueDto();
        dto.setId((long)(countryCode.hashCode() + queueNumber));
        dto.setCountryCode(countryCode);
        dto.setRegion(region);
        dto.setAssetQueueUrl(assetQueueUrl);
        dto.setLicenseUrl("https://sqs.../" + countryCode.toLowerCase() + "-license-queue"); // Not used in tests
        dto.setQueueNumber(queueNumber);
        dto.setActive(true);
        return dto;
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
                countryDist.put(queue.getAssetQueueUrl(), 0);
            }
            distributions.put(country, countryDist);
        }
        
        // Generate assets and track distribution
        int assetsPerCountry = 5000; // 5000 per country for quicker tests
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
                    assertTrue(deviation < idealPercentage * 0.30, 
                        "Distribution for " + entry.getKey() + " is outside acceptable range: " + percentage + "% (ideal: " + idealPercentage + "%)");
                }
            }
        }
    }
    
    @Test
    void testQueueAdditionRedistribution() {
        // Test minimal redistribution when adding queues
        // We'll focus on US since it has multiple queues
        
        int numAssets = 5000;
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
        newQueues.add(createQueueDto("US", "us-east", "https://sqs.../us-asset-queue-5", 5));
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
        // Allow some deviation (15-30%)
        assertTrue(changePercentage > 15.0 && changePercentage < 30.0,
            "Expected ~20% redistribution, got " + changePercentage + "%");
    }
    
    @Test
    void testPerformanceBenchmark() {
        // Performance test for a large number of lookups
        int numAssets = 10000; // Reduced for quicker tests
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
        
        // Verify performance is acceptable - use a higher threshold to accommodate
        // different environments
        assertTrue(avgLookupTimeMs < 0.1, 
            "Average lookup time exceeds target: " + avgLookupTimeMs + " ms");
    }

    // This test specifically tests series with sequential episode numbers
    @Test
    void testTVSeriesEpisodeDistribution() {
        int numSeries = 5;
        int episodesPerSeries = 200;
        Map<String, Integer> distribution = new HashMap<>();
        
        // Initialize distribution map
        for (QueueDto queue : countryQueues.get("US")) {
            distribution.put(queue.getAssetQueueUrl(), 0);
        }
        
        // Generate TV series episodes with sequential IDs
        for (int s = 1; s <= numSeries; s++) {
            String seriesName = "TVSeries" + s;
            
            for (int e = 1; e <= episodesPerSeries; e++) {
                // Format: US_EP_TVSeries1_S01E01, US_EP_TVSeries1_S01E02, etc.
                String programId = String.format("US_EP_%s_S01E%02d", seriesName, e);
                String providerId = "X1HLAP5"; // Same provider for series
                
                String queueUrl = usRouter.getTargetQueue(programId, providerId, "US");
                distribution.merge(queueUrl, 1, Integer::sum);
            }
        }
        
        // Print distribution
        System.out.println("\nDistribution for TV series episodes (sequential IDs):");
        int totalEpisodes = numSeries * episodesPerSeries;
        for (Map.Entry<String, Integer> entry : distribution.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / totalEpisodes;
            System.out.printf("  %s: %d episodes (%.2f%%)\n", 
                entry.getKey(), entry.getValue(), percentage);
        }
        
        // Verify reasonably balanced distribution
        double idealPercentage = 100.0 / countryQueues.get("US").size();
        for (int count : distribution.values()) {
            double percentage = (count * 100.0) / totalEpisodes;
            double deviation = Math.abs(percentage - idealPercentage);
            
            // For TV series with sequential IDs, allow a bit more variance (35%)
            assertTrue(deviation < idealPercentage * 0.35, 
                "Distribution for TV series episodes is outside acceptable range: " + percentage + "%");
        }
    }
}