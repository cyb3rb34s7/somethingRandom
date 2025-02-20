// ConsistentHashRouter.java
package com.samsung.ott.router;

import com.amazonaws.services.sqs.AmazonSQS;
import com.amazonaws.services.sqs.model.SendMessageRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.SortedMap;
import java.util.TreeMap;

@Service
public class ConsistentHashRouter {
    private static final int NUM_QUEUES = 10;
    private static final int VIRTUAL_NODES_PER_QUEUE = 100;
    private static final String QUEUE_URL_PREFIX = "https://sqs.region.amazonaws.com/account/asset-queue-";

    private final TreeMap<Long, Integer> ring = new TreeMap<>();
    private final MessageDigest md5;
    
    @Autowired
    private AmazonSQS sqsClient;

    public ConsistentHashRouter() throws NoSuchAlgorithmException {
        this.md5 = MessageDigest.getInstance("MD5");
    }

    @PostConstruct
    public void initializeHashRing() {
        for (int queueId = 0; queueId < NUM_QUEUES; queueId++) {
            addQueueToRing(queueId);
        }
    }

    private void addQueueToRing(int queueId) {
        for (int vnode = 0; vnode < VIRTUAL_NODES_PER_QUEUE; vnode++) {
            String virtualNodeId = "queue" + queueId + "-vnode" + vnode;
            long hash = generateHash(virtualNodeId);
            ring.put(hash, queueId);
        }
    }

    private long generateHash(String key) {
        byte[] digest = md5.digest(key.getBytes(StandardCharsets.UTF_8));
        long hash = 0;
        for (int i = 0; i < 8; i++) {
            hash = (hash << 8) | (digest[i] & 0xFF);
        }
        return hash;
    }

    public int getQueueForAsset(String assetId) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("Hash ring is not initialized");
        }

        long hash = generateHash(assetId);
        SortedMap<Long, Integer> tailMap = ring.tailMap(hash);
        Long nodeHash = tailMap.isEmpty() ? ring.firstKey() : tailMap.firstKey();
        return ring.get(nodeHash);
    }

    public void routeAsset(Asset asset) {
        int targetQueue = getQueueForAsset(asset.getId());
        String queueUrl = QUEUE_URL_PREFIX + targetQueue;

        SendMessageRequest sendMessageRequest = new SendMessageRequest()
            .withQueueUrl(queueUrl)
            .withMessageBody(asset.toJson())
            .addMessageAttributesEntry("RoutingHash", 
                new MessageAttributeValue()
                    .withDataType("Number")
                    .withStringValue(String.valueOf(generateHash(asset.getId())))
            );

        sqsClient.sendMessage(sendMessageRequest);
    }
}

// Asset.java
@Data
@Builder
public class Asset {
    private String id;
    private String contentType;
    private String cpId;
    private String country;
    // other fields...

    public String toJson() {
        return new ObjectMapper().writeValueAsString(this);
    }
}

// AssetController.java
@RestController
@RequestMapping("/api/assets")
public class AssetController {
    
    @Autowired
    private ConsistentHashRouter router;
    
    @PostMapping
    public ResponseEntity<String> processAsset(@RequestBody Asset asset) {
        try {
            router.routeAsset(asset);
            return ResponseEntity.ok("Asset routed successfully");
        } catch (Exception e) {
            log.error("Error routing asset", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                               .body("Error processing asset");
        }
    }
}

// Configuration
@Configuration
public class SQSConfig {
    
    @Value("${aws.access.key.id}")
    private String accessKey;
    
    @Value("${aws.secret.access.key}")
    private String secretKey;
    
    @Value("${aws.region}")
    private String region;
    
    @Bean
    public AmazonSQS sqsClient() {
        return AmazonSQSClientBuilder.standard()
            .withCredentials(new AWSStaticCredentialsProvider(
                new BasicAWSCredentials(accessKey, secretKey)))
            .withRegion(region)
            .build();
    }
}

// For testing distribution
@Component
public class DistributionValidator {
    
    @Autowired
    private ConsistentHashRouter router;
    
    public Map<Integer, Integer> validateDistribution(int numAssets) {
        Map<Integer, Integer> distribution = new HashMap<>();
        for (int i = 0; i < numAssets; i++) {
            String assetId = "test-asset-" + i;
            int queueNumber = router.getQueueForAsset(assetId);
            distribution.merge(queueNumber, 1, Integer::sum);
        }
        
        // Calculate statistics
        double mean = numAssets / (double) NUM_QUEUES;
        double variance = distribution.values().stream()
            .mapToDouble(count -> Math.pow(count - mean, 2))
            .average()
            .orElse(0.0);
        double stdDev = Math.sqrt(variance);
        
        log.info("Distribution: " + distribution);
        log.info("Standard Deviation: " + stdDev);
        log.info("Mean per queue: " + mean);
        
        return distribution;
    }
}