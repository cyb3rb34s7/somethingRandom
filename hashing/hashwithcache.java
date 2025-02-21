// CountryQueue.java - Entity class for queue configuration
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

// CountryQueueMapper.java - MyBatis mapper interface
@Mapper
public interface CountryQueueMapper {
    List<CountryQueue> findActiveQueuesByCountry(String countryCode);
    List<String> findAllActiveCountryCodes();
    void insertQueue(CountryQueue queue);
    void updateQueueStatus(@Param("id") Long id, @Param("isActive") boolean isActive);
    CountryQueue findById(Long id);
}

// CountryQueueMapper.xml - MyBatis XML configuration
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

// ConsistentHashRouter.java - Core routing logic implementation
@Slf4j
public class ConsistentHashRouter {
    // TreeMap maintains sorted order of hash values for efficient lookups
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

    // Initialize the hash ring with all queues and their virtual nodes
    private void initializeRing(List<CountryQueue> queues) {
        for (CountryQueue queue : queues) {
            addQueueToRing(queue);
        }
        log.info("Initialized hash ring with {} physical queues and {} virtual nodes", 
                 queues.size(), ring.size());
    }

    // Add a queue and its virtual nodes to the ring
    private void addQueueToRing(CountryQueue queue) {
        for (int i = 0; i < numberOfReplicas; i++) {
            long hash = generateHash(queue.getQueueUrl() + i);
            ring.put(hash, queue.getQueueUrl());
        }
    }

    // Generate consistent hash for a key
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

    // Get target queue for an asset
    public String getTargetQueue(String assetId) {
        if (ring.isEmpty()) {
            throw new IllegalStateException("No queues available in the hash ring");
        }

        long hash = generateHash(assetId);
        SortedMap<Long, String> tailMap = ring.tailMap(hash);
        Long nodeHash = tailMap.isEmpty() ? ring.firstKey() : tailMap.firstKey();
        return ring.get(nodeHash);
    }
}

// QueueRoutingService.java - Service for managing routing and cache
@Service
@Slf4j
public class QueueRoutingService {
    private final CountryQueueMapper queueMapper;
    private final AmazonSQS sqsClient;
    
    // Cache stores router instances for each country
    private final Cache<String, ConsistentHashRouter> countryRouters;
    
    @Value("${app.queue.cache.duration:300}") // 5 minutes default
    private int cacheDuration;

    public QueueRoutingService(CountryQueueMapper queueMapper, AmazonSQS sqsClient) {
        this.queueMapper = queueMapper;
        this.sqsClient = sqsClient;
        
        // Initialize cache with expiration
        this.countryRouters = Caffeine.newBuilder()
            .expireAfterWrite(Duration.ofSeconds(cacheDuration))
            .recordStats() // Enable statistics for monitoring
            .build();
    }

    // Main method to route an asset to appropriate queue
    public void routeAsset(Asset asset) {
        try {
            // Validate and get country code
            String countryCode = validateAndGetCountryCode(asset);
            
            // Get or create router for this country
            ConsistentHashRouter router = getOrCreateRouter(countryCode);
            
            // Get target queue and send message
            String targetQueue = router.getTargetQueue(asset.getId());
            sendToQueue(asset, targetQueue);
            
        } catch (Exception e) {
            log.error("Error routing asset: {}", asset.getId(), e);
            throw new QueueRoutingException("Failed to route asset: " + e.getMessage());
        }
    }

    // Get router from cache or create new one
    private ConsistentHashRouter getOrCreateRouter(String countryCode) {
        return countryRouters.get(countryCode, code -> {
            List<CountryQueue> queues = queueMapper.findActiveQueuesByCountry(code);
            if (queues.isEmpty()) {
                throw new CountryNotFoundException(code);
            }
            return new ConsistentHashRouter(queues);
        });
    }

    // Force refresh router for a country
    public void refreshRouter(String countryCode) {
        log.info("Refreshing router for country: {}", countryCode);
        countryRouters.invalidate(countryCode);
        // Trigger immediate rebuild
        getOrCreateRouter(countryCode);
    }

    // Refresh all routers (used when making system-wide changes)
    public void refreshAllRouters() {
        log.info("Refreshing all routers");
        countryRouters.invalidateAll();
        List<String> countryCodes = queueMapper.findAllActiveCountryCodes();
        for (String countryCode : countryCodes) {
            getOrCreateRouter(countryCode);
        }
    }
}

// QueueManagementController.java - REST endpoints for queue management
@RestController
@RequestMapping("/api/queues/admin")
@Slf4j
public class QueueManagementController {
    private final QueueRoutingService routingService;
    private final CountryQueueMapper queueMapper;

    // Add a new queue
    @PostMapping("/add")
    public ResponseEntity<String> addQueue(@RequestBody QueueAddRequest request) {
        try {
            // Validate request
            validateQueueRequest(request);
            
            // Create new queue
            CountryQueue queue = CountryQueue.builder()
                .countryCode(request.getCountryCode().toUpperCase())
                .queueUrl(request.getQueueUrl())
                .queueNumber(request.getQueueNumber())
                .isActive(true)
                .build();
            
            // Insert into DB
            queueMapper.insertQueue(queue);
            
            // Force router refresh for this country
            routingService.refreshRouter(queue.getCountryCode());
            
            log.info("Added new queue: {} for country: {}", 
                    request.getQueueUrl(), request.getCountryCode());
            
            return ResponseEntity.ok("Queue added successfully");
            
        } catch (Exception e) {
            log.error("Failed to add queue", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Failed to add queue: " + e.getMessage());
        }
    }

    // Remove a queue (soft delete)
    @PostMapping("/remove/{queueId}")
    public ResponseEntity<String> removeQueue(@PathVariable Long queueId) {
        try {
            // Get queue details
            CountryQueue queue = queueMapper.findById(queueId);
            if (queue == null) {
                return ResponseEntity.notFound().build();
            }
            
            // Soft delete by setting inactive
            queueMapper.updateQueueStatus(queueId, false);
            
            // Force router refresh for this country
            routingService.refreshRouter(queue.getCountryCode());
            
            log.info("Removed queue: {} from country: {}", 
                    queueId, queue.getCountryCode());
            
            return ResponseEntity.ok("Queue removed successfully");
            
        } catch (Exception e) {
            log.error("Failed to remove queue", e);
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body("Failed to remove queue: " + e.getMessage());
        }
    }

    // Get queue status and distribution
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