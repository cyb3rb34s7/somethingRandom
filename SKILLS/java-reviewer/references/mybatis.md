# MyBatis & Database Access Review Rules

## SQL Injection via ${ } — BLOCKER
`${}` interpolates raw strings directly into SQL. Only `#{}` produces a parameterized query safe from SQL injection.

Flag every `${}` that is not used for a structurally necessary dynamic clause (e.g., dynamic table name or ORDER BY column). Those cases require explicit allowlist validation in Java before passing to MyBatis.

**Bad:**
```xml
SELECT * FROM users WHERE user_id = '${userId}'
<!-- Directly injectable -->
```

**Good:**
```xml
SELECT * FROM users WHERE user_id = #{userId}
```

**Acceptable with validation:**
```xml
ORDER BY ${columnName}  <!-- Only if columnName is validated against an allowlist in Java -->
```

---

## N+1 Query Problem — MAJOR
Flag any Java loop in a service that calls a MyBatis mapper inside the loop body. This means one DB query per iteration — a classic N+1.

**Bad:**
```java
for (String userId : userIds) {
    User user = userMapper.findById(userId); // N queries for N users
    process(user);
}
```

**Good — use IN clause:**
```xml
<!-- In mapper XML -->
<select id="findByIds" resultType="User">
    SELECT * FROM users
    WHERE user_id IN
    <foreach item="id" collection="ids" open="(" separator="," close=")">
        #{id}
    </foreach>
</select>
```
```java
// In service
List<User> users = userMapper.findByIds(userIds); // 1 query
```

**Alternative — use MyBatis `<collection>` for nested data:**
For parent-child relationships, use `<resultMap>` with `<collection>` tag to fetch in one join query instead of multiple selects.

---

## @Param Matching — MAJOR
Parameter names in the Java Mapper interface (annotated with `@Param`) must exactly match the names referenced in the XML tags.

**Bad:**
```java
// Java interface
List<Order> findByUser(@Param("userId") String id);
```
```xml
<!-- XML references wrong name -->
WHERE user_id = #{id}  <!-- Should be #{userId} -->
```

**Good:**
```java
List<Order> findByUser(@Param("userId") String userId);
```
```xml
WHERE user_id = #{userId}
```

---

## Result Mapping Completeness — MINOR
Ensure all columns returned by a query have a corresponding field in the result type. Unmapped columns are silently dropped by MyBatis — this is a common source of missing data bugs.
