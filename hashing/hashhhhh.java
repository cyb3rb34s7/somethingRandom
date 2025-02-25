// ====================== MODEL CLASSES ======================

// Asset.java - Main model for asset data
@Data
@Builder
public class Asset {
    private String id;
    private String countryCode;
    private String cpId;
    private String contentType;
    private String title;
    private Map<String, Object> metadata;
    
    public String toJson() throws JsonProcessingException {
        return new ObjectMapper().writeValueAsString(this);
    }
}

// CountryQueue.java - Model for queue configuration
@Data
@Builder
public class CountryQueue {
    private Long id;
    private String countryCode;
    private String queueUrl;
    private Integer queueNumber;
    private boolean isActive;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}

// QueueAddRequest.java - DTO for adding a new queue
@Data
public class QueueAddRequest {
    @NotBlank(message = "Country code is required")
    private String countryCode;
    
    @NotBlank(message = "Queue URL is required")
    private String queueUrl;
    
    @NotNull(message = "Queue number is required")
    private Integer queueNumber;
}

// ====================== MYBATIS MAPPER ======================

// CountryQueueMapper.java - MyBatis mapper interface
@Mapper
public interface CountryQueueMapper {
    List<CountryQueue> findActiveQueuesByCountry(String countryCode);
    List<String> findAllActiveCountryCodes();
    void insertQueue(CountryQueue queue);
    void updateQueueStatus(@Param("id") Long id, @Param("isActive") boolean isActive);
    CountryQueue findById(Long id);
}

// ====================== MYBATIS XML ======================

<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN" "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.samsung.ott.mapper.CountryQueueMapper">
    
    <resultMap id="queueResultMap" type="CountryQueue">
        <id property="id" column="id"/>
        <result property="countryCode" column="country_code"/>
        <result property="queueUrl" column="queue_url"/>
        <result property="queueNumber" column="queue_number"/>
        <result property="isActive" column="is_active"/>
        <result property="createdAt" column="created_at"/>
        <result property="updatedAt" column="updated_at"/>
    </resultMap>

    <select id="findActiveQueuesByCountry" resultMap="queueResultMap">
        SELECT * FROM country_queues 
        WHERE country_code = #{countryCode} 
        AND is_active = true
        ORDER BY queue_number
    </select>
    
    <select id="findAllActiveCountryCodes" resultType="String">
        SELECT DISTINCT country_code 
        FROM country_queues 
        WHERE is_active = true
    </select>

    <select id="findById" resultMap="queueResultMap">
        SELECT * FROM country_queues WHERE id = #{id}
    </select>
    
    <insert id="insertQueue" parameterType="CountryQueue">
        INSERT INTO country_queues (
            country_code, queue_url, queue_number, 
            is_active, created_at, updated_at
        ) VALUES (
            #{countryCode}, #{queueUrl}, #{queueNumber},
            true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
    </insert>
    
    <update id="updateQueueStatus">
        UPDATE country_queues 
        SET is_active = #{isActive},
            updated_at = CURRENT_TIMESTAMP
        WHERE id = #{id}
    </update>
</mapper>

// ====================== CONSISTENT HASH ROUTER ======================

// ConsistentHashRouter.java - Core routing logic
@Slf4j
public class ConsistentHashRouter {
    private final TreeMap<Long, String> ring = new TreeMap<>();
    private final int numberOfReplicas;
    private final MessageDigest md5;

    public ConsistentHashRouter(List<CountryQueue> queues) {
        this(queues, 100); // Default 100 virtual nodes per queue
    }

    public ConsistentHashRouter(List<CountryQueue> queues, int numberOfReplicas) {
        try {
            this.numberOfReplicas = numberOfReplicas;
            this.md5 = MessageDigest.getInstance("MD5");
            initializeRing(queues);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("MD5 algorithm not available", e);
        }
    }

    private void initializeRing(List<CountryQueue> queues) {
        for (CountryQueue queue : queues) {
            addQueueToRing(queue);
        }
        log.info("Initialized hash ring with {} physical queues", queues.size());
    }

    private void addQueueToRing(CountryQueue queue) {
        for (int i = 0; i < numberOfReplicas; i++) {
            long hash = generateHash(queue.getQueueUrl() + i);
            ring.put(hash, queue.getQueueUrl());
        }
    }

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

    public String getTargetQueue(Asset asset) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("No queues available in the hash ring");
        }

        // Use composite key for better distribution
        String hashKey = generateHashKey(asset);
        long hash = generateHash(hashKey);
        
        SortedMap<Long, String> tailMap = ring.tailMap(hash);
        Long nodeHash = tailMap.isEmpty() ? ring.firstKey() : tailMap.firstKey();
        return ring.get(nodeHash);
    }
    
    private String generateHashKey(Asset asset) {
        return String.format("%s_%s_%s_%s", 
            asset.getCountryCode(),
            asset.getCpId(),
            asset.getContentType(),
            asset.getId()
        );
    }
}

// ====================== SERVICE LAYER ======================

// Exceptions
@ResponseStatus(HttpStatus.NOT_FOUND)
public class CountryNotFoundException extends RuntimeException {
    public CountryNotFoundException(String countryCode) {
        super("No active queues found for country: " + countryCode);
    }
}

@ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
public class QueueRoutingException extends RuntimeException {
    public QueueRoutingException(String message) {
        super(message);
    }
}

// QueueRoutingService.java - Main service for queue routing
@Service
@Slf4j
public class QueueRoutingService {
    private final CountryQueueMapper queueMapper;
    private final AmazonSQS sqsClient;

    public QueueRoutingService(CountryQueueMapper queueMapper, AmazonSQS sqsClient) {
        this.queueMapper = queueMapper;
        this.sqsClient = sqsClient;
    }

    public void routeAsset(Asset asset) {
        try {
            String countryCode = validateAndGetCountryCode(asset);
            
            // Get active queues for country
            List<CountryQueue> queues = queueMapper.findActiveQueuesByCountry(countryCode);
            if (queues.isEmpty()) {
                throw new CountryNotFoundException(countryCode);
            }

            // Create router and get target queue
            ConsistentHashRouter router = new ConsistentHashRouter(queues);
            String targetQueue = router.getTargetQueue(asset);
            
            // Send to queue
            sendToQueue(asset, targetQueue);
            
        } catch (Exception e) {
            log.error("Error routing asset: {}", asset.getId(), e);
            throw new QueueRoutingException("Failed to route asset: " + e.getMessage());
        }
    }

    private String validateAndGetCountryCode(Asset asset) {
        String countryCode = asset.getCountryCode();
        if (StringUtils.isEmpty(countryCode)) {
            throw new IllegalArgumentException("Country code is required");
        }
        return countryCode.toUpperCase();
    }

    private void sendToQueue(Asset asset, String queueUrl) {
        try {
            SendMessageRequest request = new SendMessageRequest()
                .withQueueUrl(queueUrl)
                .withMessageBody(asset.toJson())
                .withMessageAttributes(createMessageAttributes(asset));

            sqsClient.sendMessage(request);
            log.info("Asset {} routed to queue {}", asset.getId(), queueUrl);
            
        } catch (Exception e) {
            log.error("Failed to send message to SQS: {}", queueUrl, e);
            throw new QueueRoutingException("SQS send failed: " + e.getMessage());
        }
    }

    private Map<String, MessageAttributeValue> createMessageAttributes(Asset asset) {
        Map<String, MessageAttributeValue> attributes = new HashMap<>();
        attributes.put("countryCode", new MessageAttributeValue()
            .withDataType("String")
            .withStringValue(asset.getCountryCode()));
        attributes.put("assetId", new MessageAttributeValue()
            .withDataType("String")
            .withStringValue(asset.getId()));
        attributes.put("contentType", new MessageAttributeValue()
            .withDataType("String")
            .withStringValue(asset.getContentType()));
        return attributes;
    }
}

// ====================== CONTROLLERS ======================

// AssetController.java - Main endpoint for asset processing
@RestController
@RequestMapping("/api/assets")
@Slf4j
public class AssetController {
    private final QueueRoutingService routingService;
    
    public AssetController(QueueRoutingService routingService) {
        this.routingService = routingService;
    }
    
    @PostMapping
    public ResponseEntity<String> processAsset(@RequestBody Asset asset) {
        try {
            routingService.routeAsset(asset);
            return ResponseEntity.ok("Asset routed successfully");
        } catch (CountryNotFoundException e) {
            log.warn(e.getMessage());
            return ResponseEntity.status(HttpStatus.NOT_FOUND).body(e.getMessage());
        } catch (QueueRoutingException e) {
            log.error("Routing error", e);
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(e.getMessage());
        } catch (Exception e) {
            log.error("Unexpected error processing asset", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                               .body("Error processing asset: " + e.getMessage());
        }
    }
}

// QueueManagementController.java - Admin endpoints for queue management
@RestController
@RequestMapping("/api/queues/admin")
@Slf4j
public class QueueManagementController {
    private final CountryQueueMapper queueMapper;

    public QueueManagementController(CountryQueueMapper queueMapper) {
        this.queueMapper = queueMapper;
    }

    @PostMapping("/add")
    public ResponseEntity<String> addQueue(@Valid @RequestBody QueueAddRequest request) {
        try {
            CountryQueue queue = CountryQueue.builder()
                .countryCode(request.getCountryCode().toUpperCase())
                .queueUrl(request.getQueueUrl())
                .queueNumber(request.getQueueNumber())
                .isActive(true)
                .build();
            
            queueMapper.insertQueue(queue);
            
            log.info("Added new queue: {} for country: {}", 
                    request.getQueueUrl(), request.getCountryCode());
            
            return ResponseEntity.ok("Queue added successfully");
            
        } catch (Exception e) {
            log.error("Failed to add queue", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Failed to add queue: " + e.getMessage());
        }
    }

    @PostMapping("/remove/{queueId}")
    public ResponseEntity<String> removeQueue(@PathVariable Long queueId) {
        try {
            CountryQueue queue = queueMapper.findById(queueId);
            if (queue == null) {
                return ResponseEntity.notFound().build();
            }
            
            queueMapper.updateQueueStatus(queueId, false);
            
            log.info("Removed queue: {} from country: {}", 
                    queueId, queue.getCountryCode());
            
            return ResponseEntity.ok("Queue removed successfully");
            
        } catch (Exception e) {
            log.error("Failed to remove queue", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Failed to remove queue: " + e.getMessage());
        }
    }
    
    @GetMapping("/status/{countryCode}")
    public ResponseEntity<Map<String, Object>> getQueueStatus(@PathVariable String countryCode) {
        List<CountryQueue> queues = queueMapper.findActiveQueuesByCountry(countryCode);
        Map<String, Object> status = new HashMap<>();
        status.put("countryCode", countryCode);
        status.put("activeQueues", queues.size());
        status.put("queues", queues);
        return ResponseEntity.ok(status);
    }
}

// ====================== AWS CONFIGURATION ======================

// SQSConfig.java - AWS SQS client configuration
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

// ====================== DATABASE MIGRATION ======================

-- Create the initial table
CREATE TABLE country_queues (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(2) NOT NULL,
    queue_url VARCHAR(255) NOT NULL,
    queue_number INT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add index for faster lookups
CREATE INDEX idx_country_queues_country_active 
ON country_queues(country_code, is_active);

-- Add unique constraint to prevent duplicates
CREATE UNIQUE INDEX unique_country_queue 
ON country_queues(country_code, queue_number) 
WHERE is_active = true;