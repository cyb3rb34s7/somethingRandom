/**
 * Robust Consistent Hash Router implementation that provides even distribution
 * even for cases with fixed providers and similar asset patterns.
 * Includes comprehensive error handling and null checks.
 */
@Component
@Slf4j
public class ConsistentHashRouter {
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final int numberOfReplicas;
    private final MessageDigest md5;
    private final List<QueueDto> allQueues = new ArrayList<>();

    /**
     * Default constructor for Spring to use
     */
    public ConsistentHashRouter() {
        this.numberOfReplicas = 500;
        try {
            this.md5 = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            log.error("Failed to initialize MD5 algorithm", e);
            throw new IllegalStateException("MD5 algorithm not available", e);
        }
    }

    /**
     * Constructor with queues for direct initialization or testing
     */
    public ConsistentHashRouter(List<QueueDto> queues) {
        this(queues, 500);
    }

    /**
     * Constructor with custom number of virtual nodes
     */
    public ConsistentHashRouter(List<QueueDto> queues, int numberOfReplicas) {
        try {
            this.numberOfReplicas = numberOfReplicas;
            this.md5 = MessageDigest.getInstance("MD5");
            
            // Initialize the ring with queues
            if (queues != null) {
                initializeRing(queues);
            } else {
                log.warn("Initializing ConsistentHashRouter with null queues list");
            }
        } catch (NoSuchAlgorithmException e) {
            log.error("Failed to initialize MD5 algorithm", e);
            throw new IllegalStateException("MD5 algorithm not available", e);
        } catch (Exception e) {
            log.error("Failed to initialize ConsistentHashRouter", e);
            throw new IllegalStateException("Failed to initialize router: " + e.getMessage(), e);
        }
    }

    /**
     * Initialize the router with queues
     */
    public void initializeRing(List<QueueDto> queues) {
        try {
            // Clear existing data
            ring.clear();
            allQueues.clear();
            
            // Null check
            if (queues == null) {
                log.warn("Null queues list provided to initializeRing");
                return;
            }
            
            // Add valid queues
            for (QueueDto queue : queues) {
                if (queue != null) {
                    allQueues.add(queue);
                }
            }
            
            // Calculate queue counts per country
            Map<String, Integer> queueCountsByCountry = calculateQueueCountsByCountry();
            
            // Add each queue to the ring
            for (QueueDto queue : allQueues) {
                try {
                    addQueueToRing(queue, queueCountsByCountry);
                } catch (Exception e) {
                    log.error("Error adding queue to ring: {}", queue, e);
                }
            }
            
            log.info("Initialized hash ring with {} physical queues and {} virtual nodes", 
                     allQueues.size(), ring.size());
        } catch (Exception e) {
            log.error("Failed to initialize ring", e);
            throw new IllegalStateException("Ring initialization failed: " + e.getMessage(), e);
        }
    }

    /**
     * Calculate the number of queues per country
     */
    private Map<String, Integer> calculateQueueCountsByCountry() {
        Map<String, Integer> counts = new HashMap<>();
        for (QueueDto queue : allQueues) {
            if (queue != null && queue.getCountryCode() != null) {
                counts.merge(queue.getCountryCode(), 1, Integer::sum);
            }
        }
        return counts;
    }

    /**
     * Add a queue to the existing ring
     */
    public void addQueue(QueueDto queue) {
        if (queue == null) {
            log.warn("Attempted to add null queue to router");
            return;
        }
        
        try {
            allQueues.add(queue);
            
            // Recalculate queue counts per country
            Map<String, Integer> queueCountsByCountry = calculateQueueCountsByCountry();
            
            // Add the queue to the ring
            addQueueToRing(queue, queueCountsByCountry);
            
            log.info("Added queue {} for country {} to existing hash ring", 
                    queue.getQueueNumber(), queue.getCountryCode());
        } catch (Exception e) {
            log.error("Failed to add queue to ring: {}", queue, e);
            throw new IllegalStateException("Failed to add queue: " + e.getMessage(), e);
        }
    }

    /**
     * Add a queue to the ring using explicit interleaving to ensure 
     * perfectly balanced distribution
     */
    private void addQueueToRing(QueueDto queue, Map<String, Integer> queueCountsByCountry) {
        // Validate input
        if (queue == null) {
            log.warn("Null queue provided to addQueueToRing");
            return;
        }
        
        int queueNumber = queue.getQueueNumber();
        String countryCode = queue.getCountryCode();
        String queueUrl = queue.getAssetQueueUrl();
        
        // Check for required fields
        if (countryCode == null || countryCode.isEmpty()) {
            log.warn("Queue has null or empty country code: {}", queue);
            countryCode = "UNKNOWN";
        }
        
        if (queueUrl == null || queueUrl.isEmpty()) {
            log.warn("Queue has null or empty URL: {}", queue);
            return;
        }
        
        // Get total queues for this country
        int totalQueuesForCountry = queueCountsByCountry.getOrDefault(countryCode, 1);
        
        // Use explicit interleaving approach for virtual nodes
        for (int i = 0; i < numberOfReplicas; i++) {
            try {
                // This formula ensures nodes from different queues are perfectly interleaved
                // For example, with 2 queues:
                // Queue 1 gets positions at 0°, 180°, 360°, 540°...
                // Queue 2 gets positions at 90°, 270°, 450°, 630°...
                double angle = ((i * totalQueuesForCountry) + (queueNumber - 1)) * 
                              (360.0 / (numberOfReplicas * totalQueuesForCountry));
                
                // Convert to position on the hash ring (0° to 360° maps to 0 to Long.MAX_VALUE)
                long position = (long)((angle / 360.0) * Long.MAX_VALUE);
                
                // Add to ring
                ring.put(position, queueUrl);
            } catch (Exception e) {
                log.error("Error adding virtual node for queue {}: {}", queueNumber, e.getMessage());
                // Continue with other nodes
            }
        }
    }

    /**
     * Generate MD5 hash for a key
     */
    private long generateHash(String key) {
        try {
            md5.reset();
            md5.update(key.getBytes(StandardCharsets.UTF_8));
            byte[] digest = md5.digest();
            long hash = 0;
            for (int i = 0; i < 8 && i < digest.length; i++) {
                hash = (hash << 8) | (digest[i] & 0xFF);
            }
            return Math.abs(hash); // Ensure positive value
        } catch (Exception e) {
            log.error("Error generating hash for key: {}", key, e);
            // Fallback to simple hash
            return Math.abs(key.hashCode());
        }
    }

    /**
     * Get the target queue for an asset using programId, providerId and countryCode
     */
    public String getTargetQueue(String programId, String providerId, String countryCode) {
        if (ring.isEmpty()) {
            log.error("Attempted to get target queue with empty ring");
            throw new IllegalStateException("No queues available in the hash ring");
        }

        try {
            // Null safety
            String safeCountryCode = countryCode != null ? countryCode : "";
            String safeProviderId = providerId != null ? providerId : "";
            String safeProgramId = programId != null ? programId : "";
            
            // Generate composite key
            String hashKey = generateCompositeKey(safeProgramId, safeProviderId, safeCountryCode);
            long hash = generateHash(hashKey);
            
            // Find the next node on the ring
            SortedMap<Long, String> tailMap = ring.tailMap(hash);
            Long nodeHash = tailMap.isEmpty() ? ring.firstKey() : tailMap.firstKey();
            
            String targetQueue = ring.get(nodeHash);
            
            // Debugging for low volume environments
            if (log.isDebugEnabled()) {
                log.debug("Asset routed: country={}, provider={}, program={}, queue={}", 
                        safeCountryCode, safeProviderId, safeProgramId, targetQueue);
            }
            
            return targetQueue;
        } catch (Exception e) {
            log.error("Error getting target queue: country={}, provider={}, program={}", 
                    countryCode, providerId, programId, e);
            
            // Fallback: if we have any queues for this country, use the first one
            for (QueueDto queue : allQueues) {
                if (queue != null && 
                    countryCode != null && 
                    countryCode.equals(queue.getCountryCode())) {
                    return queue.getAssetQueueUrl();
                }
            }
            
            // Ultimate fallback: use any queue
            if (!allQueues.isEmpty() && allQueues.get(0) != null) {
                return allQueues.get(0).getAssetQueueUrl();
            }
            
            throw new IllegalStateException("Failed to determine target queue", e);
        }
    }
    
    /**
     * Generate a composite key for an asset
     */
    private String generateCompositeKey(String programId, String providerId, String countryCode) {
        return String.format("%s_%s_%s", countryCode, providerId, programId);
    }

    /**
     * Print distribution metrics for debugging
     */
    public void printRingDistribution() {
        try {
            // Group by queue URL
            Map<String, Integer> queueCounts = new HashMap<>();
            
            for (String queueUrl : ring.values()) {
                queueCounts.merge(queueUrl, 1, Integer::sum);
            }
            
            log.info("Ring distribution:");
            for (Map.Entry<String, Integer> entry : queueCounts.entrySet()) {
                double percentage = (entry.getValue() * 100.0) / Math.max(1, ring.size());
                log.info("  {}: {} virtual nodes ({:.2f}%)", 
                        entry.getKey(), entry.getValue(), percentage);
            }
        } catch (Exception e) {
            log.error("Error printing ring distribution", e);
        }
    }
}