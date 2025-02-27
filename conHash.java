/**
 * Consistent Hash Router implementation that provides even distribution
 * even for cases with fixed providers and similar asset patterns.
 */
@Component
@Slf4j
public class ConsistentHashRouter {
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final int numberOfReplicas;
    private final MessageDigest md5;
    private List<QueueDto> allQueues;

    /**
     * Default constructor for Spring to use
     */
    public ConsistentHashRouter() {
        this.numberOfReplicas = 500;
        try {
            this.md5 = MessageDigest.getInstance("MD5");
            this.allQueues = new ArrayList<>();
        } catch (NoSuchAlgorithmException e) {
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
            this.allQueues = new ArrayList<>(queues);
            initializeRing(queues);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("MD5 algorithm not available", e);
        }
    }

    /**
     * Initialize the router with queues
     */
    public void initializeRing(List<QueueDto> queues) {
        ring.clear();
        allQueues.clear();
        allQueues.addAll(queues);
        
        for (QueueDto queue : queues) {
            addQueueToRing(queue);
        }
        log.info("Initialized hash ring with {} physical queues and {} virtual nodes", 
                 queues.size(), ring.size());
    }

    /**
     * Add a queue to the existing ring
     */
    public void addQueue(QueueDto queue) {
        allQueues.add(queue);
        addQueueToRing(queue);
        log.info("Added queue {} to existing hash ring", queue.getQueueNumber());
    }

    /**
     * Add a queue to the ring using explicit interleaving to ensure 
     * perfectly balanced distribution
     */
    private void addQueueToRing(QueueDto queue) {
        int queueNumber = queue.getQueueNumber();
        String countryCode = queue.getCountryCode();
        
        // Count total queues for this country
        int totalQueuesForCountry = 0;
        for (QueueDto q : allQueues) {
            if (q.getCountryCode().equals(countryCode)) {
                totalQueuesForCountry++;
            }
        }
        
        // Fallback if count is zero (shouldn't happen normally)
        if (totalQueuesForCountry == 0) {
            totalQueuesForCountry = 1;
        }
        
        for (int i = 0; i < numberOfReplicas; i++) {
            // This formula ensures nodes from different queues are perfectly interleaved
            // For example, with 2 queues:
            // Queue 1 gets positions at 0°, 180°, 360°, 540°...
            // Queue 2 gets positions at 90°, 270°, 450°, 630°...
            double angle = ((i * totalQueuesForCountry) + (queueNumber - 1)) * 
                          (360.0 / (numberOfReplicas * totalQueuesForCountry));
            
            // Convert to position on the hash ring (0° to 360° maps to 0 to Long.MAX_VALUE)
            long position = (long)((angle / 360.0) * Long.MAX_VALUE);
            
            // Add to ring
            ring.put(position, queue.getAssetQueueUrl());
        }
    }

    /**
     * Generate MD5 hash for a key
     */
    private long generateHash(String key) {
        md5.reset();
        md5.update(key.getBytes(StandardCharsets.UTF_8));
        byte[] digest = md5.digest();
        long hash = 0;
        for (int i = 0; i < 8; i++) {
            hash = (hash << 8) | (digest[i] & 0xFF);
        }
        return hash;
    }

    /**
     * Get the target queue for an asset using programId, providerId and countryCode
     */
    public String getTargetQueue(String programId, String providerId, String countryCode) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("No queues available in the hash ring");
        }

        // Generate composite key
        String hashKey = generateCompositeKey(programId, providerId, countryCode);
        long hash = generateHash(hashKey);
        
        // Find the next node on the ring
        SortedMap<Long, String> tailMap = ring.tailMap(hash);
        Long nodeHash = tailMap.isEmpty() ? ring.firstKey() : tailMap.firstKey();
        
        return ring.get(nodeHash);
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
        // Group by queue URL
        Map<String, Integer> queueCounts = new HashMap<>();
        
        for (String queueUrl : ring.values()) {
            queueCounts.merge(queueUrl, 1, Integer::sum);
        }
        
        log.info("Ring distribution:");
        for (Map.Entry<String, Integer> entry : queueCounts.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / ring.size();
            log.info("  {}: {} virtual nodes ({:.2f}%)", 
                    entry.getKey(), entry.getValue(), percentage);
        }
    }
}