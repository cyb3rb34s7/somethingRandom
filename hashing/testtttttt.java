@Test
void testMinimalRedistribution() {
    // Setup with minimal implementation
    TreeMap<Long, String> ring = new TreeMap<>();
    int virtualNodes = 500;
    
    // Add 4 queues with virtual nodes
    for (int q = 1; q <= 4; q++) {
        String queueUrl = "queue-" + q;
        for (int v = 0; v < virtualNodes; v++) {
            // Use a VERY simple virtual node key 
            String nodeKey = queueUrl + "-" + v;
            long hash = hashFunction(nodeKey);
            ring.put(hash, queueUrl);
        }
    }
    
    // Generate 1000 asset IDs
    String[] assetIds = new String[1000];
    for (int i = 0; i < 1000; i++) {
        assetIds[i] = "asset-" + i;
    }
    
    // Map assets to queues
    Map<String, String> originalMapping = new HashMap<>();
    for (String assetId : assetIds) {
        long hash = hashFunction(assetId);
        Map.Entry<Long, String> entry = ring.ceilingEntry(hash);
        if (entry == null) {
            entry = ring.firstEntry();
        }
        originalMapping.put(assetId, entry.getValue());
    }
    
    // Add a 5th queue
    String newQueueUrl = "queue-5";
    for (int v = 0; v < virtualNodes; v++) {
        String nodeKey = newQueueUrl + "-" + v;
        long hash = hashFunction(nodeKey);
        ring.put(hash, newQueueUrl);
    }
    
    // Check redistribution
    int changes = 0;
    for (String assetId : assetIds) {
        long hash = hashFunction(assetId);
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
    System.out.println("Minimal test redistribution: " + percentage + "%");
}

private long hashFunction(String key) {
    try {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] digest = md.digest(key.getBytes(StandardCharsets.UTF_8));
        long hash = 0;
        for (int i = 0; i < 8; i++) {
            hash = (hash << 8) | (digest[i] & 0xFF);
        }
        return hash;
    } catch (NoSuchAlgorithmException e) {
        throw new RuntimeException(e);
    }
}