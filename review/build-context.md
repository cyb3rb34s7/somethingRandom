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

Confirm directories created:
```bash
ls -la .cline/
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

<!-- Repeat for 5-7 controllers from different modules if possible -->
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

```xml
<read_file>
<path>{config_class_path}</path>
</read_file>
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
<path>{mybatis_config_path_if_found}</path>
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
# Check for potential SQL injection risks (${} usage)
find . -type f -name "*.xml" -path "*/mapper/*" -exec grep -l '\${' {} \;
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

**Config File:** `{actual_config_file_path if found}`

### Settings
```xml
{Paste actual settings from config if found}
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

If modules are used, read 3-5 module files:

```xml
<read_file>
<path>{first_module_path}</path>
</read_file>
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

### Step 4.6: Check TypeScript and Angular Configuration

```xml
<read_file>
<path>tsconfig.json</path>
</read_file>

<read_file>
<path>package.json</path>
</read_file>
```

**What to extract:**

1. Angular version
2. TypeScript version
3. Key dependencies (RxJS version, etc.)
4. Strict mode settings
5. Path aliases

### Step 4.7: Generate TypeScript/Angular Context File

```xml
<write_file>
<path>.cline/context/typescript-angular-patterns.md</path>
<content>
# TypeScript/Angular Patterns

**Last Updated:** {current_date}
**Angular Version:** {version_from_package_json}
**TypeScript Version:** {version_from_package_json}
**Analyzed Files:** {count} components, {count} services

---

## Project Structure

**Architecture:** {Standalone components / Module-based / Hybrid}

**Directory Structure:**
```
{Describe the actual directory structure you found}
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
- Example: `{actual_state_service_path if found}`
```typescript
{Paste example state management pattern}
```

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

---

## Module Patterns (if applicable)

**Module Organization:** {How modules are structured}

**Example Module:**
```typescript
{Paste actual module structure from codebase if found}
```

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

## DO's and DON'Ts Based on This Codebase

### DO:
- ✓ {Pattern consistently followed}
- ✓ {Pattern consistently followed}

### DON'T:
- ✗ {Anti-pattern found}
- ✗ {Anti-pattern found}

### INCONSISTENCIES FOUND:
- ⚠️ {Describe any inconsistencies}

---

## References for PR Review

When reviewing TypeScript/Angular code, check:

1. **Components:**
   - [ ] Decorator pattern matches {reference_file}
   - [ ] DI pattern consistent
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
# Find potential null pointer issues in Java
grep -r "\.get(" --include="*.java" src/ 2>/dev/null | wc -l

# Find Optional usage
grep -r "Optional\.of\|Optional\.ofNullable" --include="*.java" src/ 2>/dev/null | wc -l

# Find potential SQL injection in MyBatis
find . -name "*.xml" -path "*/mapper/*" -exec grep -l '\${' {} \; 2>/dev/null

# Find console.log in TypeScript (should be removed in production)
grep -r "console\.log\|console\.error" --include="*.ts" src/ 2>/dev/null | wc -l

# Find subscriptions in components
grep -r "\.subscribe(" --include="*.component.ts" src/ 2>/dev/null | head -20

# Find @Transactional on controllers (usually wrong)
grep -r "@Transactional" --include="*Controller.java" src/ 2>/dev/null

# Find hardcoded URLs
grep -r "http://\|https://" --include="*.java" --include="*.ts" src/ 2>/dev/null | grep -v "example\|localhost" | head -20
```

### Step 5.2: Analyze Git History for Bug Fixes

```bash
# Find commits that fixed bugs
git log --all --grep="fix\|bug\|issue" --oneline --since="1 year ago" | head -30
```

Read 3-5 bug fix commits to understand what went wrong:

```bash
# Pick a few commit hashes and examine them
git show {commit_hash_1} | head -100
git show {commit_hash_2} | head -100
```

### Step 5.3: Look for TODOs and FIXMEs

```bash
# Find TODOs and FIXMEs
grep -r "TODO\|FIXME\|HACK\|XXX" --include="*.java" --include="*.ts" src/ 2>/dev/null | head -30
```

### Step 5.4: Check for Deprecated Code

```bash
# Find @Deprecated annotations
grep -r "@Deprecated" --include="*.java" src/ 2>/dev/null | head -20
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
   {Paste problematic code pattern if available from git show}
   ```

2. **Issue Type:** {e.g., Transaction Management}
   **Occurrence:** {describe}
   **Example Commit:** {commit_hash}
   **Root Cause:** {what caused it}
   **Prevention:** {how to avoid}

{Repeat for 3-5 issues found in git history}

---

## Java/Spring Boot Anti-Patterns

### Found in Codebase

1. **@Transactional on Controllers**
   **Files Found:** {list files if any from grep search}
   ```java
   {Paste example if found}
   ```
   **Why It's Wrong:** Transactions should be at service layer
   **Correct Pattern:** See service layer patterns in java-springboot-patterns.md

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
   {Paste example if found - empty catch blocks}
   ```
   **Why It's Wrong:** Makes debugging impossible
   **Correct Pattern:** {paste correct exception handling}

{Add more anti-patterns as found}

---

## MyBatis Anti-Patterns

### Found in Codebase

1. **SQL Injection Risk (${} usage)**
   **Files Found:** {count from grep search}
   {List specific files using ${}}
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
   **Why It's Wrong:** Performance issue - multiple queries in loop
   **Correct Pattern:** {paste correct pattern with joins}

3. **Missing Parameter Types**
   **Pattern Found:** {describe if found}
   **Why It's Wrong:** Can cause runtime errors
   **Correct Pattern:** {paste correct pattern}

---

## TypeScript/Angular Anti-Patterns

### Found in Codebase

1. **Memory Leaks from Subscriptions**
   **Occurrences Found:** {count from grep search}
   **Pattern Found:** Subscriptions without unsubscribe
   ```typescript
   {Paste problematic pattern}
   ```
   **Why It's Wrong:** Memory leaks
   **Correct Pattern:** {paste correct unsubscribe pattern from codebase}

2. **Console.log in Production Code**
   **Occurrences:** {count from grep}
   **Files with console.log:** {list some files}
   **Why It's Wrong:** Should be removed before production, can expose sensitive data
   **Correct Pattern:** Use proper logging service or remove

3. **Any Type Usage**
   **Pattern Found:** {search for : any in TypeScript files}
   ```typescript
   {Paste examples if found}
   ```
   **Why It's Wrong:** Defeats TypeScript's purpose, loses type safety
   **Correct Pattern:** Use proper typing

4. **Manual Subscription Instead of Async Pipe**
   **Pattern Found:** {manual subscription in templates}
   ```typescript
   {Paste problematic pattern}
   ```
   **Why It's Wrong:** Manual memory management needed, more boilerplate
   **Correct Pattern:** Use async pipe when possible

---

## Architecture Anti-Patterns

### Boundary Violations

1. **Controllers Accessing Repositories Directly**
   **Found:** {yes/no - list files if found}
   ```java
   {Paste example if found}
   ```
   **Why It's Wrong:** Breaks service layer pattern, mixes responsibilities
   **Correct Pattern:** Controllers → Services → Repositories

2. **Circular Dependencies**
   **Found:** {yes/no - describe if found}
   **Why It's Wrong:** Creates tight coupling, hard to test
   **Resolution:** {how it should be fixed}

3. **God Classes**
   **Found:** {yes/no - list large classes with line counts}
   **Examples:**
   - `{large_class_1}` - {line_count} lines
   - `{large_class_2}` - {line_count} lines
   **Why It's Wrong:** Violates Single Responsibility Principle
   **Resolution:** Break into smaller, focused classes

---

## Performance Anti-Patterns

### Found Issues

1. **N+1 Queries**
   **Locations:** {list if found in MyBatis mappers}
   **Impact:** Multiple database round-trips, slow performance
   **Solution:** Use joins or batch fetching

2. **Missing Indexes**
   **Queries Without Indexes:** {if determinable from SQL}
   **Impact:** Slow queries on large tables
   **Solution:** Add indexes on commonly queried fields

3. **Large Result Sets Without Pagination**
   **Found:** {yes/no - examples}
   **Impact:** Memory issues, slow API responses
   **Solution:** Always paginate large datasets

---

## Security Anti-Patterns

### Found Issues

1. **Hardcoded Credentials/URLs**
   **Occurrences:** {from grep search}
   ```java
   {Paste examples if found (redact actual credentials)}
   ```
   **Why It's Dangerous:** Security risk, credentials in version control
   **Correct Pattern:** Use configuration properties/environment variables

2. **Missing Input Validation**
   **Pattern Found:** {describe endpoints without validation}
   **Why It's Dangerous:** Can lead to SQL injection, XSS, data corruption
   **Correct Pattern:** Validate all user input with @Valid or custom validators

3. **SQL Injection Vulnerabilities**
   **Files:** {count from MyBatis ${} search}
   **Why It's Dangerous:** Database compromise, data theft
   **Correct Pattern:** Use #{} parameterization

---

## Code Smells Found

### Duplication

**Pattern Found:** {describe code duplication if found}
**Locations:**
- {file1} lines {X-Y} and {file2} lines {A-B} - {what's duplicated}
- {file3} and {file4} - {what's duplicated}

**Solution:** Extract to utility/helper class

### Long Methods

**Pattern Found:** {describe if found}
**Examples:**
- `{file}:{method}` - {line_count} lines
- `{file}:{method}` - {line_count} lines

**Solution:** Break into smaller, focused methods (aim for <50 lines)

### Magic Numbers/Strings

**Pattern Found:** {describe if found}
```java
{Paste examples - numbers/strings used without explanation}
```
**Solution:** Use constants or enums with descriptive names

---

## TODOs and Technical Debt

**Count:** {total TODOs found}

**High Priority TODOs:**
```
{Paste important TODOs that indicate incomplete features or known issues}
```

**Areas of Technical Debt:**
1. {area1} - {description}
2. {area2} - {description}
3. {area3} - {description}

---

## Deprecated Patterns Still in Use

**Found:** {yes/no}

**Deprecated Code:**
- `{file}` - uses deprecated {what}
- `{file}` - uses deprecated {what}

**Migration Path:** {describe how to update to new patterns}

---

## Checklist for PR Reviews

When reviewing PRs, watch out for:

### Critical Issues (Must Fix Before Merge)
- [ ] SQL injection via ${} in MyBatis
- [ ] Hardcoded credentials or sensitive data
- [ ] @Transactional on controllers
- [ ] Missing null/undefined checks in critical paths
- [ ] Unhandled exceptions that could crash application
- [ ] Security vulnerabilities

### High Priority Issues (Should Fix)
- [ ] Memory leaks from unmanaged subscriptions
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
- [ ] Inconsistent naming conventions

---

## Past Incidents to Remember

{If you found significant issues in git history}

### Incident 1: {Brief description from git log}
**Date:** {from git log}
**Commit:** {hash}
**What Went Wrong:** {describe the bug}
**Impact:** {user-facing impact if mentioned}
**How to Prevent:** {specific checks to add in PR reviews}

### Incident 2: {Brief description}
**Date:** {from git log}
**Commit:** {hash}
**What Went Wrong:** {describe}
**How to Prevent:** {specific checks}

{Add 2-3 significant incidents if found}

---

## Reference Examples

**Good Examples (Follow These):**
- `{file_path}` - Good example of {what pattern}
- `{file_path}` - Good example of {what pattern}

**Bad Examples (Don't Follow These):**
- `{file_path}` - Example of {what not to do}
- `{file_path}` - Example of {what not to do}

---

## Statistics

**Total Issues Found:**
- SQL Injection risks: {count}
- Console.log statements: {count}
- TODO/FIXME comments: {count}
- @Deprecated usage: {count}
- Potential NPE locations: {count}
- Unmanaged subscriptions: {count}

**Git History Analysis:**
- Bug fix commits analyzed: {count}
- Time period: {date range}
- Most common bug type: {type}

</content>
</write_file>
```

---

## Phase 6: Create Review Perspectives Guide

### Step 6.1: Generate Detailed Perspectives Definition

```xml
<write_file>
<path>.cline/context/review-perspectives.md</path>
<content>
# Review Perspectives - Detailed Guidelines

**Last Updated:** {current_date}

This document defines what each review perspective means in the context of OUR codebase and what specific things to check.

---

## Priority Order

1. ⚠️ **[Critical]** - Must fix before merge (security, data loss, breaking changes)
2. 🧠 **[Logical]** - Should fix before merge (logic errors, edge cases)
3. 🐛 **[Bug]** - Should fix before merge (potential runtime bugs)
4. 💡 **[Improvement]** - Good to fix (better ways we do things)
5. 🔧 **[Maintenance]** - Nice to fix (long-term maintainability)

---

## 🧠 [Logical] - TOP PRIORITY

### What to Check

Logic errors, algorithmic issues, edge cases, and correctness of implementation based on OUR patterns.

### Specific Checks for Java/Spring Boot

#### 1. Null/Optional Handling
- Are null checks appropriate based on our Optional usage?
- Reference: `java-springboot-patterns.md#optional-handling`
- **Check:** Does method return Optional? Is .isPresent() or .orElseThrow() used?

#### 2. Collection Operations
- Are loops, streams, and iterations correct?
- Off-by-one errors in array/list access?
- Empty collection handling?
- **Check:** Are there .get(index) calls without bounds checking?

#### 3. Conditional Logic
- Are if/else conditions correct and complete?
- Are all branches handled?
- Is the logic sound?
- **Check:** Complex boolean expressions - are they correct?

#### 4. Transaction Boundaries
- Is @Transactional placed correctly per our pattern?
- Are transaction propagations appropriate?
- **Check:** Should this be in a transaction? Is rollback handled?

### Specific Checks for MyBatis

#### 1. Query Logic
- Are WHERE clauses correct?
- Are JOINs appropriate and correct?
- Dynamic SQL logic sound?
- **Check:** Test query with edge cases (empty params, nulls)

#### 2. Parameter Handling
- Are all parameters bound correctly?
- How are null parameters handled?
- **Check:** What happens if parameter is null?

### Specific Checks for TypeScript/Angular

#### 1. Observable Logic
- Are RxJS operators used correctly?
- Is the stream logic sound?
- **Check:** Are operators in the right order? Are there race conditions?

#### 2. Type Safety
- Are type guards used where needed?
- Are all type assertions safe?
- **Check:** Could undefined/null slip through?

### How to Comment

```markdown
🧠 [Logical]
**File:** {filename}:{line}
**Issue:** {Specific logic error}
**Why:** Based on OUR pattern in {reference_file}, {explain why it's wrong}
**Example:** See how we handle this in {other_file}:{line}
**Fix:** {Specific suggestion with code example}
```

---

## 💡 [Improvement] - HIGH PRIORITY

### What to Check

Better ways to implement based on OUR existing codebase patterns. Not generic best practices, but specific to how WE do things.

### Specific Checks for Java/Spring Boot

#### 1. Using Existing Utilities
- Could this use our existing utility class?
- **Check:** Search codebase for similar functionality

#### 2. Consistent Response Patterns
- Is the controller returning responses like other controllers?
- **Check:** Compare with 2-3 similar controllers

#### 3. Code Reuse
- Is this duplicating code from existing files?
- **Check:** Search for similar method names/logic

### Specific Checks for MyBatis

#### 1. SQL Optimization
- Could this query be more efficient?
- Should this use our pagination pattern?
- **Check:** Compare with similar queries in codebase

#### 2. ResultMap Reuse
- Could this reuse an existing resultMap?
- **Check:** Search for similar entity mappings

### Specific Checks for TypeScript/Angular

#### 1. Using Existing Services
- Could this use our existing service?
- **Check:** Search for similar HTTP calls or logic

#### 2. Component Structure
- Should this be broken into smart/dumb components?
- Could this reuse existing component?
- **Check:** Look for similar UI patterns

### How to Comment

```markdown
💡 [Improvement]
**File:** {filename}:{line}
**Current:** {what they did}
**Better:** Use OUR pattern from {reference_file}:{line}
**Why:** {explain why our pattern is better in our context}
**Example Code:**
```java/typescript
{paste the better way from our codebase}
```
```

---

## 🔧 [Maintenance] - MEDIUM PRIORITY

### What to Check

Long-term maintainability, code clarity, and adherence to OUR conventions.

### Specific Checks

#### 1. Naming Conventions
- Do names follow OUR conventions?
- **Check:** Compare with similar classes/methods in codebase

#### 2. Code Organization
- Is code structured like similar files?
- Are methods in logical order?
- **Check:** Compare file structure with similar files

#### 3. Documentation
- For complex logic, is there inline explanation?
- Are method purposes clear?
- **Check:** Would a new developer understand this?

#### 4. Magic Numbers/Strings
- Should these be constants?
- **Check:** Search for repeated values

#### 5. Method Length
- Is this method too long?
- **Check:** Compare with typical method lengths in codebase

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

### Specific Checks for Java/Spring Boot

#### 1. Exception Handling
- Are exceptions handled per our pattern?
- Could this throw uncaught exceptions?
- **Check:** What exceptions can this throw? Are they handled?

#### 2. Null Pointer Exceptions
- Based on our data flow, could this be null?
- Is Optional handling correct?
- **Check:** Trace variable origins - could any be null?

#### 3. Resource Leaks
- Are resources properly closed?
- Is try-with-resources used?
- **Check:** Files, connections, streams - all closed?

### Specific Checks for MyBatis

#### 1. SQL Errors
- Could this query fail with certain data?
- Division by zero? Null in aggregate functions?
- **Check:** Test query mentally with edge cases

#### 2. Parameter Binding Issues
- Could parameter be null causing SQL error?
- Is ${} used (SQL injection)?
- **Check:** Reference anti-patterns.md for SQL injection patterns

### Specific Checks for TypeScript/Angular

#### 1. Undefined/Null Errors
- Could properties be undefined?
- Is optional chaining needed?
- **Check:** Trace data origins - could be undefined?

#### 2. Subscription Leaks
- Is subscription properly unsubscribed?
- **Check:** Compare with our subscription management pattern

#### 3. Race Conditions
- Could async operations cause issues?
- Is loading state handled?
- **Check:** What if multiple calls happen simultaneously?

### How to Comment

```markdown
🐛 [Bug]
**File:** {filename}:{line}
**Potential Bug:** {describe the bug}
**Scenario:** {when/how it could occur in OUR environment}
**Past Incident:** {reference to similar bug from anti-patterns.md if exists}
**Fix:** {specific fix based on our patterns}
**Reference:** See correct pattern in {file}:{line}
```

---

## ⚠️ [Critical] - HIGHEST PRIORITY

### What to Check

Security, data loss, breaking changes, severe performance issues.

### Security Checks

#### 1. SQL Injection
- Any ${} in MyBatis?
- Dynamic query construction?
- **Must Check:** Every MyBatis XML file changed

#### 2. Input Validation
- Is user input validated?
- XSS prevention in place?
- **Must Check:** All controller endpoints receiving user data

#### 3. Sensitive Data
- Is sensitive data logged?
- Are credentials hardcoded?
- **Must Check:** All logging statements, all string literals

### Data Loss Checks

#### 1. Delete Operations
- Is deletion safe?
- Should this be soft delete per our pattern?
- **Must Check:** All DELETE operations

#### 2. Update Without Where Clause
- Could this update wrong records?
- Is WHERE clause always present?
- **Must Check:** All UPDATE operations in MyBatis

### Performance Checks

#### 1. N+1 Queries
- Could this cause N+1 problem?
- **Must Check:** Loops with database calls inside

#### 2. Memory Issues
- Loading large datasets without pagination?
- **Must Check:** Queries without LIMIT

### How to Comment

```markdown
⚠️ [Critical]
**File:** {filename}:{line}
**Critical Issue:** {describe the critical issue}
**Impact:** {explain potential damage - security/data loss/performance}
**Similar Past Incident:** {reference if applicable from anti-patterns.md}
**Must Fix Before Merge:** {specific fix required}
**Reference:** {security/safety pattern from our codebase}
```

---

## Comment Template Summary

### General Structure

```markdown
{emoji} [{Perspective}]
**File:** {filename}:{line}
**Issue/Observation:** {specific description}
**In OUR Codebase:** {how we typically handle this}
**Reference:** {specific file/pattern from our codebase}
**Suggestion/Fix:** {actionable recommendation}
```

### Tone Guidelines

- **Be specific**, not generic
- **Always reference OUR codebase**
- **Be constructive** and educational
- **Assume good intent**
- **Frame as learning** opportunity
- **Use "we" language** (not "you should")

---

## Example Full Review Comment

```markdown
## PR Review: Add User Profile Update Feature

Thanks @username for this PR! I've reviewed the changes against our codebase patterns.

### 🧠 [Logical] Issues

**File:** UserService.java:45
**Issue:** The method getUserProfile() could return null, but line 67 calls .getName() without null check
**In OUR Codebase:** We use Optional<User> for user lookups (see UserRepository.findById)
**Past Bug:** Similar NPE occurred in ProfileService (see anti-patterns.md - Incident #3)
**Fix:** Change return type to Optional<User> or add null check
**Reference:** See UserAuthService.java:34 for our standard pattern:
```java
userRepository.findById(id)
    .orElseThrow(() -> new UserNotFoundException(id));
```

### 💡 [Improvement] Suggestions

**File:** UserController.java:23
**Current:** Using ResponseEntity<User> directly
**Better:** Use our ApiResponse<User> wrapper like other controllers
**Reference:** See ProductController.java:45 for standard response pattern
**Why:** Provides consistent error handling and metadata across all endpoints
**Example:**
```java
return ResponseEntity.ok(ApiResponse.success(user));
```

### ✅ What I Liked

- Good test coverage for the new feature
- Clear method naming following our conventions

### Recommendation

Request changes - please address the logical issue in UserService.java before merge. The improvements are optional but would help maintain consistency.
```

</content>
</write_file>
```

---

## Phase 7: Create Architecture Documentation Template

### Step 7.1: Analyze System Architecture

```bash
# Find main application class
find . -name "*Application.java" -o -name "Main.java" | head -5

# Find configuration files
find . -name "application.properties" -o -name "application.yml" -o -name "application.yaml" | head -10

# Understand module structure
ls -la src/main/java/ 2>/dev/null || ls -la src/
```

Read application configuration:

```xml
<read_file>
<path>{path_to_application_yml_or_properties}</path>
</read_file>

<read_file>
<path>{path_to_main_application_class}</path>
</read_file>
```

### Step 7.2: Generate Architecture Documentation

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

**Purpose:** {Describe based on package structure and code analysis}

**Main Modules Found:**
{List main packages/modules discovered}

---

## Technical Stack

### Backend
- **Language:** Java {version}
- **Framework:** Spring Boot {version}
- **ORM:** MyBatis {version}
- **Database:** {from config}
- **Build Tool:** {Maven/Gradle}

### Frontend
- **Language:** TypeScript {version}
- **Framework:** Angular {version}
- **State Management:** {what you found}
- **UI Library:** {if any found}

### Infrastructure
- **Server Port:** {from config}
- **Profiles:** {list profiles from application-{profile}.yml files}

---

## Module Structure

**Java Package Structure:**
```
{Paste actual package structure}
com.{company}.{app}/
├── controller/
├── service/
├── repository/
├── model/
├── dto/
└── config/
```

**Angular Module Structure:**
```
{Paste actual src structure}
src/
├── app/
│   ├── components/
│   ├── services/
│   └── models/
```

---

## Data Flow

**Standard Request Flow:**

```
{Describe the actual flow you observed}

HTTP Request
→ Controller (validates, delegates)
→ Service (business logic, transaction boundary)
→ Repository (data access)
→ MyBatis Mapper (SQL execution)
→ Database
← Response (reverse flow)
```

**Example Flow from Actual Code:**
```
{Pick one actual flow and describe it}
Example: User Login
AuthController.login()
→ AuthService.authenticate()
→ UserRepository.findByUsername()
→ MyBatis UserMapper.selectByUsername
→ Database SELECT query
```

---

## API Design

**Base URL:** {from config}
**API Pattern:** {REST / Other}

**Endpoint Structure:**
{Describe actual endpoint patterns}
```
{Paste examples of actual endpoints from controllers}
```

**Response Format:**
{Describe actual response format}
```json
{Paste example response structure from code}
```

---

## Database Design

**Database:** {from config}
**Connection Pool:** {if found in config}

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

---

## Configuration Management

**Config Files:**
- `{path to application.yml/properties}`
- `{path to other configs}`

**Profiles Found:**
{List profiles}
- {profile1}
- {profile2}

---

## Error Handling

**Global Exception Handler:** `{path if found}`

**Error Response Format:**
```json
{Paste actual error response structure}
```

---

## Important Architectural Rules

Based on code analysis:

1. **Layered Architecture**
   - Controllers don't access Repositories directly
   - Services contain business logic
   - Transactions at service layer

2. **DTO Usage**
   - {Where DTOs are used vs entities}

3. **{Other architectural rules discovered}**

---

## References for PR Review

**Key Files:**
- **Controller Example:** `{path}`
- **Service Example:** `{path}`
- **Repository Example:** `{path}`
- **Configuration:** `{path}`

</content>
</write_file>
```

---

## Phase 8: Validate and Create Summary

### Step 8.1: Verify All Files Created

```bash
echo "Checking created files..."
ls -la .cline/context/
```

Expected files:
- architecture.md
- java-springboot-patterns.md
- mybatis-patterns.md
- typescript-angular-patterns.md
- anti-patterns.md
- review-perspectives.md

### Step 8.2: Generate README

```xml
<write_file>
<path>.cline/context/README.md</path>
<content>
# Codebase Context Documentation

**Generated:** {current_date}
**Purpose:** Context files for automated PR reviews

---

## Files Overview

### 1. architecture.md
System architecture, modules, data flow

### 2. java-springboot-patterns.md
Java Spring Boot coding patterns
**Analyzed:** {count} files

### 3. mybatis-patterns.md
MyBatis mapper patterns and SQL conventions
**Analyzed:** {count} files

### 4. typescript-angular-patterns.md
TypeScript and Angular coding patterns
**Analyzed:** {count} files

### 5. anti-patterns.md
Known issues, bugs, and things to avoid
**Bug commits analyzed:** {count}

### 6. review-perspectives.md
Detailed guidelines for each review perspective

---

## Usage

### For PR Reviews
```
/review-pr.md {PR_NUMBER}
```

### Updating Context
Re-run this workflow:
```
/build-context.md
```

---

## Statistics

**Codebase Analysis:**
- Controllers: {count}
- Services: {count}
- Repositories: {count}
- Components: {count}
- MyBatis Mappers: {count}

**Issues Found:**
- SQL Injection risks: {count}
- Console.log statements: {count}
- TODOs: {count}

</content>
</write_file>
```

### Step 8.3: Present Final Summary

```xml
<ask_followup_question>
<question>
✅ **Context Generation Complete!**

I've successfully analyzed your codebase and generated 6 comprehensive context files.

## Files Created:

1. **.cline/context/architecture.md** - System overview and data flow
2. **.cline/context/java-springboot-patterns.md** - {X} controllers, {X} services analyzed
3. **.cline/context/mybatis-patterns.md** - {X} XML mappers, {X} Java interfaces analyzed
4. **.cline/context/typescript-angular-patterns.md** - {X} components, {X} services analyzed
5. **.cline/context/anti-patterns.md** - {X} bug commits analyzed, {X} issues found
6. **.cline/context/review-perspectives.md** - Detailed review guidelines
7. **.cline/context/README.md** - Documentation overview

## Key Findings:

### Patterns Discovered:
- {Summarize key patterns found}
- {Consistency level}

### Issues Identified:
- SQL Injection risks: {count}
- Console.log statements: {count}
- Potential bugs from git history: {count}
- TODOs/Technical debt: {count}

### Inconsistencies:
- {Describe any major inconsistencies}

## Statistics:

**Total Files Analyzed:** {total_count}
- Java files: {count}
- MyBatis mappers: {count}
- TypeScript files: {count}
- Git commits: {count}

## Next Steps:

The context files are ready! You can now:
1. Review the generated files for accuracy
2. Test the PR review workflow with `/review-pr.md {PR_NUMBER}`
3. Refine specific patterns if needed

Would you like me to:
- Review specific sections in detail
- Test the PR review workflow now
- Add more detail to certain areas
- Explain any findings

</question>
<options>["Review specific sections", "Test PR review workflow", "Explain findings", "Looks good!"]</options>
</ask_followup_question>
```

---

## Workflow Execution Notes

### Important Reminders:

**1. Real Data Only**
- Never invent patterns
- Only document what you ACTUALLY see
- Use real file paths and code snippets
- Mark uncertain patterns as "Needs Verification"

**2. Be Thorough**
- Read multiple examples (5-7 per category minimum)
- Look for both patterns AND inconsistencies
- Document variations between modules
- Note old vs new patterns

**3. Quantify Everything**
- Count files analyzed
- Note percentages (e.g., "80% of controllers follow pattern X")
- Provide statistics in summaries

**4. Real Examples Required**
- Copy actual code snippets (not pseudo-code)
- Use exact file paths
- Reference actual git commits for bugs
- Include line numbers where relevant

**5. Handle Errors Gracefully**
- If patterns unclear, read more examples
- If files missing, search more broadly
- If unsure, mark for manual review
- Document what you couldn't determine

### Time Estimate:
- This workflow takes **10-20 minutes** to complete
- Reads 50+ files across codebase
- Analyzes git history
- Generates 6 comprehensive documentation files

### Success Criteria:
✅ All 6 context files created
✅ Real code examples in every file
✅ File paths reference actual codebase files
✅ Patterns backed by multiple examples
✅ Inconsistencies documented
✅ Statistics provided (file counts, issue counts)
✅ Anti-patterns linked to git history
✅ README generated

---

## Error Handling

### If Commands Fail:

**"find: No such file or directory"**
```bash
# Try broader search
find . -name "*.java" 2>/dev/null | head -20
```

**"grep: No matches found"**
- Document as "Pattern not found in codebase"
- Continue with other checks

**"Can't determine pattern"**
- Read 2-3 more examples
- If still unclear, mark as "Pattern varies - manual review needed"
- Document the variations you see

**"Files too large to read"**
- Read key sections (class declaration, key methods)
- Use grep to find specific patterns
- Focus on pattern recognition, not complete reading

### If Patterns are Inconsistent:

Document both patterns:
```markdown
### Pattern Inconsistency Found

**Pattern A (60% of files):**
{describe and give examples}

**Pattern B (40% of files):**
{describe and give examples}

**Recommendation for PR Review:**
Prefer Pattern A as it's more common, but both are acceptable until standardization.
```

---

## Post-Generation Steps

After workflow completes:

1. **User Reviews Generated Files**
   - Check accuracy of patterns
   - Verify file paths are correct
   - Confirm examples make sense

2. **User Tests PR Review**
   - Run `/review-pr.md` on sample PR
   - Check quality of feedback
   - Verify references work

3. **Iterate and Refine**
   - Update patterns based on feedback
   - Add missing patterns
   - Correct misunderstandings

4. **Keep Updated**
   - Re-run periodically (monthly/quarterly)
   - Update manually as patterns evolve
   - Add new anti-patterns as discovered

---

## Workflow Complete

This workflow will produce comprehensive, codebase-specific context documentation that enables the PR review workflow to provide intelligent, actionable feedback based on YOUR actual coding patterns, not generic best practices.

**Result:** 6 detailed markdown files totaling 1000+ lines of codebase-specific documentation, ready for use with the PR review workflow.