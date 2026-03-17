# AWS DynamoDB SDK v2 Review Rules

## Enforce the Enhanced Client — BLOCKER if violated
If code maps DynamoDB results to POJOs, mandate `DynamoDbEnhancedClient` with `@DynamoDbBean` annotated POJOs.

**Bad — manual attribute mapping:**
```java
Map<String, AttributeValue> item = new HashMap<>();
item.put("userId", AttributeValue.builder().s(user.getId()).build());
item.put("score", AttributeValue.builder().n(String.valueOf(user.getScore())).build());
```

**Good — Enhanced Client:**
```java
@DynamoDbBean
public class User {
    private String userId;
    private int score;

    @DynamoDbPartitionKey
    public String getUserId() { return userId; }
    // other getters/setters
}

// Usage:
DynamoDbTable<User> table = enhancedClient.table("Users", TableSchema.fromBean(User.class));
table.putItem(user);
```

---

## No Client-Side Key Filtering — BLOCKER
Flag any Java loop that filters results by partition key or sort key after a `query()` or `scan()`. DynamoDB guarantees key matches — post-key-filtering in Java is always redundant and signals a misunderstanding.

**Bad:**
```java
List<Order> orders = orderTable.query(queryRequest).items().stream().collect(toList());
for (Order o : orders) {
    if (o.getUserId().equals(targetUserId)) { // DynamoDB already filtered this
        process(o);
    }
}
```

---

## getItem vs query — MAJOR
If both the exact Partition Key AND Sort Key are known at call time, mandate `getItem()`. Using `query()` in this case is wasteful and semantically incorrect.

**Bad:**
```java
// When both pk and sk values are known constants
QueryEnhancedRequest req = QueryEnhancedRequest.builder()
    .keyConditionExpression("pk = :pk AND sk = :sk")
    ...
```

**Good:**
```java
Key key = Key.builder()
    .partitionValue(pk)
    .sortValue(sk)
    .build();
table.getItem(key);
```

---

## Reserved Words Safety — MAJOR (low-level client only)
If using the low-level `DynamoDbClient` with expression strings directly, all attribute names must be aliased via `ExpressionAttributeNames`. Common reserved words: `name`, `status`, `type`, `count`, `value`, `key`, `order`, `partition`.

**Bad:**
```java
.filterExpression("status = :status") // ValidationException at runtime
```

**Good:**
```java
.filterExpression("#s = :status")
.expressionAttributeNames(Map.of("#s", "status"))
```
