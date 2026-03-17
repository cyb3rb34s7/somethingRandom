# Java & Spring Boot Review Rules

## Fail-Fast / Guard Clauses
Invert `if (obj != null)` blocks at method entry. Exit early on null/invalid state to reduce nesting depth.

**Bad:**
```java
public void process(Data data) {
    if (data != null) {
        if (data.getItems() != null) {
            // 40 lines of logic
        }
    }
}
```

**Good:**
```java
public void process(Data data) {
    if (data == null || data.getItems() == null) return;
    // logic here
}
```

---

## Unused Dependencies
Flag any constructor-injected or `@Autowired` bean that is never referenced in the class body.

---

## Stream Bugs
- `.stream().toString()` prints a memory address, not data. Always apply a terminal operation.
- Flag any stream missing a terminal operation like `.collect()`, `.findFirst()`, `.count()`, etc.

**Bad:**
```java
String result = list.stream().filter(x -> x.isActive()).toString(); // BUG — memory ref
```

**Good:**
```java
List<Item> result = list.stream().filter(Item::isActive).collect(Collectors.toList());
```

---

## DRY — Don't Repeat Yourself
Flag methods with identical or near-identical logic. Suggest extraction to a shared private method or utility class.

---

## Exception Handling

### Zero Tolerance for Silent Failures — BLOCKER
Any `catch` block that only logs without re-throwing or returning a domain failure object is a **blocker**.

**Bad:**
```java
try {
    processOrder(order);
} catch (Exception e) {
    log.error("Failed", e); // caller has no idea this failed
}
```

**Good:**
```java
try {
    processOrder(order);
} catch (Exception e) {
    log.error("Order processing failed for orderId={}", order.getId(), e);
    throw new OrderProcessingException("Failed to process order", e);
}
```

### Preserve Stack Traces
When wrapping in a custom exception, always pass the original as the cause.

**Bad:** `throw new ServiceException("Failed");`
**Good:** `throw new ServiceException("Failed to process request", e);`

### Redundant Catch
Flag any catch block that catches an exception only to re-throw the exact same exception type with no added context.

---

## SLF4J Logging
Flag string concatenation in log calls. Enforce parameterized logging.

**Bad:** `log.info("Processing user: " + userId);`
**Good:** `log.info("Processing userId={}", userId);`

Every `log.error(...)` must include at least one identifying field (entity ID, input value, or operation type) so errors are traceable without a debugger.
