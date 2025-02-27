/**
 * Optimized Consistent Hash Router implementation with excellent distribution properties,
 * even when using fixed provider IDs and country codes.
 */
@Component
@Slf4j
public class ConsistentHashRouter {
    private final TreeMap<Integer, String> ring = new TreeMap<>();
    private final int virtualNodesPerQueue;
    
    /**
     * Default constructor for Spring
     */
    public ConsistentHashRouter() {
        this.virtualNodesPerQueue = 1024;
    }
    
    /**
     * Constructor with queues for direct initialization
     */
    public ConsistentHashRouter(List<QueueDto> queues) {
        this(queues, 1024);
    }
    
    /**
     * Constructor with custom virtual node count
     */
    public ConsistentHashRouter(List<QueueDto> queues, int virtualNodesPerQueue) {
        this.virtualNodesPerQueue = virtualNodesPerQueue;
        initializeRing(queues);
    }
    
    /**
     * Initialize the hash ring with queues
     */
    public void initializeRing(List<QueueDto> queues) {
        if (queues == null || queues.isEmpty()) {
            log.warn("Initializing router with empty queues");
            return;
        }
        
        ring.clear();
        
        for (QueueDto queue : queues) {
            if (queue == null || queue.getAssetQueueUrl() == null) {
                continue;
            }
            
            String queueUrl = queue.getAssetQueueUrl();
            
            for (int i = 0; i < virtualNodesPerQueue; i++) {
                // Create virtual node key
                String nodeKey = queueUrl + "#" + i;
                int hash = fnvHash(nodeKey);
                ring.put(hash, queueUrl);
            }
        }
        
        log.info("Initialized hash ring with {} queues, {} virtual nodes", 
                queues.size(), ring.size());
    }
    
    /**
     * Add a single queue to the ring
     */
    public void addQueue(QueueDto queue) {
        if (queue == null || queue.getAssetQueueUrl() == null) {
            log.warn("Attempted to add null queue");
            return;
        }
        
        String queueUrl = queue.getAssetQueueUrl();
        
        for (int i = 0; i < virtualNodesPerQueue; i++) {
            String nodeKey = queueUrl + "#" + i;
            int hash = fnvHash(nodeKey);
            ring.put(hash, queueUrl);
        }
        
        log.info("Added queue {} to ring with {} virtual nodes", 
                queue.getQueueNumber(), virtualNodesPerQueue);
    }
    
    /**
     * Get the target queue for an asset
     */
    public String getTargetQueue(String programId, String providerId, String countryCode) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("No queues available in the hash ring");
        }
        
        // Safe handling of inputs
        String safeProgram = programId != null ? programId : "";
        String safeProvider = providerId != null ? providerId : "";
        String safeCountry = countryCode != null ? countryCode : "";
        
        // Create composite key
        String key = safeCountry + "_" + safeProvider + "_" + safeProgram;
        int hash = fnvHash(key);
        
        // Find the next node on the ring
        Map.Entry<Integer, String> entry = ring.ceilingEntry(hash);
        if (entry == null) {
            entry = ring.firstEntry();
        }
        
        return entry.getValue();
    }
    
    /**
     * FNV-1a hash function - provides excellent distribution properties
     */
    private int fnvHash(String key) {
        final int FNV_PRIME = 0x01000193;
        int hash = 0x811c9dc5;
        
        for (int i = 0; i < key.length(); i++) {
            hash ^= key.charAt(i);
            hash *= FNV_PRIME;
        }
        
        return hash;
    }
    
    /**
     * Print distribution metrics for debugging
     */
    public void printRingDistribution() {
        if (ring.isEmpty()) {
            log.info("Ring is empty");
            return;
        }
        
        Map<String, Integer> queueCounts = new HashMap<>();
        for (String queueUrl : ring.values()) {
            queueCounts.merge(queueUrl, 1, Integer::sum);
        }
        
        log.info("Ring distribution (virtual nodes per queue):");
        for (Map.Entry<String, Integer> entry : queueCounts.entrySet()) {
            double percentage = (entry.getValue() * 100.0) / ring.size();
            log.info("  {}: {} nodes ({:.2f}%)", 
                    entry.getKey(), entry.getValue(), percentage);
        }
    }
}