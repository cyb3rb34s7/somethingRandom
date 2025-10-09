# Automated Context Builder Workflow

This workflow analyzes your codebase to automatically extract coding patterns, conventions, and architectural decisions. It creates comprehensive context documentation that will be used by the PR review workflow.

**Goal:** Generate accurate, specific, example-rich context files by analyzing the actual codebase.

**Important:** You MUST analyze REAL code from this repository. Do NOT make assumptions or provide generic advice. Every pattern you document MUST be backed by actual examples from the codebase.

---

## Phase 1: Initialize Context Directory

First, create the context directory structure:

```bash
mkdir -p .cline/context
mkdir -p .cline/workflows
```

---

## Phase 2: Analyze Java Spring Boot Patterns

### Step 2.1: Find All Spring Boot Components

Execute these searches to discover Spring Boot files:

```bash
# Find all controllers
find . -type f -name "*.java" -path "*/controller/*" | head -20

# Find all services
find . -type f -name "*.java" -path "*/service/*" | head -20

# Find all repositories
find . -type f -name "*.java" -path "*/repository/*" | head -20

# Find configuration classes
find . -type f -name "*.java" | xargs grep -l "@Configuration" | head -10

# Find exception handlers
find . -type f -name "*.java" | xargs grep -l "@ControllerAdvice\|@ExceptionHandler" | head -10
```

### Step 2.2: Analyze Controller Patterns

Read 5-7 different controller files to understand patterns:

```xml
<read_file>
<path>{first_controller_path}</path>
</read_file>

<read_file>
<path>{second_controller_path}</path>
</read_file>

<!-- Repeat for 5-7 controllers -->
```

**What to look for in Controllers:**
1. **Class-level annotations:** What annotations are consistently used? (@RestController, @RequestMapping, @CrossOrigin, @Validated, etc.)
2. **Base class patterns:** Do controllers extend a common base class? If yes, read that base class.
3. **Dependency injection:** How are dependencies injected? Constructor injection? Field injection? @Autowired vs @RequiredArgsConstructor?
4. **Method signatures:** 
   - What do endpoint methods return? (ResponseEntity? Custom wrapper classes? Plain objects?)
   - What status codes are used and when?
   - How are path variables, query params, and request bodies handled?
5. **Validation:** Where and how is validation performed? (@Valid, @Validated, manual validation?)
6. **Exception handling:** How are exceptions thrown? Custom exceptions? Standard exceptions?
7. **Response structure:** Is there a consistent response wrapper? (Result<T>, ApiResponse<T>, etc.)
8. **Logging:** Is logging consistent? What's logged at what level?
9. **Documentation:** Any Swagger/OpenAPI annotations? JavaDoc patterns?
10. **Common utilities:** Any utility methods or helper classes frequently used?

**Pattern Recognition Task:**
After reading the controllers, identify:
- "I notice that ALL controllers follow pattern X"
- "I see that 80% of controllers do Y"
- "There are two different patterns: older controllers do A, newer ones do B"
- "Controllers in module X differ from module Y in this way"

### Step 2.3: Analyze Service Layer Patterns

Read 5-7 service files:

```xml
<read_file>
<path>{first_service_path}</path>
</read_file>

<!-- Repeat for 5-7 services -->
```

**What to look for in Services:**
1. **Class structure:** Interface + implementation? Just classes? Abstract base classes?
2. **Transaction management:** Where is @Transactional used? On class or method level? Propagation settings?
3. **Business logic organization:** How is complex logic structured? Helper methods? Private methods?
4. **Error handling:** How are errors handled? Throw exceptions? Return error objects? Logging patterns?
5. **Dependency management:** What do services depend on? Repositories? Other services? External APIs?
6. **Data transformation:** Where does DTO ↔ Entity conversion happen? MapStruct? Manual mapping? Utility classes?
7. **Validation:** Business validation logic patterns
8. **Caching:** Any caching annotations or patterns? (@Cacheable, @CacheEvict, etc.)
9. **Async operations:** Any @Async methods? CompletableFuture usage?
10. **Testing:** Look at test files for services to understand testing patterns

### Step 2.4: Analyze Repository Patterns

Read 3-5 repository interfaces:

```xml
<read_file>
<path>{first_repository_path}</path>
</read_file>

<!-- Repeat for 3-5 repositories -->
```

**What to look for in Repositories:**
1. **Interface patterns:** Extend JpaRepository? CrudRepository? Custom base repository?
2. **Method naming:** Naming conventions for query methods (findByXXX, getXXX, etc.)
3. **Custom queries:** @Query annotations? Query methods? Specifications?
4. **Native queries:** When are native queries used vs JPQL?
5. **Projections:** Any projection interfaces or DTOs?

### Step 2.5: Analyze Exception Handling

Find and read exception handler classes:

```bash
find . -type f -name "*.java" | xargs grep -l "@ControllerAdvice\|@ExceptionHandler"
```

```xml
<read_file>
<path>{exception_handler_path}</path>
</read_file>
```

**What to look for:**
1. **Exception hierarchy:** Custom exception classes? Base exception class?
2. **HTTP status mapping:** Which exceptions map to which HTTP status codes?
3. **Error response format:** Consistent error response structure?
4. **Logging strategy:** What's logged when exceptions occur?

### Step 2.6: Analyze Configuration Patterns

Read configuration classes:

```bash
find . -type f -name "*.java" | xargs grep -l "@Configuration" | head -5
```

**What to look for:**
1. **Bean definitions:** Common beans? Custom configurations?
2. **Profile usage:** Different configs for different environments?
3. **Properties:** How are external properties used? @Value? @ConfigurationProperties?

### Step 2.7: Generate Java Spring Boot Context File

Now create `.cline/context/java-springboot-patterns.md`:

```xml
<write_file>
<path>.cline/context/java-springboot-patterns.md</path>
<content>
# Java Spring Boot Patterns

**Last Updated:** {current_date}
**Analyzed Files:** {count} controllers, {count} services, {count} repositories

---

## Controller Layer Patterns

### Structure
{Describe the actual pattern you found}

**Example Controllers:**
- `{actual_file_path_1}` - {brief description}
- `{actual_file_path_2}` - {brief description}

### Standard Annotations
```java
{Paste actual annotation pattern from codebase}
```

### Dependency Injection
**Pattern Found:** {Constructor injection / Field injection / Mixed}
```java
{Paste actual example from codebase}
```

### Endpoint Method Signatures
**Return Type Pattern:** {ResponseEntity<T> / Custom wrapper / etc}
```java
{Paste actual method signature from codebase}
```

### Request Validation
**Pattern Found:** {Where and how validation happens}
```java
{Paste actual validation example}
```

### Exception Handling in Controllers
**Pattern Found:** {How exceptions are thrown}
```java
{Paste actual exception throwing example}
```

### Response Structure
**Pattern Found:** {Describe consistent response format}
```java
{Paste actual response wrapper if exists}
```

### Common Mistakes to Avoid
- {Based on inconsistencies you found}
- {Based on older vs newer patterns}

---

## Service Layer Patterns

### Structure
**Pattern Found:** {Interface + Impl / Just classes / etc}

**Example Services:**
- `{actual_file_path_1}`
- `{actual_file_path_2}`

### Transaction Management
**@Transactional Usage:** {Class level / Method level}
**Propagation Settings:** {REQUIRED / REQUIRES_NEW / etc if specified}
```java
{Paste actual @Transactional usage from codebase}
```

### Business Logic Organization
{Describe how complex logic is structured}

### Error Handling
**Pattern Found:** {How errors are handled}
```java
{Paste actual error handling example}
```

### Data Transformation (DTO ↔ Entity)
**Pattern Found:** {MapStruct / Manual / Utility class}
**Location:** {Where conversion happens}
```java
{Paste actual conversion example}
```

### Service Dependencies
**Pattern Found:** {What services typically depend on}
- Repositories: {Yes/No - examples}
- Other Services: {Yes/No - examples}
- External APIs: {Yes/No - examples}

---

## Repository Layer Patterns

### Structure
**Pattern Found:** {Extends JpaRepository / CrudRepository / Custom}

**Example Repositories:**
- `{actual_file_path_1}`
- `{actual_file_path_2}`

### Method Naming Conventions
**Pattern Found:** {findByXXX / getXXX / etc}
```java
{Paste actual method examples}
```

### Custom Queries
**@Query Usage:** {Common / Rare / Preferred approach}
```java
{Paste actual @Query examples}
```

### Native Queries
**When Used:** {Describe when native queries are used vs JPQL}
```java
{Paste example if exists}
```

---

## Exception Handling Architecture

### Exception Hierarchy
**Files Found:**
- `{exception_handler_file_path}`
- `{custom_exception_paths}`

### Exception Flow
```
{Describe the exception handling flow}
Controller throws → {what type} → Handler catches → Returns {what format}
```

### HTTP Status Mapping
```java
{Paste actual exception → status code mapping}
```

### Error Response Format
```json
{Paste actual error response structure}
```

---

## Configuration Patterns

### Bean Configuration
{Describe common bean patterns}

### Properties Management
**Pattern Found:** {@Value / @ConfigurationProperties}
```java
{Paste actual examples}
```

---

## Common Utilities and Helpers

### Frequently Used Utility Classes
- `{util_class_1}` - {what it does}
- `{util_class_2}` - {what it does}

### Base Classes
- `{base_class_if_exists}` - {what it provides}

---

## DO's and DON'Ts Based on This Codebase

### DO:
- ✓ {Pattern consistently followed}
- ✓ {Pattern consistently followed}
- ✓ {Pattern consistently followed}

### DON'T:
- ✗ {Anti-pattern found}
- ✗ {Anti-pattern found}

### INCONSISTENCIES FOUND:
- ⚠️ {Describe any inconsistencies}
- ⚠️ {Old vs new Angular patterns}

---

## References for PR Review

When reviewing TypeScript/Angular code, check:

1. **Components:**
   - [ ] Decorator pattern matches {reference_file}
   - [ ] DI pattern consistent
   - [ ] Lifecycle hooks appropriate
   - [ ] Subscription management correct
   - [ ] Change detection strategy appropriate

2. **Services:**
   - [ ] Injectable pattern correct
   - [ ] HTTP calls typed properly
   - [ ] Error handling consistent
   - [ ] Observable patterns match codebase

3. **Models/Interfaces:**
   - [ ] Naming convention followed
   - [ ] Type annotations complete
   - [ ] Optional properties handled correctly

**Example Reference Files (Good Patterns):**
- `{path_to_well_written_component}` - Good example of {what}
- `{path_to_well_written_service}` - Good example of {what}

</content>
</write_file>
```

---

## Phase 5: Identify Anti-Patterns and Common Issues

### Step 5.1: Search for Known Problematic Patterns

Execute these searches across the codebase:

```bash
# Find potential null pointer issues
grep -r "\.get(" --include="*.java" src/ | wc -l
grep -r "Optional\.of\|Optional\.ofNullable" --include="*.java" src/ | wc -l

# Find potential SQL injection in MyBatis
find . -name "*.xml" -path "*/mapper/*" -exec grep -l '\${' {} \;

# Find console.log in TypeScript (should be removed in production)
grep -r "console\.log\|console\.error" --include="*.ts" src/ | wc -l

# Find any.subscribe without unsubscribe
grep -r "\.subscribe(" --include="*.component.ts" src/ | head -20

# Find @Transactional on controllers (usually wrong)
grep -r "@Transactional" --include="*Controller.java" src/

# Find hardcoded URLs or credentials
grep -r "http://\|https://" --include="*.java" --include="*.ts" src/ | grep -v "example\|localhost" | head -20
```

### Step 5.2: Analyze Git History for Bug Fixes

```bash
# Find commits that fixed bugs
git log --all --grep="fix\|bug\|issue" --oneline | head -30

# Look at a few bug fix commits to understand what went wrong
git show {commit_hash} | head -100
```

Read 3-5 bug fix commits to understand common issues.

### Step 5.3: Look for TODOs and FIXMEs

```bash
# Find TODOs and FIXMEs
grep -r "TODO\|FIXME\|HACK\|XXX" --include="*.java" --include="*.ts" src/ | head -30
```

### Step 5.4: Check for Deprecated Code

```bash
# Find @Deprecated annotations
grep -r "@Deprecated" --include="*.java" src/

# Find deprecated Angular patterns
grep -r "EventEmitter<" --include="*.ts" src/ | head -20
```

### Step 5.5: Generate Anti-Patterns File

```xml
<write_file>
<path>.cline/context/anti-patterns.md</path>
<content>
# Anti-Patterns and Common Issues

**Last Updated:** {current_date}
**Analysis Based On:** Git history, code searches, pattern analysis

---

## Known Issues from Git History

### Bug Patterns Found
Based on analyzing bug fix commits, these issues have occurred:

1. **Issue Type:** {e.g., Null Pointer Exceptions}
   **Occurrence:** {describe from git history}
   **Example Commit:** {commit_hash} - {commit message}
   **Root Cause:** {what caused it}
   **Prevention:** {how to avoid}
   ```java
   {Paste problematic code pattern if available}
   ```

2. **Issue Type:** {e.g., Transaction Management}
   **Occurrence:** {describe}
   **Example Commit:** {commit_hash}
   **Root Cause:** {what caused it}
   **Prevention:** {how to avoid}

{Repeat for other issues found in git history}

---

## Java/Spring Boot Anti-Patterns

### Found in Codebase

1. **@Transactional on Controllers**
   **Files Found:** {list files if any}
   ```java
   {Paste example}
   ```
   **Why It's Wrong:** Transactions should be at service layer
   **Correct Pattern:** {reference to service pattern file}

2. **Improper Optional Handling**
   **Pattern Found:** {describe if found}
   ```java
   {Paste problematic pattern}
   ```
   **Why It's Wrong:** {explain}
   **Correct Pattern:** {paste correct pattern from codebase}

3. **Exception Swallowing**
   **Search Results:** {found yes/no}
   ```java
   {Paste example if found}
   ```
   **Why It's Wrong:** Makes debugging impossible
   **Correct Pattern:** {paste correct exception handling}

{Add more anti-patterns found}

---

## MyBatis Anti-Patterns

### Found in Codebase

1. **SQL Injection Risk (${} usage)**
   **Files Found:**
   {List all files using ${}}
   ```xml
   {Paste examples}
   ```
   **Why It's Dangerous:** Direct SQL injection vulnerability
   **Correct Pattern:** Use #{} for parameter binding

2. **N+1 Query Problems**
   **Pattern Found:** {describe if found}
   ```xml
   {Paste problematic query pattern}
   ```
   **Why It's Wrong:** Performance issue
   **Correct Pattern:** {paste correct pattern with joins}

3. **Missing Parameter Types**
   **Pattern Found:** {describe if found}
   **Why It's Wrong:** {explain}
   **Correct Pattern:** {paste correct pattern}

{Add more MyBatis anti-patterns}

---

## TypeScript/Angular Anti-Patterns

### Found in Codebase

1. **Memory Leaks from Subscriptions**
   **Pattern Found:** {how many subscriptions without unsubscribe}
   ```typescript
   {Paste problematic pattern}
   ```
   **Why It's Wrong:** Memory leaks
   **Correct Pattern:** {paste correct unsubscribe pattern from codebase}

2. **Console.log in Production Code**
   **Occurrences:** {count from grep}
   **Files:** {list some files}
   **Why It's Wrong:** Should be removed before production
   **Correct Pattern:** Use proper logging service or remove

3. **Any Type Usage**
   **Pattern Found:** {search for : any}
   ```typescript
   {Paste examples}
   ```
   **Why It's Wrong:** Defeats TypeScript's purpose
   **Correct Pattern:** Use proper typing

4. **Not Using Async Pipe**
   **Pattern Found:** {manual subscription instead of async pipe}
   ```typescript
   {Paste problematic pattern}
   ```
   **Why It's Wrong:** Manual memory management needed
   **Correct Pattern:** Use async pipe when possible

{Add more Angular anti-patterns}

---

## Architecture Anti-Patterns

### Boundary Violations

1. **Controllers Accessing Repositories Directly**
   **Found:** {yes/no - list files if found}
   **Why It's Wrong:** Breaks service layer pattern
   **Correct Pattern:** Controllers → Services → Repositories

2. **Circular Dependencies**
   **Found:** {yes/no - describe if found}
   **Why It's Wrong:** Creates tight coupling
   **Resolution:** {how it should be fixed}

3. **God Classes**
   **Found:** {yes/no - list large classes}
   **Why It's Wrong:** Violates SRP
   **Resolution:** {suggest refactoring}

---

## Performance Anti-Patterns

### Found Issues

1. **N+1 Queries**
   **Locations:** {list if found}
   **Impact:** {describe performance impact}
   **Solution:** {eager loading / join patterns}

2. **Missing Indexes**
   **Queries Without Indexes:** {if determinable}
   **Impact:** Slow queries
   **Solution:** Add indexes on commonly queried fields

3. **Large Result Sets Without Pagination**
   **Found:** {yes/no - examples}
   **Impact:** Memory issues
   **Solution:** Always paginate large datasets

---

## Security Anti-Patterns

### Found Issues

1. **Hardcoded Credentials/URLs**
   **Occurrences:** {from grep search}
   ```java
   {Paste examples if found (redact sensitive info)}
   ```
   **Why It's Dangerous:** Security risk
   **Correct Pattern:** Use configuration properties

2. **Missing Input Validation**
   **Pattern Found:** {describe}
   **Why It's Dangerous:** {explain risks}
   **Correct Pattern:** {validation pattern from codebase}

3. **SQL Injection Vulnerabilities**
   **Files:** {from MyBatis ${} search}
   **Why It's Dangerous:** Database compromise
   **Correct Pattern:** Use #{} parameterization

---

## Code Smells Found

### Duplication

**Pattern Found:** {describe code duplication if found}
**Locations:**
- {file1} and {file2} - {what's duplicated}
- {file3} and {file4} - {what's duplicated}

**Solution:** Extract to utility/helper class

### Long Methods

**Pattern Found:** {describe if found}
**Examples:**
- {file}:{method} - {line count}
- {file}:{method} - {line count}

**Solution:** Break into smaller methods

### Magic Numbers/Strings

**Pattern Found:** {describe if found}
```java
{Paste examples}
```
**Solution:** Use constants or enums

---

## TODOs and Technical Debt

**Count:** {total TODOs found}

**High Priority TODOs:**
```
{Paste important TODOs from grep}
```

**Areas of Technical Debt:**
1. {area1} - {description}
2. {area2} - {description}

---

## Deprecated Patterns Still in Use

**Found:** {yes/no}

**Deprecated Code:**
- {file} - uses deprecated {what}
- {file} - uses deprecated {what}

**Migration Path:** {describe how to update}

---

## Checklist for PR Reviews

When reviewing PRs, watch out for:

### Critical Issues (Must Fix)
- [ ] SQL injection via ${} in MyBatis
- [ ] Hardcoded credentials or sensitive data
- [ ] @Transactional on controllers
- [ ] Missing null/undefined checks in critical paths
- [ ] Unhandled exceptions
- [ ] Security vulnerabilities

### High Priority Issues (Should Fix)
- [ ] Memory leaks from subscriptions
- [ ] N+1 query problems
- [ ] Missing pagination on large datasets
- [ ] Improper exception handling
- [ ] Console.log statements
- [ ] Architecture boundary violations

### Code Quality Issues (Nice to Fix)
- [ ] Code duplication
- [ ] Magic numbers/strings
- [ ] Any type usage in TypeScript
- [ ] Long methods (>50 lines)
- [ ] Missing or inadequate comments for complex logic
- [ ] Inconsistent naming

---

## Past Incidents to Remember

{If you found significant issues in git history}

### Incident 1: {Brief description}
**Date:** {from git log}
**Commit:** {hash}
**What Went Wrong:** {describe}
**How to Prevent:** {specific checks in PR review}

### Incident 2: {Brief description}
**Date:** {from git log}
**Commit:** {hash}
**What Went Wrong:** {describe}
**How to Prevent:** {specific checks in PR review}

---

## Reference Examples

**Good Examples (Follow These):**
- `{file_path}` - Good example of {what}
- `{file_path}` - Good example of {what}

**Bad Examples (Don't Follow These):**
- `{file_path}` - Example of {what not to do}
- `{file_path}` - Example of {what not to do}

</content>
</write_file>
```

---

## Phase 6: Create Review Perspectives Guide

### Step 6.1: Generate Perspectives Definition File

```xml
<write_file>
<path>.cline/context/review-perspectives.md</path>
<content>
# Review Perspectives - Detailed Guidelines

**Last Updated:** {current_date}

This document defines what each review perspective means in the context of OUR codebase and what specific things to check.

---

## 🧠 [Logical] - TOP PRIORITY

### What to Check

Logic errors, algorithmic issues, edge cases, and correctness of implementation based on OUR patterns.

### Specific Checks

#### For Java/Spring Boot:

1. **Null/Optional Handling**
   - Are null checks appropriate based on our Optional usage?
   - Reference: `.cline/context/java-springboot-patterns.md#optional-handling`
   - Example from our codebase:
   ```java
   {Paste example of proper Optional handling from codebase}
   ```

2. **Collection Operations**
   - Are loops, streams, and iterations correct?
   - Off-by-one errors?
   - Empty collection handling?
   - Example from our codebase:
   ```java
   {Paste example of proper collection handling}
   ```

3. **Conditional Logic**
   - Are if/else conditions correct?
   - Are all branches handled?
   - Is the logic sound?

4. **Concurrency Issues**
   - Thread safety concerns?
   - Race conditions possible?
   - Are shared resources properly synchronized?

5. **Transaction Boundaries**
   - Is @Transactional placed correctly per our pattern?
   - Are transaction propagations appropriate?
   - Reference pattern: {file_path}

#### For MyBatis:

1. **Query Logic**
   - Are WHERE clauses correct?
   - Are JOINs appropriate?
   - Dynamic SQL logic sound?
   - Example correct dynamic SQL:
   ```xml
   {Paste example from codebase}
   ```

2. **Parameter Handling**
   - Are all parameters bound correctly?
   - Null parameter handling?
   - Reference pattern: `.cline/context/mybatis-patterns.md#parameter-handling`

3. **Result Mapping**
   - Does resultMap correctly map all fields?
   - Are nested results handled properly?

#### For TypeScript/Angular:

1. **Observable Logic**
   - Are RxJS operators used correctly?
   - Is the stream logic sound?
   - Example from our codebase:
   ```typescript
   {Paste example of correct observable usage}
   ```

2. **Conditional Rendering**
   - Are *ngIf conditions correct?
   - Are all template paths handled?

3. **Type Safety**
   - Are type guards used where needed?
   - Are all type assertions safe?
   - Optional chaining used appropriately?

4. **Form Logic**
   - Form validation logic correct?
   - Are all form states handled?

### How to Comment

```markdown
🧠 [Logical]
**File:** {filename}:{line}
**Issue:** {Specific logic error}
**Why:** Based on OUR pattern in {reference_file}, {explain why it's wrong}
**Example:** See how we handle this in {other_file}:{line}
**Fix:** {Specific suggestion}
```

---

## 💡 [Improvement] - HIGH PRIORITY

### What to Check

Better ways to implement based on OUR existing codebase patterns. Not generic best practices, but specific to how WE do things.

### Specific Checks

#### For Java/Spring Boot:

1. **Using Existing Utilities**
   - Could this use our {UtilityClass} instead?
   - Example: Instead of manual validation, use our ValidationUtil
   ```java
   // Instead of this
   {paste suboptimal pattern}
   
   // Use our pattern from {file}
   {paste better pattern from codebase}
   ```

2. **Consistent Response Patterns**
   - Is the controller returning responses like other controllers?
   - Reference: {controller_file} for standard pattern

3. **Service Layer Organization**
   - Could this logic be in an existing service?
   - Should this be extracted to a separate service?

4. **Code Reuse**
   - Is this duplicating code from {existing_file}?
   - Could both use a shared method?

#### For MyBatis:

1. **SQL Optimization**
   - Could this query be more efficient like {reference_mapper}?
   - Should this use our pagination pattern?
   - Example efficient query:
   ```xml
   {Paste optimized query from codebase}
   ```

2. **ResultMap Reuse**
   - Could this reuse an existing resultMap?
   - Reference: {mapper_file}

3. **Dynamic SQL Patterns**
   - Could this use our standard dynamic SQL pattern?
   - Reference: `.cline/context/mybatis-patterns.md#dynamic-sql`

#### For TypeScript/Angular:

1. **Using Existing Services**
   - Could this use our {ExistingService}?
   - Example: Use our HttpService wrapper, not HttpClient directly

2. **Component Structure**
   - Should this be broken into smart/dumb components like {reference}?
   - Could this reuse {existing_component}?

3. **Observable Patterns**
   - Could this use our standard observable pattern from {file}?
   ```typescript
   {Paste standard pattern}
   ```

4. **State Management**
   - Should this use our state service like {reference_file}?

### How to Comment

```markdown
💡 [Improvement]
**File:** {filename}:{line}
**Current:** {what they did}
**Better:** Use OUR pattern from {reference_file}:{line}
**Why:** {explain why our pattern is better in our context}
**Example:** See {other_file} for how we typically do this
```

---

## 🔧 [Maintenance] - MEDIUM PRIORITY

### What to Check

Long-term maintainability, code clarity, and adherence to OUR conventions.

### Specific Checks

1. **Naming Conventions**
   - Do names follow OUR conventions?
   - Reference: {patterns_file}
   - Java: {our_naming_pattern}
   - TypeScript: {our_naming_pattern}

2. **Code Organization**
   - Is code structured like similar files in our codebase?
   - Are methods in logical order per our convention?

3. **Documentation**
   - For complex logic, is there inline explanation?
   - Are method purposes clear?
   - JavaDoc/TSDoc following our format?

4. **Magic Numbers/Strings**
   - Should these be constants?
   - Reference our constant usage pattern: {file}

5. **Method Length**
   - Is this method too long compared to our typical methods?
   - Should it be broken down?

6. **Architectural Consistency**
   - Does this respect our module boundaries?
   - Is it in the right layer (controller/service/repository)?

### How to Comment

```markdown
🔧 [Maintenance]
**File:** {filename}:{line}
**Issue:** {what could be better for maintenance}
**Our Convention:** In our codebase, we typically {describe pattern}
**Reference:** See {file} for example
**Suggestion:** {specific suggestion}
```

---

## 🐛 [Bug] - HIGH PRIORITY

### What to Check

Potential runtime bugs based on OUR specific patterns and environment.

### Specific Checks

#### For Java/Spring Boot:

1. **Exception Handling**
   - Are exceptions handled per our pattern?
   - Could this throw uncaught exceptions?
   - Reference: `.cline/context/java-springboot-patterns.md#exception-handling`
   - Example from past bug:
   ```java
   {Paste example of bug that occurred before}
   ```

2. **Null Pointer Exceptions**
   - Based on our data flow, could this be null?
   - Is Optional handling correct?
   - Past incident: {reference to anti-patterns.md incident}

3. **Transaction Rollback**
   - Could this fail mid-transaction without rollback?
   - Is exception handling preserving transaction rollback?

4. **Resource Leaks**
   - Are resources (files, connections) properly closed?
   - Try-with-resources used appropriately?

#### For MyBatis:

1. **SQL Errors**
   - Could this query fail with certain data?
   - Division by zero? Null in aggregate functions?

2. **Parameter Binding Issues**
   - Could parameter be null causing SQL error?
   - Is ${} used (SQL injection)?
   - Reference: `.cline/context/anti-patterns.md#sql-injection`

3. **Type Mismatches**
   - Do Java types match database types?
   - Could type conversion fail?

#### For TypeScript/Angular:

1. **Undefined/Null Errors**
   - Could properties be undefined?
   - Is optional chaining needed?
   - Past bug example:
   ```typescript
   {Paste example of bug from git history}
   ```

2. **Subscription Leaks**
   - Is subscription properly unsubscribed?
   - Reference pattern: `.cline/context/typescript-angular-patterns.md#subscription-management`

3. **Race Conditions**
   - Could async operations cause issues?
   - Is loading state handled?

4. **Form Errors**
   - Are all form states handled?
   - Could invalid data be submitted?

### How to Comment

```markdown
🐛 [Bug]
**File:** {filename}:{line}
**Potential Bug:** {describe the bug}
**Scenario:** {when/how it could occur in OUR environment}
**Past Incident:** Similar issue in {reference to anti-patterns or git history}
**Fix:** {specific fix based on our patterns}
**Reference:** See correct pattern in {file}:{line}
```

---

## ⚠️ [Critical] - HIGHEST PRIORITY

### What to Check

Security, data loss, breaking changes, severe performance issues.

### Specific Checks

#### Security:

1. **SQL Injection**
   - Any ${} in MyBatis?
   - Dynamic query construction?
   - Reference: `.cline/context/anti-patterns.md#sql-injection`

2. **Authentication/Authorization**
   - Are endpoints properly secured per our pattern?
   - Reference security pattern: {file}

3. **Input Validation**
   - Is user input validated per our pattern?
   - XSS prevention?

4. **Sensitive Data**
   - Is sensitive data logged?
   - Are credentials hardcoded?

#### Data Loss:

1. **Delete Operations**
   - Is deletion safe?
   - Should this be soft delete per our pattern?
   - Reference: {file} for soft delete pattern

2. **Update Without Where Clause**
   - Could this update wrong records?
   - Is WHERE clause always present?

3. **Transaction Issues**
   - Could partial data be committed?
   - Is rollback handled?

#### Breaking Changes:

1. **API Changes**
   - Does this break existing API contracts?
   - Is this backward compatible?

2. **Database Schema**
   - Are migrations included?
   - Is this backward compatible?

3. **Dependency Changes**
   - Does this break other modules?
   - Are all references updated?

#### Performance:

1. **N+1 Queries**
   - Could this cause N+1 problem?
   - Reference: `.cline/context/anti-patterns.md#n-plus-1`
   - Example efficient alternative:
   ```xml
   {Paste efficient query from codebase}
   ```

2. **Memory Issues**
   - Loading large datasets without pagination?
   - Reference pagination pattern: {file}

3. **Infinite Loops**
   - Could this loop indefinitely?
   - Are exit conditions correct?

### How to Comment

```markdown
⚠️ [Critical]
**File:** {filename}:{line}
**Critical Issue:** {describe the critical issue}
**Impact:** {explain potential damage - security/data loss/performance}
**Similar Past Incident:** {reference if applicable}
**Must Fix Before Merge:** {specific fix required}
**Reference:** {security/safety pattern from our codebase}
```

---

## Comment Template Summary

### Structure for All Perspectives:

```markdown
{emoji} [{Perspective}]
**File:** {filename}:{line}
**Issue/Observation:** {specific description}
**In OUR Codebase:** {how we typically handle this}
**Reference:** {specific file/pattern from our codebase}
**Suggestion/Fix:** {actionable recommendation}
```

### Priority Order:

1. ⚠️ [Critical] - Must fix before merge
2. 🧠 [Logical] - Should fix before merge
3. 🐛 [Bug] - Should fix before merge
4. 💡 [Improvement] - Good to fix
5. 🔧 [Maintenance] - Nice to fix

### Tone:

- Be specific, not generic
- Always reference OUR codebase
- Be constructive and educational
- Assume good intent
- Frame as learning opportunity

### Example Full Comment:

```markdown
## PR Review: Add User Profile Update Feature

### 🧠 [Logical] Issues

**File:** UserService.java:45
**Issue:** The method getUserProfile() could return null, but line 67 calls .getName() without null check
**In OUR Codebase:** We use Optional<User> for user lookups (see UserRepository.findById)
**Past Bug:** Similar NPE occurred in ProfileService (commit abc123)
**Fix:** Check Optional.isPresent() or use .orElseThrow()
**Reference:** See UserAuthService.java:34 for our standard pattern

### 💡 [Improvement] Suggestions

**File:** UserController.java:23
**Current:** Using ResponseEntity<User> directly
**Better:** Use our ApiResponse<User> wrapper like other controllers
**Reference:** See ProductController.java:45 for standard response pattern
**Why:** Provides consistent error handling and metadata across all endpoints

{... more perspectives ...}
```

</content>
</write_file>
```

---

## Phase 7: Create Architecture Documentation Template

### Step 7.1: Analyze System Architecture

```bash
# Find main application class
find . -name "*Application.java" -o -name "Main.java"

# Find configuration files
find . -name "application.properties" -o -name "application.yml" -o -name "application.yaml"

# Understand module structure
ls -la src/main/java/com/  # Adjust path as needed
```

Read application configuration:

```xml
<read_file>
<path>{application.yml_or_properties_path}</path>
</read_file>

<read_file>
<path>{main_application_class_path}</path>
</read_file>
```

### Step 7.2: Generate Architecture Template

```xml
<write_file>
<path>.cline/context/architecture.md</path>
<content>
# System Architecture

**Last Updated:** {current_date}
**Application:** {application_name_from_config}
**Tech Stack:** Java {version}, Spring Boot {version}, Angular {version}

---

## System Overview

**Type:** {Monolith / Microservices / Describe what you found}

**Purpose:** {Describe based on package structure and code}

**Main Modules Found:**
{List main packages/modules discovered}

---

## Technical Stack

### Backend
- **Language:** Java {version}
- **Framework:** Spring Boot {version}
- **ORM:** MyBatis {version}
- **Database:** {from config}
- **Build Tool:** {Maven/Gradle - which you found}

### Frontend
- **Language:** TypeScript {version}
- **Framework:** Angular {version}
- **State Management:** {what you found}
- **UI Library:** {if any found}

### Infrastructure (if discoverable)
- **Server:** {if mentioned in config}
- **Port:** {from config}
- **Profiles:** {from application-{profile}.yml files}

---

## Module Structure

**Java Package Structure:**
```
{Paste actual package structure you discovered}
com.{company}.{app}/
├── controller/
│   ├── {list main controllers}
├── service/
│   ├── {list main services}
├── repository/
│   ├── {list main repositories}
├── model/
├── dto/
└── config/
```

**Angular Module Structure:**
```
{Paste actual src structure}
src/
├── app/
│   ├── {list main modules/components}
```

---

## Data Flow

**Standard Request Flow (based on code analysis):**

```
{Describe the actual flow you observed}

1. HTTP Request → {Controller pattern}
2. {Controller} → {Service pattern}
3. {Service} → {Repository pattern}
4. {Repository} → MyBatis → Database
5. Response path (reverse)
```

**Example Flow from actual code:**
```
{Pick one actual flow from the codebase and describe it}
User Login Example:
AuthController.login() 
→ AuthService.authenticate()
→ UserRepository.findByUsername()
→ MyBatis UserMapper.xml
→ Database query
```

---

## API Design

**Base URL:** {from config}
**API Pattern:** {REST / Other - what you found}

**Endpoint Structure:**
{Describe actual endpoint patterns found}
```
{Paste examples of actual endpoints}
```

**Response Format:**
{Describe actual response format}
```json
{Paste example response structure from code}
```

---

## Database Design

**Database:** {from config}
**Schema:** {if discoverable}

**Main Entities Found:**
{List main entity/model classes}
- `{Entity1}` - {describe purpose}
- `{Entity2}` - {describe purpose}

**Relationship Patterns:**
{Describe relationships you found}

---

## Security Architecture

**Authentication:** {pattern found - JWT / Session / Other}
**Authorization:** {pattern found - Role-based / etc}

**Security Configuration:**
{If you found security config, describe it}

**Protected Endpoints:**
{Pattern for protecting endpoints}

---

## Configuration Management

**Config Files:**
- `{path to application.yml/properties}`
- `{path to other configs}`

**Profiles Found:**
{List profiles from application-{profile}.yml}
- {profile1}
- {profile2}

**External Configuration:**
{Environment variables / Config server / etc}

---

## Error Handling

**Global Exception Handler:** `{path if found}`

**Error Response Format:**
```json
{Paste actual error response structure}
```

**Exception Hierarchy:**
{Describe custom exception classes found}

---

## Logging

**Logging Framework:** {SLF4J / Log4j / what you found}

**Log Levels Used:**
{Describe logging patterns from code}

---

## Testing Strategy

{If test files exist, describe patterns}

**Backend Tests:**
- Unit tests: {pattern found}
- Integration tests: {pattern found}

**Frontend Tests:**
- Component tests: {pattern found}
- Service tests: {pattern found}

---

## Important Architectural Rules

Based on code analysis, these rules seem important:

1. **Layered Architecture**
   - Controllers don't access Repositories directly
   - Services contain business logic
   - {Other rules observed}

2. **Transaction Management**
   - @Transactional at service layer
   - {Other patterns}

3. **DTO Usage**
   - {Where DTOs are used vs entities}
   - {Conversion patterns}

4. **{Other architectural rules you discovered}**

---

## Module Dependencies

**Backend Module Dependencies:**
{Describe how modules depend on each other}
```
{module1} → depends on → {module2}
```

**Frontend Module Dependencies:**
{Describe Angular module dependencies}

---

## Integration Points

**External APIs:** {if any found in config}
**Message Queues:** {if any found}
**Cache:** {if any found}
**File Storage:** {if any found}

---

## Deployment

**Build Command:** {mvn clean install / npm run build / what you found}
**Artifact:** {JAR / WAR / what's produced}
**Static Assets:** {where Angular build goes}

---

## Things to Verify in PR Review

### Architectural Boundaries
- [ ] Controllers only call services
- [ ] Services contain business logic
- [ ] Repositories only for data access
- [ ] No circular dependencies

### Module Boundaries
- [ ] Changes respect module isolation
- [ ] No inappropriate cross-module dependencies

### API Design
- [ ] Endpoints follow our REST conventions
- [ ] Response format consistent with existing APIs
- [ ] Error responses match our standard format

### Configuration
- [ ] No hardcoded values that should be in config
- [ ] Environment-specific values in correct profile

---

## References

**Key Files to Reference in Reviews:**
- **Controller Example:** `{path_to_good_controller}`
- **Service Example:** `{path_to_good_service}`
- **Repository Example:** `{path_to_good_repository}`
- **Configuration:** `{path_to_main_config}`

</content>
</write_file>
```

---

## Phase 8: Validate and Summarize

### Step 8.1: Verify All Files Created

Check that all context files were successfully created:

```bash
ls -la .cline/context/
```

Expected files:
- `architecture.md`
- `java-springboot-patterns.md`
- `mybatis-patterns.md`
- `typescript-angular-patterns.md`
- `anti-patterns.md`
- `review-perspectives.md`

### Step 8.2: Generate Summary Report

```xml
<write_file>
<path>.cline/context/README.md</path>
<content>
# Codebase Context Documentation

**Generated:** {current_date}
**Purpose:** Context files for automated PR reviews

---

## Overview

This directory contains automatically extracted patterns, conventions, and guidelines from our codebase. These files are used by the PR review workflow to provide codebase-specific, actionable feedback.

---

## Files

### 1. `architecture.md`
**Purpose:** System architecture, modules, data flow, and design decisions

**Contains:**
- Technical stack details
- Module structure
- API design patterns
- Database design
- Security architecture
- Configuration management

**When to Update:** When architecture changes, new modules added, or major refactoring

---

### 2. `java-springboot-patterns.md`
**Purpose:** Java Spring Boot coding patterns and conventions

**Contains:**
- Controller layer patterns
- Service layer patterns
- Repository patterns
- Exception handling
- Transaction management
- Dependency injection patterns
- Configuration patterns

**Analyzed:** {count} controllers, {count} services, {count} repositories

**When to Update:** When Spring Boot patterns evolve or new conventions adopted

---

### 3. `mybatis-patterns.md`
**Purpose:** MyBatis mapper patterns and SQL conventions

**Contains:**
- XML mapper patterns
- Java mapper interface patterns
- Dynamic SQL conventions
- Pagination patterns
- Parameter handling
- Result mapping patterns

**Analyzed:** {count} XML mappers, {count} Java mapper interfaces

**When to Update:** When MyBatis patterns change or new query patterns emerge

---

### 4. `typescript-angular-patterns.md`
**Purpose:** TypeScript and Angular coding patterns

**Contains:**
- Component patterns
- Service patterns
- Module organization
- RxJS patterns
- State management
- Form handling
- Type usage conventions

**Analyzed:** {count} components, {count} services, {count} modules

**When to Update:** When Angular version updates or patterns evolve

---

### 5. `anti-patterns.md`
**Purpose:** Known issues, bugs, and things to avoid

**Contains:**
- Historical bug patterns from git history
- Common mistakes in codebase
- Performance anti-patterns
- Security issues
- Architecture violations
- Technical debt areas

**Based On:** Git history analysis, code searches, pattern inconsistencies

**When to Update:** When new bugs discovered or patterns identified

---

### 6. `review-perspectives.md`
**Purpose:** Detailed guidelines for each review perspective

**Contains:**
- Logical error checking guidelines
- Improvement suggestions criteria
- Maintenance concerns checklist
- Bug detection patterns
- Critical issue identification

**When to Update:** When review priorities change or new check types needed

---

## Usage

### For PR Reviews

These files are automatically loaded by the `review-pr.md` workflow when reviewing pull requests.

**To review a PR:**
```
/review-pr.md {PR_NUMBER}
```

The workflow will:
1. Load all context from these files
2. Analyze PR against our patterns
3. Generate perspective-based review
4. Post to GitHub

### For Manual Reference

Developers can read these files to understand:
- How we structure code
- What patterns to follow
- What mistakes to avoid
- Examples of good code in our codebase

---

## Maintenance

### Updating Context Files

#### Option 1: Re-run Context Builder
```
/build-context.md
```
This will regenerate all files based on current codebase.

**Warning:** This overwrites existing files. Save manual additions first.

#### Option 2: Manual Updates
Edit individual files to:
- Add new patterns as they emerge
- Document new conventions
- Add examples from recent PRs
- Update references

#### Option 3: Incremental Updates
As you use the PR review workflow, you'll notice:
- Missing patterns
- Incorrect assumptions
- Outdated references

Update the relevant context file to reflect reality.

### Update Frequency

**Recommended:**
- **architecture.md:** Every major release
- **Pattern files:** Every sprint/month
- **anti-patterns.md:** When bugs discovered
- **review-perspectives.md:** When review priorities change

---

## Statistics

### Codebase Analysis

**Java/Spring Boot:**
- Controllers analyzed: {count}
- Services analyzed: {count}
- Repositories analyzed: {count}
- Configuration files: {count}

**MyBatis:**
- XML mappers analyzed: {count}
- Java mapper interfaces: {count}
- Dynamic SQL patterns found: {count}

**TypeScript/Angular:**
- Components analyzed: {count}
- Services analyzed: {count}
- Modules analyzed: {count}

**Anti-Patterns:**
- Historical bugs analyzed: {count}
- Potential issues found: {count}
- Code smells identified: {count}

---

## Quality Metrics

**Pattern Consistency:**
- Controllers: {high/medium/low consistency}
- Services: {high/medium/low consistency}
- Repositories: {high/medium/low consistency}
- Components: {high/medium/low consistency}

**Documentation Coverage:**
- Java: {percentage}% of classes have JavaDoc
- TypeScript: {percentage}% of classes have TSDoc

**Issues Found:**
- Critical: {count}
- High Priority: {count}
- Medium Priority: {count}

---

## Next Steps

### 1. Review Generated Content
- Read each context file
- Verify accuracy
- Add missing patterns
- Correct any misinterpretations

### 2. Test PR Review Workflow
- Run `/review-pr.md` on a sample PR
- Check if feedback is accurate
- Verify references work
- Adjust prompts if needed

### 3. Iterate and Improve
- Gather feedback from team
- Refine perspective definitions
- Add more examples
- Update patterns as codebase evolves

### 4. Automate (Optional)
- Once workflow is solid, consider GitHub Actions automation
- Schedule periodic context regeneration
- Set up notifications for reviews

---

## Troubleshooting

### Issue: Context files seem inaccurate
**Solution:** Re-run `/build-context.md` or manually correct specific sections

### Issue: PR reviews missing important checks
**Solution:** Update `review-perspectives.md` with new check criteria

### Issue: References point to wrong files
**Solution:** Update file paths in pattern files

### Issue: Too many false positives in reviews
**Solution:** Refine patterns to be more specific, add counter-examples

---

## Contributing

When adding new patterns or updating context:

1. **Be Specific:** Always reference actual files from codebase
2. **Use Examples:** Include real code snippets
3. **Explain Why:** Document the reasoning behind patterns
4. **Keep Updated:** Remove outdated patterns
5. **Test:** Verify changes improve PR review quality

---

## Contact

For questions about these context files or the PR review workflow:
- Review the workflow: `.cline/workflows/review-pr.md`
- Check documentation in each context file
- Discuss with team for pattern clarifications

---

**Remember:** These files are living documentation. Keep them updated as the codebase evolves!
</content>
</write_file>
```

### Step 8.3: Create Final Summary for User

Present a comprehensive summary:

```xml
<ask_followup_question>
<question>
✅ **Context Generation Complete!**

I've successfully analyzed your codebase and generated comprehensive context documentation.

## Files Created:

1. **`.cline/context/architecture.md`**
   - System overview and module structure
   - Data flow patterns
   - API design
   - {X} main modules documented

2. **`.cline/context/java-springboot-patterns.md`**
   - Analyzed {X} controllers, {X} services, {X} repositories
   - Documented controller, service, and repository patterns
   - Exception handling and transaction management patterns
   - {X} code examples included

3. **`.cline/context/mybatis-patterns.md`**
   - Analyzed {X} XML mappers, {X} Java interfaces
   - SQL patterns and conventions
   - Dynamic SQL usage patterns
   - {X} potential SQL injection risks found (flagged in anti-patterns)

4. **`.cline/context/typescript-angular-patterns.md`**
   - Analyzed {X} components, {X} services
   - Component and service patterns
   - RxJS and state management patterns
   - {X} subscription patterns documented

5. **`.cline/context/anti-patterns.md`**
   - {X} historical bugs analyzed from git history
   - {X} code smells identified
   - {X} potential issues flagged
   - Common mistakes and prevention strategies

6. **`.cline/context/review-perspectives.md`**
   - Detailed guidelines for each review perspective
   - Specific checks for Logical, Improvement, Maintenance, Bug, Critical
   - Comment templates and examples

7. **`.cline/context/README.md`**
   - Overview and usage guide
   - Maintenance instructions
   - Statistics summary

## Key Findings:

### Patterns Found:
- {Describe key patterns discovered}
- {Consistency level of patterns}

### Issues Identified:
- {Count and types of issues found}
- {Critical issues flagged}

### Inconsistencies:
- {Describe any inconsistencies between different parts of codebase}

## Next Steps:

Would you like me to:
1. **Review and refine** specific sections of the generated context?
2. **Test the PR review workflow** on a sample PR?
3. **Add more detail** to specific patterns?
4. **Explain findings** in more detail?

The context files are ready for use with `/review-pr.md {PR_NUMBER}`!
</question>
<options>["Review specific sections", "Test PR review workflow now", "Add more detail", "Looks good, I'll test it myself"]</options>
</ask_followup_question>
```

---

## Important Notes for Execution

### Critical Instructions:

1. **NEVER Invent Patterns**
   - Only document what you ACTUALLY see in the code
   - If unsure, mark as "Needs Verification"
   - Use exact file paths and code snippets

2. **Be Thorough**
   - Read multiple examples of each file type
   - Look for patterns AND inconsistencies
   - Document both good and bad examples

3. **Provide Context**
   - Always link patterns to actual files
   - Include line numbers for examples
   - Explain WHY a pattern exists if determinable

4. **Handle Inconsistencies**
   - Document when different parts of codebase do things differently
   - Note old vs new patterns
   - Highlight which pattern to prefer

5. **Use Real Examples**
   - Copy actual code snippets (not pseudo-code)
   - Use real file paths
   - Reference actual git commits for bugs

6. **Quantify**
   - Count how many files follow pattern
   - Note percentages (e.g., "80% of controllers do X")
   - Provide statistics

---

## Error Handling

If you encounter issues during analysis:

### Can't Find Files
```bash
# Search more broadly
find . -type f -name "*.java" | head -50
find . -type f -name "*.ts" | head -50
```

### Can't Determine Pattern
- Read more examples
- Look for comments in code
- Check git history for context
- Mark as "Pattern Unclear - Needs Manual Review"

### Too Many Variations
- Document all variations found
- Note which is most common
- Suggest standardization in review-perspectives.md

### Files Too Large
- Read sections at a time
- Focus on key methods
- Use grep to find specific patterns

---

## Workflow Complete

Once all phases are done:
1. All 6 context files created
2. README.md generated
3. Summary presented to user
4. Ready for PR review workflow testing

**Time Estimate:** This workflow should take 10-20 minutes to complete depending on codebase size.

**Result:** Comprehensive, codebase-specific context that enables intelligent, actionable PR reviews.base

### DO:
- ✓ {Pattern consistently followed}
- ✓ {Pattern consistently followed}
- ✓ {Pattern consistently followed}

### DON'T:
- ✗ {Anti-pattern found / inconsistency}
- ✗ {Anti-pattern found / inconsistency}

### INCONSISTENCIES FOUND:
- ⚠️ {Describe any inconsistencies between files}
- ⚠️ {Old vs new patterns}

---

## References for PR Review

When reviewing Java Spring Boot code, check:

1. **Controller Layer:**
   - [ ] Follows annotation pattern from {reference_file}
   - [ ] Uses consistent response structure
   - [ ] Proper validation as in {reference_file}
   - [ ] Exception handling matches pattern

2. **Service Layer:**
   - [ ] Transaction boundaries correct
   - [ ] Error handling consistent
   - [ ] DTO conversion in right place

3. **Repository Layer:**
   - [ ] Method naming follows convention
   - [ ] Query patterns match existing code

</content>
</write_file>
```

**Critical Instructions for Writing This File:**
1. DO NOT invent patterns - only document what you ACTUALLY see
2. Include REAL file paths as references
3. Include REAL code snippets (not pseudo-code)
4. Note inconsistencies and variations
5. Be specific: "Controllers in `auth` module do X, but `user` module does Y"
6. If unsure about a pattern, mark it as "Needs Verification"

---

## Phase 3: Analyze MyBatis Patterns

### Step 3.1: Find MyBatis Files

```bash
# Find XML mappers
find . -type f -name "*.xml" -path "*/mapper/*" -o -path "*/mybatis/*" | head -20

# Find Java mapper interfaces
find . -type f -name "*Mapper.java" -o -name "*Dao.java" | head -20

# Find MyBatis config
find . -type f -name "mybatis-config.xml" -o -name "*mybatis*.xml"
```

### Step 3.2: Analyze Mapper XML Files

Read 5-7 mapper XML files:

```xml
<read_file>
<path>{first_mapper_xml_path}</path>
</read_file>

<!-- Repeat for 5-7 mappers -->
```

**What to look for in Mapper XMLs:**
1. **Namespace pattern:** How are namespaces structured?
2. **SQL ID naming:** Conventions for select, insert, update, delete IDs?
3. **Parameter handling:**
   - Single parameter vs multiple parameters?
   - Use of @Param annotation?
   - ParameterType specifications?
4. **Result mapping:**
   - ResultType vs ResultMap?
   - Custom ResultMaps? Naming conventions?
   - Nested results? Association/Collection mappings?
5. **Dynamic SQL patterns:**
   - Common use of `<if>`, `<choose>`, `<where>`, `<set>`, `<foreach>`?
   - Trim usage patterns?
   - SQL fragment reuse (`<sql>` and `<include>`)?
6. **Pagination:**
   - How is pagination handled? RowBounds? Limit/Offset? Plugin?
   - Any standard pagination patterns?
7. **SQL style:**
   - Formatting conventions
   - Use of aliases
   - Join patterns (inner, left, subqueries?)
8. **Type handlers:** Any custom type handlers?
9. **Common SQL fragments:** Reusable SQL pieces?

### Step 3.3: Analyze Java Mapper Interfaces

Read 5-7 mapper interfaces:

```xml
<read_file>
<path>{first_mapper_interface_path}</path>
</read_file>

<!-- Repeat for 5-7 mapper interfaces -->
```

**What to look for in Mapper Interfaces:**
1. **Annotation usage:** @Mapper? @Repository? Other annotations?
2. **Method naming:** Naming conventions?
3. **Parameter annotations:** Consistent use of @Param?
4. **Return types:** What types are returned? Lists, POJOs, Optional, Map?
5. **Annotation-based queries:** Any @Select, @Insert, @Update, @Delete?

### Step 3.4: Look for MyBatis Configuration

```xml
<read_file>
<path>{mybatis_config_path}</path>
</read_file>
```

**What to look for:**
1. Type aliases
2. Settings (cacheEnabled, lazyLoadingEnabled, etc.)
3. Plugins
4. Type handlers

### Step 3.5: Check for Common MyBatis Issues

Search for potential issues:

```bash
# Check for potential SQL injection risks
find . -type f -name "*.xml" -path "*/mapper/*" -exec grep -l '\${' {} \;

# Check for missing parameterType/resultType
grep -r "select id=" --include="*.xml" .cline/context/ 2>/dev/null || find . -type f -name "*.xml" -path "*/mapper/*" | head -5
```

### Step 3.6: Generate MyBatis Context File

```xml
<write_file>
<path>.cline/context/mybatis-patterns.md</path>
<content>
# MyBatis Patterns

**Last Updated:** {current_date}
**Analyzed Files:** {count} XML mappers, {count} Java mapper interfaces

---

## XML Mapper Patterns

### File Location
**Pattern Found:** {where mapper XMLs are located}

**Example Mappers:**
- `{actual_xml_path_1}` - {what entity/domain}
- `{actual_xml_path_2}` - {what entity/domain}

### Namespace Convention
**Pattern Found:** {how namespaces are structured}
```xml
{Paste actual namespace example}
```

### SQL ID Naming Convention
**Pattern Found:** {naming pattern for SQL IDs}

**Examples from codebase:**
```xml
<select id="{actual_id_from_codebase}" ...>
<insert id="{actual_id_from_codebase}" ...>
<update id="{actual_id_from_codebase}" ...>
<delete id="{actual_id_from_codebase}" ...>
```

### Parameter Handling

**Single Parameter Pattern:**
```xml
{Paste actual example from codebase}
```

**Multiple Parameters Pattern:**
```xml
{Paste actual example from codebase}
```

**@Param Usage in Java Interface:**
```java
{Paste actual example from codebase}
```

### Result Mapping

**ResultType Usage:**
```xml
{Paste actual example where resultType is used}
```

**ResultMap Usage:**
```xml
{Paste actual resultMap definition from codebase}
{Paste actual select using that resultMap}
```

**Association/Collection Patterns:**
```xml
{Paste actual nested mapping example if exists}
```

---

## Dynamic SQL Patterns

### Common Dynamic SQL Usage

**Pattern Found:** {Which dynamic tags are most commonly used}

**`<if>` Tag Usage:**
```xml
{Paste actual <if> example from codebase}
```

**`<where>` Tag Usage:**
```xml
{Paste actual <where> example from codebase}
```

**`<trim>` Tag Usage:**
```xml
{Paste actual <trim> example if used}
```

**`<foreach>` Tag Usage:**
```xml
{Paste actual <foreach> example from codebase}
```

**`<choose>/<when>/<otherwise>` Usage:**
```xml
{Paste actual example if used}
```

### SQL Fragment Reuse

**Pattern Found:** {Whether <sql> fragments are used for reuse}
```xml
{Paste actual <sql id=""> and <include refid=""> examples}
```

---

## Pagination Patterns

**Pattern Found:** {How pagination is implemented}

**Example:**
```xml
{Paste actual pagination example from codebase}
```

**Java Interface Signature:**
```java
{Paste actual method signature for paginated query}
```

---

## Java Mapper Interface Patterns

### Annotation Pattern
**Pattern Found:** {What annotations are consistently used}
```java
{Paste actual interface example with annotations}
```

### Method Naming Convention
**Pattern Found:** {Naming convention for mapper methods}

**Examples:**
```java
{Paste actual method signatures from codebase}
```

### Parameter Annotation Usage
**Pattern Found:** {How @Param is used}
```java
{Paste actual examples}
```

### Return Types
**Pattern Found:** {Common return types}
- Single object: {Type}
- Multiple objects: {List<Type> / Set<Type> / etc}
- Optional: {Is Optional<T> used?}
- Primitive counts: {int / long / Integer / Long}

---

## MyBatis Configuration

**Config File:** `{actual_config_file_path}`

### Settings
```xml
{Paste actual settings from config}
```

### Type Aliases
```xml
{Paste actual type aliases if defined}
```

### Plugins
```xml
{Paste actual plugins if configured}
```

---

## Common Issues and Anti-Patterns Found

### Potential SQL Injection Risks
{List any files using ${} instead of #{}}
```xml
{Paste examples if found - these should be flagged in reviews}
```

### Inconsistencies Found
- ⚠️ {Describe any inconsistencies between mappers}
- ⚠️ {Different pagination approaches}
- ⚠️ {Different dynamic SQL patterns}

---

## DO's and DON'Ts Based on This Codebase

### DO:
- ✓ {Pattern consistently followed}
- ✓ {Pattern consistently followed}
- ✓ Use `#{}` for parameter binding (prevents SQL injection)
- ✓ {Other patterns found}

### DON'T:
- ✗ Don't use `${}` unless absolutely necessary (SQL injection risk)
- ✗ {Anti-pattern found in codebase}
- ✗ {Anti-pattern found in codebase}

---

## References for PR Review

When reviewing MyBatis code, check:

1. **XML Mapper Files:**
   - [ ] Namespace matches Java interface: `{example_namespace}`
   - [ ] SQL IDs follow naming convention from {reference_file}
   - [ ] Parameters use `#{}` not `${}` (unless intentional)
   - [ ] ResultMaps follow pattern from {reference_file}
   - [ ] Dynamic SQL uses consistent patterns

2. **Java Mapper Interfaces:**
   - [ ] Annotations match pattern from {reference_file}
   - [ ] Method names follow convention
   - [ ] @Param used consistently for multiple parameters
   - [ ] Return types appropriate

3. **Common Mistakes to Flag:**
   - SQL injection via `${}`
   - Missing parameter types
   - Inefficient queries (N+1, missing indexes)
   - Inconsistent naming

**Example Reference Mappers (Good Patterns):**
- `{path_to_well_written_mapper_1}` - Good example of {what}
- `{path_to_well_written_mapper_2}` - Good example of {what}

</content>
</write_file>
```

---

## Phase 4: Analyze TypeScript/Angular Patterns

### Step 4.1: Find Angular Files

```bash
# Find components
find . -type f -name "*.component.ts" | head -20

# Find services
find . -type f -name "*.service.ts" | head -20

# Find modules
find . -type f -name "*.module.ts" | head -10

# Find models/interfaces
find . -type f -name "*.model.ts" -o -name "*.interface.ts" | head -20

# Find guards, interceptors, pipes
find . -type f -name "*.guard.ts" -o -name "*.interceptor.ts" -o -name "*.pipe.ts" | head -10
```

### Step 4.2: Analyze Component Patterns

Read 7-10 component files (mix of simple and complex):

```xml
<read_file>
<path>{first_component_path}</path>
</read_file>

<!-- Repeat for 7-10 components -->
```

**What to look for in Components:**
1. **Component decorator:**
   - Selector naming convention?
   - ChangeDetection strategy?
   - Standalone vs module-based?
2. **Class structure:**
   - Property declarations at top?
   - Constructor for dependency injection?
   - Lifecycle hooks - which are commonly used?
   - Method organization?
3. **Smart vs Dumb components:**
   - Are there presentational (dumb) components?
   - Are there container (smart) components?
   - How is the distinction made?
4. **Dependency injection:**
   - What's injected? Services? ActivatedRoute? Router?
   - Constructor injection pattern?
   - inject() function usage (Angular 14+)?
5. **State management:**
   - Component state in properties?
   - Signals usage (Angular 17+)?
   - Input/Output patterns?
6. **Template interaction:**
   - How are events handled?
   - Two-way binding patterns?
   - Async pipe usage?
7. **RxJS usage:**
   - Observable subscriptions - where and how?
   - Subscription management (unsubscribe patterns)?
   - Common operators used?
8. **Forms:**
   - Reactive forms? Template-driven?
   - FormGroup/FormControl patterns?
   - Validation approach?
9. **Error handling:**
   - How are errors displayed?
   - Error service usage?
10. **TypeScript patterns:**
    - Type annotations?
    - Interface usage?
    - Access modifiers (public/private/protected)?

### Step 4.3: Analyze Service Patterns

Read 5-7 service files:

```xml
<read_file>
<path>{first_service_path}</path>
</read_file>

<!-- Repeat for 5-7 services -->
```

**What to look for in Services:**
1. **Injectable decorator:**
   - providedIn: 'root'? Module-level?
2. **Purpose classification:**
   - Data services (API calls)?
   - State management services?
   - Utility services?
   - Facade services?
3. **HTTP patterns:**
   - HttpClient usage?
   - API endpoint organization?
   - Request/response typing?
   - Error handling?
4. **Observable patterns:**
   - BehaviorSubject/Subject usage?
   - Observable streams?
   - Operators commonly used?
5. **Caching:**
   - Any caching mechanisms?
6. **Error handling:**
   - Centralized error handling?
   - Error interceptors?

### Step 4.4: Analyze Module Patterns (if not standalone)

Read 3-5 module files:

```xml
<read_file>
<path>{first_module_path}</path>
</read_file>

<!-- Repeat for modules -->
```

**What to look for:**
1. Module organization structure
2. Shared modules?
3. Lazy loading patterns?
4. Import/Export patterns

### Step 4.5: Analyze Models and Interfaces

Read 5-7 model/interface files:

```xml
<read_file>
<path>{first_model_path}</path>
</read_file>

<!-- Repeat for models/interfaces -->
```

**What to look for:**
1. **Naming conventions:**
   - Interface naming (IUser vs User)?
   - Model vs Interface distinction?
2. **Structure:**
   - Properties only? Methods too?
   - Optional vs required properties?
3. **Type usage:**
   - Union types? Literal types?
   - Generics?

### Step 4.6: Check TypeScript Configuration

```xml
<read_file>
<path>tsconfig.json</path>
</read_file>

<read_file>
<path>tsconfig.app.json</path>
</read_file>
```

**What to look for:**
1. Strict mode settings
2. Path aliases
3. Target ES version

### Step 4.7: Check Angular Version and Configuration

```xml
<read_file>
<path>package.json</path>
</read_file>

<read_file>
<path>angular.json</path>
</read_file>
```

**Extract:**
1. Angular version
2. Key dependencies (RxJS version, etc.)
3. Project structure

### Step 4.8: Generate TypeScript/Angular Context File

```xml
<write_file>
<path>.cline/context/typescript-angular-patterns.md</path>
<content>
# TypeScript/Angular Patterns

**Last Updated:** {current_date}
**Angular Version:** {version_from_package_json}
**TypeScript Version:** {version_from_package_json}
**Analyzed Files:** {count} components, {count} services, {count} modules

---

## Project Structure

**Architecture:** {Standalone components / Module-based / Hybrid}

**Directory Structure:**
```
{Describe the actual directory structure you found}
src/
├── app/
│   ├── {actual_structure}
```

---

## Component Patterns

### Component Decorator Pattern
**Pattern Found:** {Describe common decorator pattern}

```typescript
{Paste actual component decorator from codebase}
```

### Class Structure Pattern
**Pattern Found:** {Describe how components are structured}

```typescript
{Paste actual component class structure example}
```

**Property Declaration Location:** {Top of class / Other}
**Constructor Pattern:** {What's typically in constructor}
**Lifecycle Hooks Used:** {ngOnInit, ngOnDestroy, etc - which are common}

### Smart vs Dumb Components

**Pattern Found:** {Whether this distinction exists}

**Smart (Container) Components:**
- {Describe characteristics}
- Example: `{actual_smart_component_path}`

**Dumb (Presentational) Components:**
- {Describe characteristics}
- Example: `{actual_dumb_component_path}`

### Dependency Injection

**Pattern Found:** {Constructor injection / inject() function}

```typescript
{Paste actual DI example from codebase}
```

**Commonly Injected:**
- {Service types commonly injected}
- {Other injectables}

### State Management in Components

**Pattern Found:** {How component state is managed}

```typescript
{Paste actual state management example}
```

**Signals Usage (Angular 17+):** {Yes/No - if yes, paste example}

### Input/Output Patterns

**@Input Pattern:**
```typescript
{Paste actual @Input examples from codebase}
```

**@Output Pattern:**
```typescript
{Paste actual @Output examples from codebase}
```

### RxJS Usage in Components

**Subscription Pattern Found:** {How subscriptions are managed}

```typescript
{Paste actual subscription example}
```

**Unsubscribe Pattern:** {takeUntil / Subscription / async pipe / other}
```typescript
{Paste actual unsubscribe pattern from codebase}
```

**Common Operators Used:**
- {operator1} - {paste example}
- {operator2} - {paste example}

### Form Handling

**Pattern Found:** {Reactive / Template-driven}

```typescript
{Paste actual form handling example from codebase}
```

**Validation Pattern:**
```typescript
{Paste validation example}
```

---

## Service Patterns

### Injectable Pattern
**Pattern Found:** {providedIn root / module-level}

```typescript
{Paste actual service decorator from codebase}
```

### Service Types Found

**Data Services (API calls):**
- Example: `{actual_data_service_path}`
```typescript
{Paste example method from data service}
```

**State Management Services:**
- Example: `{actual_state_service_path}`
```typescript
{Paste example state management pattern}
```

**Utility Services:**
- Example: `{actual_utility_service_path}`

### HTTP Patterns

**HttpClient Usage:**
```typescript
{Paste actual HTTP call example from codebase}
```

**API Endpoint Organization:** {How are endpoints structured}

**Request/Response Typing:**
```typescript
{Paste example of typed HTTP call}
```

**Error Handling in HTTP Calls:**
```typescript
{Paste actual error handling pattern}
```

### Observable Patterns

**BehaviorSubject/Subject Usage:**
```typescript
{Paste actual example if used}
```

**Observable Streams:**
```typescript
{Paste example of observable stream}
```

**Common Operators:**
- {operator1} - {usage pattern}
- {operator2} - {usage pattern}

---

## Module Patterns (if applicable)

**Module Organization:** {How modules are structured}

**Example Module:**
```typescript
{Paste actual module structure from codebase}
```

**Shared Modules:** {Yes/No - if yes, describe}

**Lazy Loading:** {Yes/No - if yes, paste example}

---

## Models and Interfaces

### Naming Convention
**Pattern Found:** {Interface vs Model naming}

**Examples:**
```typescript
{Paste actual interface/model examples}
```

### Structure Pattern
**Properties:** {Type annotations style}
**Optional Properties:** {How handled}
**Methods in Models:** {Yes/No - examples}

### Type Usage
```typescript
{Paste examples of union types, generics, etc if used}
```

---

## TypeScript Configuration

**Strict Mode:** {Enabled/Disabled}
**Key Settings:**
```json
{Paste relevant tsconfig settings}
```

**Path Aliases:**
```json
{Paste path aliases if configured}
```

---

## Common Utilities and Helpers

**Utility Files Found:**
- `{util_file_1}` - {what it does}
- `{util_file_2}` - {what it does}

**Helper Functions:**
```typescript
{Paste examples of commonly used helpers}
```

---

## Error Handling Patterns

### Component-Level Error Handling
```typescript
{Paste actual error handling example}
```

### Service-Level Error Handling
```typescript
{Paste actual service error handling}
```

### Global Error Handling
**Interceptor:** `{path_if_exists}`
```typescript
{Paste interceptor code if exists}
```

---

## DO's and DON'Ts Based on This Code