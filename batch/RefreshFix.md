Perfect. This is a design-level fix, not a refactor. I’ll give you surgical code changes, exact locations, before / after snippets, and the technical justification you can paste into a PR or design review.

I’ll structure this cleanly so it’s usable.


---

1️⃣ Problem Summary (1-liner for context)

Caffeine.refreshAfterWrite() performs cache refresh on a background thread which does not carry request-scoped authentication (user token + SSO token). Since IMS requires a real user token, async refresh causes intermittent authentication failures and silent cache staleness.


---

2️⃣ Design Decision (What we are changing)

Change cache refresh from async → synchronous
Use expireAfterWrite with single-flight refresh protection, ensuring IMS is always called with the current request’s user context.


---

3️⃣ Code Changes (exact & minimal)

📍 Location

UserNameCacheServiceImpl.java


---

🔴 BEFORE (current implementation)

Cache initialization

this.cache = Caffeine.newBuilder()
        .refreshAfterWrite(5, TimeUnit.MINUTES)
        .build(key -> fetchAllUsersFromIMSWithRetry());

Access method

@Override
public Map<String, String> getUserNameMap() {
    try {
        return cache.get(CACHE_KEY);
    } catch (Exception e) {
        log.error("Error fetching usernames from cache", e);
        return lastSuccessfulUserMap;
    }
}

Problem in this code

fetchAllUsersFromIMSWithRetry() may execute:

Outside HTTP request

Without auth context


IMS auth fails silently

Cache refresh never succeeds again



---

🟢 AFTER (proposed change)

1️⃣ Change cache configuration (remove async refresh)

this.cache = Caffeine.newBuilder()
        .expireAfterWrite(5, TimeUnit.MINUTES)
        .build();

✔ Removes background refresh
✔ Prevents context loss


---

2️⃣ Add refresh lock (class-level)

private final Object refreshLock = new Object();

📍 Add inside UserNameCacheServiceImpl


---

3️⃣ Modify getUserNameMap() (single-flight sync refresh)

@Override
public Map<String, String> getUserNameMap() {

    Map<String, String> cached = cache.getIfPresent(CACHE_KEY);
    if (cached != null && !cached.isEmpty()) {
        return cached;
    }

    synchronized (refreshLock) {

        // Double-check to avoid duplicate refresh
        cached = cache.getIfPresent(CACHE_KEY);
        if (cached != null && !cached.isEmpty()) {
            return cached;
        }

        try {
            Map<String, String> freshData = fetchAllUsersFromIMSWithRetry();
            cache.put(CACHE_KEY, freshData);
            lastSuccessfulUserMap = freshData;
            return freshData;
        } catch (Exception ex) {
            log.error("IMS fetch failed during username cache refresh", ex);
            return lastSuccessfulUserMap;
        }
    }
}


---

4️⃣ No changes required in:

getUserName(String userId)

IMS client

Security config

Controllers



---

4️⃣ Why this works (technical reasoning)

What we guarantee now

Concern	Guarantee

Auth availability	Always from active request
Thread context	Request thread
Cache consistency	Single refresh
Failure handling	Safe fallback
Token storage	❌ Not needed
Async bugs	❌ Eliminated



---

Key Principle Applied

> Any operation requiring request-scoped authentication must execute synchronously within the request lifecycle.




---

5️⃣ Why not the other approaches (explicit reasoning)

❌ Async refresh + token propagation

Requires capturing & storing user tokens

Token expiry handling

Security risks

High implementation complexity



---

❌ Service account / system token

Not supported by IMS

Security model violation



---

❌ Per-user cache

Memory explosion

Wrong abstraction

Cache invalidation complexity



---

❌ Scheduled background refresh

Still needs auth

No guarantee of valid user context

Operational complexity



---

✅ Why synchronous refresh was chosen

✔ Correctness over cleverness
✔ Least moving parts
✔ Predictable behavior
✔ No hidden state
✔ Easy to debug & reason about


---

6️⃣ Demo Workflow Scenario (step-by-step)

Scenario: Cache expired, multiple requests hit

Time = T + 5 mins
Cache entry expires

Request 1 (User A)

getUserNameMap()
↓
cache miss
↓
enters synchronized block
↓
IMS call with User A token
↓
cache populated
↓
returns data

Request 2 (User B) arrives simultaneously

getUserNameMap()
↓
waits on lock
↓
cache now present
↓
returns cached data

✔ Only one IMS call
✔ Correct auth
✔ No duplication


---

Failure scenario: IMS down

Cache expired
↓
IMS throws error
↓
Fallback to lastSuccessfulUserMap
↓
UI continues working

✔ No crash
✔ No empty UI
✔ Logged failure


---

7️⃣ Final PR-ready justification (copy-paste)

> We replaced async cache refresh with synchronous refresh because IMS authentication depends on request-scoped user tokens. Background refresh threads do not have access to this context, causing intermittent authentication failures and silent cache staleness. The new design ensures cache refresh always occurs within an authenticated request, while still preserving resilience via lastSuccessfulUserMap.




---

If you want next:

I can help you write unit tests for this

Or validate thread-safety

Or review lock contention risks

Or produce a sequence diagram


Just say the word.