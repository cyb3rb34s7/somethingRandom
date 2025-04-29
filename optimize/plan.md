# Streamlined Metadata History System Design

Based on your feedback and constraints, let's design a simpler yet highly efficient system for your metadata history tracking. I'll focus on practical optimizations with concrete metrics and examples.

## Core Design Principles

1. **Denormalized Storage**: Store all frequently accessed data directly in the history table
2. **Optimized Indexing**: Strategic indexing for common access patterns
3. **Efficient Pagination**: Using proper pagination techniques
4. **Application-level Caching**: Without relying on Redis

## Detailed Design Approach

### 1. Denormalized Table Structure

Rather than maintaining a separate copy table and joining during queries, let's denormalize the data:

```
CREATE TABLE metadata_history (
  id BIGSERIAL PRIMARY KEY,
  asset_id VARCHAR(50),
  program_id VARCHAR(50),
  cp_name VARCHAR(100),          -- Denormalized from copy table
  tech_integrator VARCHAR(50),    -- Denormalized from copy table
  title VARCHAR(255),             -- Denormalized from copy table
  media_type VARCHAR(50),         -- Denormalized from copy table
  updated_by VARCHAR(50),
  change_timestamp TIMESTAMP,
  changes JSONB                   -- Using native JSONB instead of string
);
```

**Performance Impact**:
- **Eliminates Join Cost**: Typical join operations add 20-30% overhead to query execution time
- **Specific Example**: A query returning 1000 history records with joins might take 500ms; without joins, the same query could run in 350-400ms

### 2. Keyset Pagination Explained

Keyset pagination (also called cursor-based pagination) uses a unique identifier from the last seen record to determine the next page, rather than using an offset:

**Current Approach (Offset Pagination)**:
```sql
SELECT * FROM metadata_history 
ORDER BY change_timestamp DESC 
LIMIT 1000 OFFSET 2000;
```

**Problem**: The database must scan and discard the first 2000 rows before returning the next 1000. As offset increases, performance degrades.

**Proposed Approach (Keyset Pagination)**:
```sql
SELECT * FROM metadata_history 
WHERE change_timestamp < :last_seen_timestamp 
  OR (change_timestamp = :last_seen_timestamp AND id < :last_seen_id)
ORDER BY change_timestamp DESC, id DESC
LIMIT 1000;
```

**Performance Impact**:
- **Small Dataset (10K records)**: Minimal difference (~10-20% improvement)
- **Medium Dataset (100K records)**: 2-3x faster for later pages
- **Large Dataset (1M+ records)**: 10-20x faster for later pages

**UI Implementation**:
- Store the `change_timestamp` and `id` of the last record in each page
- Use these values to fetch the next page
- Frontend pagination controls remain the same, but backend queries change

### 3. Strategic Indexing

```sql
-- Index for time-based filtering (most common case)
CREATE INDEX idx_metadata_timestamp ON metadata_history(change_timestamp DESC);

-- Composite index for keyset pagination
CREATE INDEX idx_metadata_timestamp_id ON metadata_history(change_timestamp DESC, id DESC);

-- Index for CP filtering (assuming common filter)
CREATE INDEX idx_metadata_cp ON metadata_history(cp_name);

-- Index for Tech Integrator filtering
CREATE INDEX idx_metadata_tech ON metadata_history(tech_integrator);

-- Index for Media Type filtering 
CREATE INDEX idx_metadata_media_type ON metadata_history(media_type);
```

**Performance Impact**:
- **Unindexed vs. Indexed Queries**: 10-100x performance difference
- **Example**: Filtering by date range unindexed: 2-3 seconds; indexed: 50-100ms

### 4. Table Partitioning by Time

```sql
CREATE TABLE metadata_history (
  -- columns as above
) PARTITION BY RANGE (change_timestamp);

-- Create monthly partitions
CREATE TABLE metadata_history_2025_04 PARTITION OF metadata_history
  FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
```

**Performance Impact**:
- **Query Performance**: 3-5x faster for time-ranged queries (e.g., "last 3 months")
- **Maintenance**: Easier to archive/drop old partitions
- **Example**: Query for 3-month history on 10M record table: 1-2 seconds without partitioning, 200-400ms with partitioning

### 5. Application-Level Caching with Caffeine

Since Redis is not an option, use Caffeine (in-memory caching library for Java):

```java
Cache<String, List<MetadataHistoryDTO>> historyCache = Caffeine.newBuilder()
    .maximumSize(1000)
    .expireAfterWrite(5, TimeUnit.MINUTES)
    .build();

// Cache key could be a hash of the filter parameters
String cacheKey = generateCacheKey(filterParams);
List<MetadataHistoryDTO> result = historyCache.get(cacheKey, k -> fetchFromDatabase(filterParams));
```

**Performance Impact**:
- **Cache Hit**: 50-100x faster than database query
- **Example**: Database query: 300ms; Cached response: 2-5ms
- **Memory Usage**: ~2-5MB for 1000 cached results (depending on size)

### 6. DynamoDB for Selective Caching (Optional)

If you want to leverage DynamoDB for shared caching:

```
Table: MetadataHistoryCache
- PK: cache_key (hash of filter parameters)
- SK: page_number  
- data: serialized result set
- ttl: expiration timestamp
```

**Performance Comparison**:
- **PostgreSQL Query**: 200-500ms
- **DynamoDB Retrieval**: 20-50ms
- **Cost**: Evaluate based on read/write units needed (~$0.25 per million reads)

### 7. JSONB Optimization 

Convert existing string JSON to native JSONB:

```sql
ALTER TABLE metadata_history 
ALTER COLUMN changes TYPE JSONB USING changes::jsonb;
```

**Performance Impact**:
- **Storage**: 10-20% less space compared to text JSON
- **Retrieval**: 30-40% faster when extracting values from JSONB
- **Example**: Query extracting specific fields from 1000 JSON records: 300ms as text, 180-200ms as JSONB

## Implementation Strategy

1. **First Phase** (Immediate gains with minimal changes):
   - Convert to JSONB
   - Add proper indexes
   - Implement application caching

2. **Second Phase** (Structural improvements):
   - Implement denormalized table structure
   - Set up keyset pagination
   - Add table partitioning

## Concrete Performance Metrics

For a system with 1 million history records, typical performance improvements:

| Operation | Current (Estimated) | Optimized | Improvement |
|-----------|---------------------|-----------|-------------|
| List view (first page) | 500-800ms | 100-200ms | 4-5x faster |
| List view (10th page) | 1-2s | 150-250ms | 6-8x faster |
| Filter by date range | 800ms-1s | 150-300ms | 3-5x faster |
| Filter by CP + date | 1-1.5s | 200-400ms | 3-5x faster |
| Expanded view (details) | 300-500ms | 50-150ms | 3-6x faster |

## Simplified Architecture Diagram

```
Client Request → Spring Controller → 
  → Check Application Cache (Caffeine) 
    → Hit: Return cached data
    → Miss: Query Database with optimized schema
      → Store in cache
      → Return to client
```

Would you like me to elaborate on any specific aspect of this design? Or shall we discuss implementation details for the highest-impact components first?