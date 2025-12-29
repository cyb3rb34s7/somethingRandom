This is the **Final Execution Plan** for your Admin Portal User Name Resolution.

Based on your requirement (checking only when UI needs it, ~1000 users, avoiding over-engineering), the **Lazy-Load Synchronized Approach** is the perfect fit.

### 1. High-Level Architecture

We will implement a `UserNameService` inside your Admin Backend. This service acts as a "Gatekeeper."

* **Trigger:** It is only called when the Admin Service constructs the response for **History** or **Profile** pages.
* **Mechanism:** "Check-Then-Act." It checks if its internal cache is fresh (updated < 5 mins ago).
* **If Fresh:** Returns name immediately from RAM.
* **If Stale:** Uses the *current user's token* to fetch the 1,000 users from IMS, updates the cache, then returns.



---

### 2. Handling the Multi-Threaded Problem

You asked for reasoning on `synchronized` vs. other options.

#### **Option A: The `synchronized` Keyword (Recommended)**

This is the standard Java way to ensure only one thread executes a block of code at a time.

* **How it works:** If User A triggers a refresh, User B, C, and D (who clicked "History" at the same exact second) will **pause** and wait at the method entry until User A finishes.
* **Is it enough?**
* **Yes.** Processing 1,000 users is trivial.
* **Network Call:** Fetching 1,000 users JSON takes ~200-500ms.
* **Data Processing:** Converting list to map takes < 5ms.
* **Total Block Time:** ~0.5 seconds.
* **Impact:** Once every 5 minutes, a few concurrent users might see a page load take 0.5s longer. This is completely acceptable for an internal Admin Portal.



#### **Option B: `ReentrantLock` with `tryLock()` (The "Non-Blocking" Alternative)**

If you are worried about users "waiting," you use this.

* **How it works:** User A grabs the lock and updates. User B tries to grab the lock, fails, and **instead of waiting**, User B just uses the *old stale data* immediately.
* **Why skip it?** It adds code complexity (handling locks in `finally` blocks) and implies you are okay with showing data that is 5 minutes + a few seconds old. Given `synchronized` is simpler and safer, Option A is better here.

---

### 3. Data Handling Strategy (The "1000 Users")

You have 1,000 users. In computer science terms, this is **tiny**.

* **Memory Footprint:**
* 1 User Entry ≈ 150 Bytes (UUID + Name + Overhead).
* 1,000 Users ≈ **150 KB**.
* Even if you scale to 50,000 users, it is only **7.5 MB**.


* **Processing:**
* Iterating a list of 1,000 items in Java takes microseconds. You do not need complex algorithms. A simple loop is fine.



---

### 4. Implementation Plan (The Code)

Here is the robust, copy-paste-ready logic.

#### **Step A: The Cache Service**

This service holds the map and handles the 5-minute logic.

```java
@Service
@Slf4j
public class UserNameService {

    // Ideally, inject your Repositories and Feign Clients here
    private final UserRepository userRepository; // To get GUID <-> UUID mapping
    private final ImsClient imsClient;           // To call IMS
    
    // The Cache: Maps UUID (System ID) -> "John Doe"
    private Map<String, String> nameCache = new ConcurrentHashMap<>();
    
    private volatile long lastRefillTime = 0;
    private static final long REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 Minutes

    /**
     * PRIMARY METHOD: Called by your History/Profile DTO Mappers.
     * Usage: dto.setUpdatedByName(userNameService.getUserName(entity.getUpdatedBy()));
     */
    public String getUserName(String userId) {
        if (userId == null) return "Unknown";

        // 1. Check freshness (Non-blocking check first for performance)
        if (isCacheStale()) {
            refreshCacheSynchronized();
        }

        // 2. Return from cache, or fallback to userId if not found
        return nameCache.getOrDefault(userId, userId);
    }

    private boolean isCacheStale() {
        return System.currentTimeMillis() - lastRefillTime > REFRESH_INTERVAL_MS;
    }

    /**
     * The Guarded Refresh. Only ONE thread enters here.
     * Others wait, then benefit from the fresh data.
     */
    private synchronized void refreshCacheSynchronized() {
        // Double-check: Someone might have finished refreshing while we waited
        if (!isCacheStale()) {
            return;
        }

        try {
            // 1. Get Token from the User who triggered this request
            String authToken = SecurityUtils.getCurrentUserAuthToken();
            if (authToken == null) return; // Cannot refresh without token

            log.info("Refeshing User Name Cache...");

            // 2. Fetch IMS Data (The "1000 Users")
            // Returns: [{guid: "abc", givenName: "John", familyName: "Doe"}, ...]
            List<ImsUserDto> imsUsers = imsClient.fetchAllUsers(authToken);

            // 3. Fetch Local DB Mapping
            // Returns: { "abc": "uuid-123", ... }
            Map<String, String> guidToUuidMap = userRepository.findAllActiveGuidUuidMappings();

            // 4. The "Join" Logic (In-Memory)
            Map<String, String> newCache = new HashMap<>();
            
            for (ImsUserDto imsUser : imsUsers) {
                String uuid = guidToUuidMap.get(imsUser.getGuid());
                
                // Only cache users who exist in OUR system
                if (uuid != null) {
                    String fullName = imsUser.getGivenName() + " " + imsUser.getFamilyName();
                    newCache.put(uuid, fullName);
                }
            }

            // 5. Atomic Switch
            // replacing the reference is thread-safe
            this.nameCache = new ConcurrentHashMap<>(newCache);
            this.lastRefillTime = System.currentTimeMillis();
            
            log.info("Cache Refreshed. Loaded {} users.", newCache.size());

        } catch (Exception e) {
            log.error("Failed to refresh user cache from IMS. Serving stale data.", e);
            // We do NOT update lastRefillTime, so next request will retry.
        }
    }
}

```

#### **Step B: Integration into History Service**

When your Admin Service fetches history, it likely maps the database entities to DTOs for the UI. You inject the service there.

```java
@Service
public class HistoryService {

    @Autowired
    private UserNameService userNameService;

    public List<HistoryRecordDto> getHistory(int page, int size) {
        // 1. Get raw entities (with UUIDs)
        List<HistoryEntity> entities = historyRepo.findAll(PageRequest.of(page, size));

        // 2. Convert to DTOs and Resolve Names
        return entities.stream().map(entity -> {
            HistoryRecordDto dto = new HistoryRecordDto();
            dto.setAction(entity.getAction());
            dto.setTimestamp(entity.getTimestamp());
            
            // --- THE RESOLUTION HAPPENS HERE ---
            // Even if we loop 100 times, the cache refresh only happens ONCE (if needed).
            String name = userNameService.getUserName(entity.getUpdatedBy());
            dto.setUpdatedByName(name);
            
            return dto;
        }).collect(Collectors.toList());
    }
}

```

### 5. Summary of Why This Works

1. **Simple:** No background threads, no system users, no complex locking libraries.
2. **Efficient:** The `synchronized` block only runs once every 5 minutes. For 99.9% of requests, it's a simple `Map.get()` (nanoseconds).
3. **Safe:** If IMS fails, the old `nameCache` stays in memory, so the UI never breaks.
4. **Scalable:** 1,000 users is nothing for memory. It will work fine even if your company grows to 20,000 users.
