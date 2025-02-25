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
    
    // Get the US queues
    List<QueueDto> usQueues = new ArrayList<>(countryQueues.get("US"));
    
    // Step 1: Create the FIRST consistent hash router instance
    ConsistentHashRouter router = new ConsistentHashRouter(usQueues);
    
    // Step 2: Record original routing
    Map<String, String> originalRouting = new HashMap<>();
    Map<String, Integer> originalDistribution = new HashMap<>();
    for (QueueDto queue : usQueues) {
        originalDistribution.put(queue.getAssetQueueUrl(), 0);
    }
    
    // Route assets and record distribution
    for (int i = 0; i < numAssets; i++) {
        String targetQueue = router.getTargetQueue(programIds.get(i), providerIds.get(i), "US");
        originalRouting.put(programIds.get(i), targetQueue);
        originalDistribution.merge(targetQueue, 1, Integer::sum);
    }
    
    // Print original distribution
    System.out.println("\nOriginal Distribution:");
    for (Map.Entry<String, Integer> entry : originalDistribution.entrySet()) {
        double percentage = (entry.getValue() * 100.0) / numAssets;
        System.out.printf("  %s: %d assets (%.2f%%)\n", 
            entry.getKey(), entry.getValue(), percentage);
    }
    
    // Step 3: Add a new queue to the SAME router instance
    // Create the new queue
    QueueDto newQueue = createQueueDto("US", "us-east", "https://sqs.../us-asset-queue-5", 5);
    
    // Add the method to ConsistentHashRouter if it doesn't exist
    // public void addQueue(QueueDto queue) {
    //     addQueueToRing(queue);
    // }
    
    // Add the queue to the EXISTING router
    router.addQueue(newQueue);
    
    // Step 4: Check redistribution with the SAME router instance
    Map<String, Integer> newDistribution = new HashMap<>();
    for (QueueDto queue : usQueues) {
        newDistribution.put(queue.getAssetQueueUrl(), 0);
    }
    newDistribution.put(newQueue.getAssetQueueUrl(), 0);
    
    int changes = 0;
    
    // Route assets again and count changes
    for (int i = 0; i < numAssets; i++) {
        String programId = programIds.get(i);
        String providerId = providerIds.get(i);
        
        String newTargetQueue = router.getTargetQueue(programId, providerId, "US");
        newDistribution.merge(newTargetQueue, 1, Integer::sum);
        
        if (!newTargetQueue.equals(originalRouting.get(programId))) {
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