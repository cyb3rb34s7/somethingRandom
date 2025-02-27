// Diagnostic test code
List<QueueDto> queues = queueMapper.findActiveQueuesByCountry(countryCode);

// Log the queues for verification
log.info("Found {} queues for country {}", queues.size(), countryCode);
for (QueueDto q : queues) {
    log.info("Queue: id={}, number={}, url={}", q.getId(), q.getQueueNumber(), q.getAssetQueueUrl());
}

// Create router
log.info("Creating consistent hash router");
ConsistentHashRouter router = new ConsistentHashRouter(queues);

// Print ring distribution
router.printRingDistribution();

// Test with a few assets
String[] testAssets = {"TEST_ASSET_1", "TEST_ASSET_2", "TEST_ASSET_3", "TEST_ASSET_4", "TEST_ASSET_5"};
for (String asset : testAssets) {
    String targetQueue = router.getTargetQueue(asset, providerId, countryCode);
    log.info("Asset {} -> Queue {}", asset, targetQueue);
}