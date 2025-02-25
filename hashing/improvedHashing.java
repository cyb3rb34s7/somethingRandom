/**
 * Improved implementation of ConsistentHashRouter that addresses the high redistribution
 * issue when adding or removing queues.
 */
@Component
@Slf4j
public class ConsistentHashRouter {
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final int numberOfReplicas;
    private final MessageDigest md5;

    /**
     * Default constructor for Spring to use
     */
    public ConsistentHashRouter() {
        this.numberOfReplicas = 500; // Higher value for better distribution
        try {
            this.md5 = MessageDigest.getInstance("MD5");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("MD5 algorithm not available", e);
        }
    }

    /**
     * Constructor with queues for direct initialization or testing
     */
    public ConsistentHashRouter(List<QueueDto> queues) {
        this(queues, 500); // Higher default for better distribution
    }

    /**
     * Constructor with custom number of virtual nodes
     */
    public ConsistentHashRouter(List<QueueDto> queues, int numberOfReplicas) {
        try {
            this.numberOfReplicas = numberOfReplicas;
            this.md5 = MessageDigest.getInstance("MD5");
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
        for (QueueDto queue : queues) {
            addQueueToRing(queue);
        }
        log.info("Initialized hash ring with {} physical queues and {} virtual nodes", 
                 queues.size(), ring.size());
    }

    /**
     * Add a queue to the ring using improved virtual node generation
     * to ensure better distribution and minimal redistribution on changes
     */
    private void addQueueToRing(QueueDto queue) {
        String countryCode = queue.getCountryCode();
        int queueNumber = queue.getQueueNumber();
        
        for (int i = 0; i < numberOfReplicas; i++) {
            // Use a well-distributed pattern for virtual node keys
            // This is the key difference from the original implementation
            String virtualNodeKey = String.format("vnode:%s:%d:%d:%03d", 
                    countryCode, queueNumber, i % 1000, i);
            
            long hash = generateHash(virtualNodeKey);
            ring.put(hash, queue.getAssetQueueUrl());
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
     * Get the target queue for an asset using the programId, providerId and countryCode
     */
    public String getTargetQueue(String programId, String providerId, String countryCode) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("No queues available in the hash ring");
        }

        // Generate composite key using the same format
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
}