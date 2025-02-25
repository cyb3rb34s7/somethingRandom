import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Test suite for the ConsistentHashRouter implementation.
 * These tests verify that the consistent hashing algorithm works as expected
 * with proper distribution and minimal redistribution when queues change.
 */
@ExtendWith(MockitoExtension.class)
public class ConsistentHashRouterTest {

    private static final Logger log = LoggerFactory.getLogger(ConsistentHashRouterTest.class);

    @Mock
    private CountryQueueMapper queueMapper;

    private List<QueueDto> allQueues;
    private Map<String, List<QueueDto>> countryToQueues;
    private Random random;

    @BeforeEach
    void setup() {
        // Use fixed seed for reproducible tests
        random = new Random(42);
        
        // Initialize test data
        countryToQueues = new HashMap<>();
        
        // Create 4 queues for US
        List<QueueDto> usQueues = Arrays.asList(
            createQueueDto("US", "us-east", "https://sqs.us-east-1.amazonaws.com/123456789012/us-asset-queue-1", 1),
            createQueueDto("US", "us-east", "https://sqs.us-east-1.amazonaws.com/123456789012/us-asset-queue-2", 2),
            createQueueDto("US", "us-east", "https://sqs.us-east-1.amazonaws.com/123456789012/us-asset-queue-3", 3),
            createQueueDto("US", "us-east", "https://sqs.us-east-1.amazonaws.com/123456789012/us-asset-queue-4", 4)
        );
        countryToQueues.put("US", usQueues);
        
        // Create single queues for other countries
        String[] otherCountries = {"IN", "UK", "CA", "AU", "JP", "DE", "FR", "IT", "BR", "MX"};
        for (String country : otherCountries) {
            countryToQueues.put(country, Collections.singletonList(
                createQueueDto(country, "region", 
                     "https://sqs.region.amazonaws.com/123456789012/" + country.toLowerCase() + "-asset-queue-1", 1)
            ));
        }
        
        // Create flat list of all queues
        allQueues = countryToQueues.values().stream()
            .flatMap(List::stream)
            .collect(Collectors.toList());
    }
    
    /**
     * Helper method to create QueueDto with consistent structure
     */
    private QueueDto createQueueDto(String countryCode, String region, String assetQueueUrl, int queueNumber) {
        QueueDto dto = new QueueDto();
        dto.setId((long)(countryCode.hashCode() + queueNumber));
        dto.setCountryCode(countryCode);
        dto.setRegion(region);
        dto.setAssetQueueUrl(assetQueueUrl);
        dto.setLicenseUrl("https://sqs.region.amazonaws.com/123456789012/" + countryCode.toLowerCase() + "-license-queue");
        dto.setQueueNumber(queueNumber);
        dto.setActive(true);
        return dto;
    }
    
    /**
     * Generate realistic program ID for testing
     */
    private String generateProgramId(String countryCode) {
        String[] contentTypes = {"MO", "EP", "SE", "CL"};
        String[] titles = {"Friends", "Batman", "Titanic", "Matrix", "Inception", "GOT"};
        
        String contentType = contentTypes[random.nextInt(contentTypes.length)];
        String title = titles[random.nextInt(titles.length)];
        
        // Add season and episode numbers for episodes
        String suffix = "";
        if (contentType.equals("EP")) {
            int season = 1 + random.nextInt(5);
            int episode = 1 + random.nextInt(24);
            suffix = String.format("_S%02dE%02d", season, episode);
        }
        
        return String.format("%s_%s_%s%s", countryCode, contentType, title, suffix);
    }
    
    /**
     * Generate realistic provider ID for testing
     */
    private String generateProviderId() {
        String[] providers = {"NETFLIX", "AMAZONP", "HBO", "DISNEY", "HULU", "SHOWTIME"};
        return providers[random.nextInt(providers.length)];
    }

    /**
     * Test 1: Verify consistent routing - same asset should always route to same queue
     */
    @Test
    void testConsistentRouting() {
        // Get US queues
        List<QueueDto> usQueues = countryToQueues.get("US");
        ConsistentHashRouter router = new ConsistentHashRouter(usQueues);
        
        // Test with 1000 assets
        for (int i = 0; i < 1000; i++) {
            String programId = generateProgramId("US");
            String providerId = generateProviderId();
            
            String queue1 = router.getTargetQueue(programId, providerId, "US");
            String queue2 = router.getTargetQueue(programId, providerId, "US");
            
            assertEquals(queue1, queue2, "Same asset should always route to same queue");
        }
    }
    
    /**
     * Test 2: Verify basic distribution across queues
     */
    @Test
    void testDistribution() {
        // Get US queues
        List<QueueDto> usQueues = countryToQueues.get("US");
        ConsistentHashRouter router = new ConsistentHashRouter(usQueues);
        
        // Create test data
        int numAssets = 10000;
        Map<String, Integer> distribution = new HashMap<>();
        usQueues.forEach(q -> distribution.put(q.getAssetQueueUrl(), 0));
        
        // Route assets and track distribution
        for (int i = 0; i < numAssets; i++) {
            String programId = generateProgramId("US");
            String providerId = generateProviderId();
            
            String queue = router.getTargetQueue(programId, providerId, "US");
            distribution.merge(queue, 1, Integer::sum);
        }
        
        // Print distribution for debugging
        log.info("Queue distribution for {} assets:", numAssets);
        double idealPercentage = 100.0 / usQueues.size();
        
        distribution.forEach((queue, count) -> {
            double percentage = (count * 100.0) / numAssets;
            log.info("  {}: {} assets ({:.2f}%)", queue, count, percentage);
            
            // Verify reasonably balanced distribution (within 30% of ideal)
            double deviation = Math.abs(percentage - idealPercentage);
            assertTrue(deviation < idealPercentage * 0.3,
                "Distribution outside acceptable range: " + percentage + "% (ideal: " + idealPercentage + "%)");
        });
    }
    
    /**
     * Test 3: Verify similar assets (like show episodes) don't cluster on one queue
     */
    @Test
    void testSimilarAssetDistribution() {
        List<QueueDto> usQueues = countryToQueues.get("US");
        ConsistentHashRouter router = new ConsistentHashRouter(usQueues);
        
        // Create multiple episodes of the same show
        int numShows = 5;
        int episodesPerShow = 200;
        
        Map<String, Integer> distribution = new HashMap<>();
        usQueues.forEach(q -> distribution.put(q.getAssetQueueUrl(), 0));
        
        for (int show = 1; show <= numShows; show++) {
            String showName = "Show" + show;
            String providerId = "NETFLIX";
            
            for (int ep = 1; ep <= episodesPerShow; ep++) {
                String programId = String.format("US_EP_%s_S01E%02d", showName, ep);
                
                String queue = router.getTargetQueue(programId, providerId, "US");
                distribution.merge(queue, 1, Integer::sum);
            }
        }
        
        // Print distribution for debugging
        log.info("Similar assets distribution ({} episodes of {} shows):", 
                episodesPerShow, numShows);
        
        double idealPercentage = 100.0 / usQueues.size();
        distribution.forEach((queue, count) -> {
            double percentage = (count * 100.0) / (numShows * episodesPerShow);
            log.info("  {}: {} assets ({:.2f}%)", queue, count, percentage);
            
            // Allow 35% deviation for similar assets
            double deviation = Math.abs(percentage - idealPercentage);
            assertTrue(deviation < idealPercentage * 0.35,
                "Similar asset distribution outside acceptable range: " + percentage + "% (ideal: " + idealPercentage + "%)");
        });
    }
    
    /**
     * Test 4: Verify redistribution when adding a queue
     * This is the critical test that should show approximately 20% redistribution
     */
    @Test
    void testQueueAdditionRedistribution() {
        log.info("Running queue addition redistribution test...");
        
        // Create a controlled test with predictable asset IDs
        int numAssets = 10000;
        List<String> assetIds = new ArrayList<>();
        List<String> providerIds = new ArrayList<>();
        
        // Generate test asset IDs in a controlled way to avoid test artifacts
        for (int i = 0; i < numAssets; i++) {
            assetIds.add("US_ASSET_" + i);
            providerIds.add("PROVIDER_" + (i % 5));
        }
        
        log.info("Testing with {} assets", numAssets);
        
        // Get US queues and create router
        List<QueueDto> usQueues = new ArrayList<>(countryToQueues.get("US"));
        
        // STEP 1: Create the router and establish baseline routing
        ConsistentHashRouter router = new ConsistentHashRouter(usQueues);
        
        // STEP 2: Track the original routing
        Map<String, String> originalRouting = new HashMap<>();
        Map<String, Integer> originalDistribution = new HashMap<>();
        
        usQueues.forEach(q -> originalDistribution.put(q.getAssetQueueUrl(), 0));
        
        for (int i = 0; i < numAssets; i++) {
            String assetId = assetIds.get(i);
            String providerId = providerIds.get(i);
            
            String queue = router.getTargetQueue(assetId, providerId, "US");
            originalRouting.put(assetId, queue);
            originalDistribution.merge(queue, 1, Integer::sum);
        }
        
        // Print original distribution for debugging
        log.info("Original Distribution:");
        originalDistribution.forEach((queue, count) -> {
            double percentage = (count * 100.0) / numAssets;
            log.info("  {}: {} assets ({:.2f}%)", queue, count, percentage);
        });
        
        // STEP 3: Add a new queue - THIS IS THE KEY DIFFERENCE
        // Use the manual addQueue method to modify the existing router
        QueueDto newQueue = createQueueDto("US", "us-east", 
                "https://sqs.us-east-1.amazonaws.com/123456789012/us-asset-queue-5", 5);
        
        // Add method to add a single queue (if not already present in your router)
        router.addQueue(newQueue);
        
        // STEP 4: Check redistribution
        Map<String, Integer> newDistribution = new HashMap<>();
        usQueues.forEach(q -> newDistribution.put(q.getAssetQueueUrl(), 0));
        newDistribution.put(newQueue.getAssetQueueUrl(), 0);
        
        int changes = 0;
        
        for (int i = 0; i < numAssets; i++) {
            String assetId = assetIds.get(i);
            String providerId = providerIds.get(i);
            
            String newQueue = router.getTargetQueue(assetId, providerId, "US");
            newDistribution.merge(newQueue, 1, Integer::sum);
            
            if (!newQueue.equals(originalRouting.get(assetId))) {
                changes++;
            }
        }
        
        // Calculate and print redistribution percentage
        double redistributionPercentage = (changes * 100.0) / numAssets;
        log.info("Redistribution when adding 5th queue: {} assets changed queues ({:.2f}%)",
                changes, redistributionPercentage);
        
        // Print new distribution
        log.info("New Distribution:");
        newDistribution.forEach((queue, count) -> {
            double percentage = (count * 100.0) / numAssets;
            log.info("  {}: {} assets ({:.2f}%)", queue, count, percentage);
        });
        
        // Theoretical expectation: ~20% redistribution (1/5 of keys)
        // Allow range from 15-30% to account for natural variation
        assertTrue(redistributionPercentage >= 15.0 && redistributionPercentage <= 30.0,
            "Expected approximately 20% redistribution, got " + redistributionPercentage + "%");
    }
    
    /**
     * Test 5: Minimal test that focuses purely on the consistent hashing algorithm
     * This verifies at the lowest level that the algorithm behaves as expected
     */
    @Test
    void testMinimalConsistentHashing() {
        // This is a simplified test that eliminates any potential test artifacts
        
        // Set up a consistent hash ring
        TreeMap<Long, String> ring = new TreeMap<>();
        int virtualNodes = 500;
        
        // Add 4 queues
        for (int queueNum = 1; queueNum <= 4; queueNum++) {
            String queueUrl = "queue-" + queueNum;
            
            for (int v = 0; v < virtualNodes; v++) {
                String nodeKey = queueUrl + "-vnode-" + v;
                long hash = hashSimple(nodeKey);
                ring.put(hash, queueUrl);
            }
        }
        
        // Create asset IDs
        String[] assetIds = new String[10000];
        for (int i = 0; i < assetIds.length; i++) {
            assetIds[i] = "asset-" + i;
        }
        
        // Map assets to queues
        Map<String, String> originalMapping = new HashMap<>();
        for (String assetId : assetIds) {
            long hash = hashSimple(assetId);
            Map.Entry<Long, String> entry = ring.ceilingEntry(hash);
            if (entry == null) {
                entry = ring.firstEntry();
            }
            originalMapping.put(assetId, entry.getValue());
        }
        
        // Add a 5th queue
        String newQueueUrl = "queue-5";
        for (int v = 0; v < virtualNodes; v++) {
            String nodeKey = newQueueUrl + "-vnode-" + v;
            long hash = hashSimple(nodeKey);
            ring.put(hash, newQueueUrl);
        }
        
        // Check redistribution
        int changes = 0;
        for (String assetId : assetIds) {
            long hash = hashSimple(assetId);
            Map.Entry<Long, String> entry = ring.ceilingEntry(hash);
            if (entry == null) {
                entry = ring.firstEntry();
            }
            
            String newQueue = entry.getValue();
            if (!newQueue.equals(originalMapping.get(assetId))) {
                changes++;
            }
        }
        
        double percentage = (changes * 100.0) / assetIds.length;
        log.info("Minimal test redistribution: {:.2f}%", percentage);
        
        // Expect approximately 20% redistribution (1/5 of keys)
        assertTrue(percentage >= 15.0 && percentage <= 30.0,
            "Minimal test expected approximately 20% redistribution, got " + percentage + "%");
    }
    
    /**
     * Simple hash function for the minimal test
     */
    private long hashSimple(String key) {
        long hash = 0;
        for (int i = 0; i < key.length(); i++) {
            hash = 31 * hash + key.charAt(i);
        }
        return Math.abs(hash);
    }
    
    /**
     * Test 6: Performance benchmark for the router
     */
    @Test
    void testPerformance() {
        List<QueueDto> usQueues = countryToQueues.get("US");
        ConsistentHashRouter router = new ConsistentHashRouter(usQueues);
        
        int numAssets = 100000;
        List<String> programIds = new ArrayList<>(numAssets);
        List<String> providerIds = new ArrayList<>(numAssets);
        
        // Generate assets first to not measure generation time
        for (int i = 0; i < numAssets; i++) {
            programIds.add(generateProgramId("US"));
            providerIds.add(generateProviderId());
        }
        
        // Measure lookup time
        long startTime = System.nanoTime();
        
        for (int i = 0; i < numAssets; i++) {
            router.getTargetQueue(programIds.get(i), providerIds.get(i), "US");
        }
        
        long endTime = System.nanoTime();
        double totalTimeMs = (endTime - startTime) / 1_000_000.0;
        double avgLookupTimeMs = totalTimeMs / numAssets;
        
        log.info("Performance: {} lookups in {:.2f} ms ({:.5f} ms per lookup)",
                numAssets, totalTimeMs, avgLookupTimeMs);
        
        // Should be very fast (under 0.1ms per lookup)
        assertTrue(avgLookupTimeMs < 0.1,
            "Lookup performance not meeting target: " + avgLookupTimeMs + " ms/lookup");
    }
}