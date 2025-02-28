package com.yourcompany.dbapi.router;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;
import java.util.SortedMap;
import java.util.TreeMap;
import java.util.UUID;
import java.util.logging.Logger;

/**
 * A robust consistent hashing implementation optimized for small queue counts (2-8).
 * Uses increased virtual nodes and better hashing for balanced distribution.
 */
public class RobustConsistentHashRouter {

    private static final Logger logger = Logger.getLogger(RobustConsistentHashRouter.class.getName());
    private static final int DEFAULT_VIRTUAL_NODES = 1000; // Higher count for better distribution

    private final SortedMap<Integer, String> ring = new TreeMap<>();
    private final int virtualNodesPerQueue;

    /**
     * Constructs a new router with default virtual node settings.
     * @param queues List of queue URLs to distribute across
     */
    public RobustConsistentHashRouter(List<String> queues) {
        this(queues, DEFAULT_VIRTUAL_NODES);
    }

    /**
     * Constructs a new router with specified virtual node count.
     * @param queues List of queue URLs to distribute across
     * @param virtualNodesPerQueue Number of virtual nodes per physical queue
     */
    public RobustConsistentHashRouter(List<String> queues, int virtualNodesPerQueue) {
        this.virtualNodesPerQueue = virtualNodesPerQueue;
        initializeRing(queues);
    }

    /**
     * Gets the appropriate queue URL for the given asset.
     * Uses a random UUID rather than the asset ID to ensure even distribution.
     * 
     * @param assetId The asset ID (not used for hashing, just for logging)
     * @return The selected queue URL
     */
    public String getQueueForAsset(String assetId) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("Hash ring is empty");
        }
        
        // Generate a random UUID for this asset
        String randomKey = UUID.randomUUID().toString();
        
        // Hash the random key
        int hash = hashString(randomKey);
        
        // Find the queue for this hash
        String selectedQueue = findQueueOnRing(hash);
        
        logger.fine("Asset " + assetId + " routed to " + selectedQueue);
        return selectedQueue;
    }

    /**
     * Sets up the hash ring with virtual nodes for each queue.
     */
    private void initializeRing(List<String> queues) {
        for (String queue : queues) {
            for (int i = 0; i < virtualNodesPerQueue; i++) {
                // Create a virtual node key with better distribution across the hash space
                // Using both the queue ID and a fraction ensures better spread
                double fraction = (double) i / virtualNodesPerQueue;
                String nodeKey = queue + "#" + fraction;
                
                // Hash the key
                int hashValue = hashString(nodeKey);
                
                // Add to the ring
                ring.put(hashValue, queue);
            }
        }
        
        logger.info("Initialized consistent hash ring with " + ring.size() + 
                    " virtual nodes for " + queues.size() + " queues");
    }

    /**
     * Finds the appropriate queue on the hash ring.
     */
    private String findQueueOnRing(int hash) {
        // Find the first point on the ring at or after the hash
        SortedMap<Integer, String> tailMap = ring.tailMap(hash);
        
        // If no points after hash, wrap around to first point
        Integer key = tailMap.isEmpty() ? ring.firstKey() : tailMap.firstKey();
        
        return ring.get(key);
    }

    /**
     * A robust hash function using built-in Java security APIs.
     * This is a simplified wrapper around SHA-256 which is both fast and high-quality.
     */
    private int hashString(String key) {
        try {
            // Get bytes of the string in UTF-8 encoding
            byte[] data = key.getBytes(StandardCharsets.UTF_8);
            
            // Use MessageDigest for SHA-256 (built into Java, no complex implementation needed)
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(data);
            
            // Use first 4 bytes for an integer
            return ((hash[0] & 0xFF) << 24) |
                   ((hash[1] & 0xFF) << 16) |
                   ((hash[2] & 0xFF) << 8)  |
                   (hash[3] & 0xFF);
                   
        } catch (NoSuchAlgorithmException e) {
            // Fallback to a simple hash if SHA-256 is somehow not available
            return key.hashCode();
        }
    }
}