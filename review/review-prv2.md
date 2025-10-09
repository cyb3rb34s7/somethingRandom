# PR Review Workflow - Codebase-Specific Perspective Analysis

You are conducting a comprehensive code review for a Pull Request. This review must be **specific to our codebase patterns**, not generic advice.

**CRITICAL:** Every comment MUST reference actual files, patterns, or examples from OUR codebase. Never give generic advice.

---

## Prerequisites Check

Before starting, verify:
- [ ] You have access to `gh` CLI (already authenticated)
- [ ] You are in the correct repository directory
- [ ] Context files exist in `.cline/context/`

If context files are missing, run `/build-context.md` first.

---

## STEP 1: Get PR Number from User

Ask the user which PR to review:

```xml
<ask_followup_question>
<question>Which PR number should I review?</question>
</ask_followup_question>
```

Wait for user response with PR number (e.g., "456" or "PR #456").

Extract the number and proceed with that PR.

---

## STEP 2: Fetch PR Information

Execute these commands to gather PR data:

```bash
# Get PR metadata
gh pr view {PR_NUMBER} --json title,body,author,comments,labels,additions,deletions

# Get the full diff
gh pr diff {PR_NUMBER}

# Get list of changed files
gh pr view {PR_NUMBER} --json files
```

**Action:** Read and understand:
- What is the PR trying to accomplish? (from title and body)
- What files are being changed?
- How large is the change? (additions/deletions)
- Are there any existing comments to consider?

---

## STEP 3: Load ALL Context Documentation

Read every context file to understand OUR patterns. This is CRITICAL - do not skip any file.

```xml
<read_file>
<path>.cline/context/architecture.md</path>
</read_file>

<read_file>
<path>.cline/context/java-springboot-patterns.md</path>
</read_file>

<read_file>
<path>.cline/context/mybatis-patterns.md</path>
</read_file>

<read_file>
<path>.cline/context/typescript-angular-patterns.md</path>
</read_file>

<read_file>
<path>.cline/context/anti-patterns.md</path>
</read_file>

<read_file>
<path>.cline/context/review-perspectives.md</path>
</read_file>
```

**Action:** Internalize these patterns. They define:
- HOW we write code
- WHAT patterns to follow
- WHAT mistakes to avoid
- WHAT to check in reviews

---

## STEP 4: Analyze Changed Files with Context

For EACH changed file, read it completely to understand the changes in context:

```xml
<read_file>
<path>{path_to_changed_file_1}</path>
</read_file>

<read_file>
<path>{path_to_changed_file_2}</path>
</read_file>

<!-- Repeat for ALL changed files -->
```

**For complex changes, also read related files:**

### If Java Controller changed:
```xml
<read_file>
<path>{related_service_file}</path>
</read_file>
```

### If Service changed:
```xml
<read_file>
<path>{related_repository_file}</path>
</read_file>
```

### If MyBatis XML changed:
```xml
<read_file>
<path>{corresponding_java_mapper_interface}</path>
</read_file>
```

### If Angular Component changed:
```xml
<read_file>
<path>{related_service_file}</path>
</read_file>
```

**Use search_files to find similar implementations:**

```xml
<search_files>
<path>src/</path>
<regex>{similar_method_name_or_pattern}</regex>
<file_pattern>*.java</file_pattern>
</search_files>
```

---

## STEP 5: Perform Perspective-Based Analysis

Now analyze the PR changes against OUR codebase patterns. Work through EACH perspective systematically.

**IMPORTANT:** Only report issues you actually find. Don't invent issues. If a perspective has no issues, say so.

### 🧠 [Logical] Analysis - TOP PRIORITY

Reference: `.cline/context/review-perspectives.md` - Logical section

**For Java/Spring Boot changes, check:**
1. **Null/Optional handling** - Compare with our Optional patterns in `java-springboot-patterns.md`
2. **Collection operations** - Are loops/streams correct? Off-by-one errors?
3. **Conditional logic** - Are all branches handled?
4. **Transaction boundaries** - Is @Transactional used correctly per our pattern?

**For MyBatis changes, check:**
1. **Query logic** - Are WHERE clauses, JOINs correct?
2. **Dynamic SQL** - Is the logic sound? Compare with examples in `mybatis-patterns.md`
3. **Parameter handling** - What if parameters are null?

**For TypeScript/Angular changes, check:**
1. **Observable logic** - Are RxJS operators correct? Compare with our patterns
2. **Type safety** - Could undefined/null slip through?
3. **Form logic** - Are all states handled?

**Record findings with:**
- Specific line numbers
- What's wrong and why (based on OUR patterns)
- Reference to similar code in our codebase
- Concrete fix suggestion

---

### 💡 [Improvement] Analysis - HIGH PRIORITY

Reference: `.cline/context/review-perspectives.md` - Improvement section

**Question for each change:** "Is there a BETTER way we already do this in OUR codebase?"

**For Java/Spring Boot:**
1. **Could this use existing utility classes?** (Check `java-springboot-patterns.md` - Common Utilities section)
2. **Does response format match other controllers?** (Compare with example controllers in patterns file)
3. **Is this duplicating code?** (Search for similar implementations)
4. **Does exception handling match our pattern?** (Check exception handling section)

**For MyBatis:**
1. **Could query be more efficient?** (Compare with similar queries in `mybatis-patterns.md`)
2. **Should this use our pagination pattern?** (Check pagination section)
3. **Could this reuse existing resultMap?** (Search for similar mappings)

**For TypeScript/Angular:**
1. **Could this use existing service?** (Check `typescript-angular-patterns.md` - Services section)
2. **Should this follow our component structure?** (Compare with example components)
3. **Does observable pattern match ours?** (Check RxJS patterns section)

**For each improvement, provide:**
- What they currently did
- The better way from OUR codebase (with file reference)
- Why our way is better in our context
- Code example from our codebase

---

### 🔧 [Maintenance] Analysis - MEDIUM PRIORITY

Reference: `.cline/context/review-perspectives.md` - Maintenance section

**Check:**
1. **Naming conventions** - Compare with our conventions in pattern files
2. **Code organization** - Is structure similar to related files?
3. **Documentation** - Is complex logic explained?
4. **Magic numbers/strings** - Should these be constants? (Check our constant patterns)
5. **Method length** - Compare with typical method lengths in our codebase
6. **Architectural consistency** - Does this respect module boundaries from `architecture.md`?

---

### 🐛 [Bug] Analysis - HIGH PRIORITY

Reference: `.cline/context/review-perspectives.md` - Bug section
Reference: `.cline/context/anti-patterns.md` - Past bugs and issues

**CRITICAL: Check against past bugs in anti-patterns.md**

**For Java/Spring Boot:**
1. **Exception handling** - Could uncaught exceptions occur? (Check our exception patterns)
2. **NPE potential** - Could this be null? (Check past NPE incidents in anti-patterns.md)
3. **Transaction rollback** - Is rollback handled correctly?
4. **Resource leaks** - Are resources closed?

**For MyBatis:**
1. **SQL errors** - Could query fail with certain data?
2. **${} usage** - SQL INJECTION RISK! (Check anti-patterns.md)
3. **Type mismatches** - Java types match database types?

**For TypeScript/Angular:**
1. **Undefined errors** - Could properties be undefined?
2. **Subscription leaks** - Is unsubscribe handled? (Check our subscription patterns)
3. **Race conditions** - Are async operations safe?

**For each bug, reference:**
- Similar past incidents from anti-patterns.md if exists
- How we prevent this elsewhere in codebase
- Specific scenario where bug would occur

---

### ⚠️ [Critical] Analysis - HIGHEST PRIORITY

Reference: `.cline/context/review-perspectives.md` - Critical section
Reference: `.cline/context/anti-patterns.md` - Security and critical issues

**MUST CHECK (Non-negotiable):**

**Security:**
1. **SQL Injection** - ANY ${} in MyBatis XML? (Check EVERY changed mapper)
2. **Input validation** - Is user input validated per our pattern?
3. **Sensitive data** - Is sensitive data logged or exposed?
4. **Hardcoded credentials** - Any credentials in code?

**Data Loss:**
1. **Delete operations** - Is deletion safe? Should be soft delete?
2. **Update without WHERE** - Could this update wrong records?
3. **Transaction issues** - Could partial data be committed?

**Performance:**
1. **N+1 queries** - Loops with DB calls inside? (Check anti-patterns.md examples)
2. **Missing pagination** - Large datasets without pagination?
3. **Infinite loops** - Could loops run forever?

**Breaking Changes:**
1. **API changes** - Does this break existing contracts?
2. **Database schema** - Are migrations included?

**If any critical issue found, this is a MUST FIX before merge.**

---

## STEP 6: Structure Your Review

Create a comprehensive review following this EXACT structure:

```markdown
## PR Review: {PR_TITLE}

Thanks @{author_username} for this PR!

### Summary
{2-3 sentences explaining what this PR does - your understanding}

---

### ⚠️ [Critical] Issues

{ONLY include this section if critical issues found}

**File:** `{filename}`:{line}
**Critical Issue:** {specific issue}
**Impact:** {security/data loss/performance impact}
**Reference:** {similar issue from anti-patterns.md or security pattern}
**Must Fix:** {specific required fix}
**Example from our codebase:**
```{language}
{paste correct pattern from our codebase}
```

{Repeat for each critical issue}

---

### 🧠 [Logical] Issues

{ONLY include if logical issues found, otherwise write "✅ No logical issues found"}

**File:** `{filename}`:{line}
**Issue:** {specific logic error}
**Why this is wrong:** Based on our pattern in `{reference_file}`, {explain}
**Past incident:** {reference to similar bug from anti-patterns.md if exists}
**Fix:**
```{language}
{show correct implementation}
```
**Reference:** See `{our_file}`:{line} for how we handle this

{Repeat for each logical issue}

---

### 🐛 [Bug] Potential Bugs

{ONLY include if bugs found, otherwise write "✅ No potential bugs found"}

**File:** `{filename}`:{line}
**Potential Bug:** {describe bug}
**Scenario:** {when/how this could fail in OUR environment}
**Past incident:** {reference from anti-patterns.md if similar bug occurred}
**Fix:** {specific fix based on our patterns}
**Reference:** Correct pattern in `{our_file}`:{line}

{Repeat for each bug}

---

### 💡 [Improvement] Suggestions

{ONLY include if improvements found, otherwise write "✅ Code follows our patterns well"}

**File:** `{filename}`:{line}
**Current approach:** {what they did}
**Better approach:** Use our pattern from `{reference_file}`
**Why:** {explain why our pattern is better in our context}
**Example from our codebase:**
```{language}
{paste the better way from our actual codebase}
```

{Repeat for each improvement}

---

### 🔧 [Maintenance] Concerns

{ONLY include if maintenance issues found, otherwise write "✅ Maintenance looks good"}

**File:** `{filename}`:{line}
**Concern:** {maintenance issue}
**Our convention:** {describe our convention from patterns}
**Reference:** `{example_file}` does this correctly
**Suggestion:** {specific suggestion}

{Repeat for each maintenance concern}

---

### ✅ What I Liked

{Mention 1-3 positive things if applicable:}
- Good test coverage
- Clear naming following our conventions
- Proper error handling
- {etc.}

---

### Recommendation

{Choose ONE of these based on findings:}

**If Critical or multiple Logical/Bug issues:**
❌ **Request Changes** - Please address the {critical/logical/bug} issues before merge.

**If only Improvements/Maintenance:**
💬 **Comment** - The code works correctly. The suggestions above would improve consistency with our codebase but are optional.

**If no issues:**
✅ **Approve** - Code looks good and follows our patterns!

---

### Summary Stats
- Critical issues: {count}
- Logical issues: {count}
- Potential bugs: {count}
- Improvements suggested: {count}
- Maintenance concerns: {count}
```

---

## STEP 7: Validate Your Review

Before presenting to user, self-check:

**Quality Checks:**
- [ ] Every issue references a SPECIFIC line number
- [ ] Every issue references OUR codebase patterns (file path provided)
- [ ] Every issue includes example from OUR codebase (not generic advice)
- [ ] No generic advice like "follow best practices"
- [ ] Past incidents from anti-patterns.md referenced where applicable
- [ ] Tone is friendly and constructive ("we" language, not "you should")
- [ ] Code examples are from OUR actual codebase
- [ ] Only reported issues that ACTUALLY exist (didn't invent issues)

**Accuracy Checks:**
- [ ] File paths are correct
- [ ] Line numbers are accurate
- [ ] Referenced patterns actually exist in context files
- [ ] Similar code examples are actually similar

---

## STEP 8: Present Review to User

Show the user your complete review:

```xml
<ask_followup_question>
<question>I've completed the codebase-specific review of PR #{PR_NUMBER}. Here's my analysis:

{Paste your COMPLETE structured review here}

---

**Next Steps:**

Would you like me to:
1. **Post this review to GitHub** (will use appropriate approve/comment/request-changes based on findings)
2. **Revise specific sections** (which section?)
3. **Add more detail** to certain perspectives
4. **Don't post** - you'll handle it manually

What would you like to do?
</question>
<options>["Post to GitHub", "Revise sections", "Add more detail", "Don't post"]</options>
</ask_followup_question>
```

---

## STEP 9: Post Review to GitHub

Based on user's choice, post the review with appropriate status:

### If Critical or Multiple Logical/Bug Issues: REQUEST CHANGES

```bash
cat << 'EOF' | gh pr review {PR_NUMBER} --request-changes --body-file -
{Your complete structured review}
EOF
```

### If Only Improvements/Maintenance: ADD COMMENT

```bash
cat << 'EOF' | gh pr review {PR_NUMBER} --comment --body-file -
{Your complete structured review}
EOF
```

### If No Issues: APPROVE

```bash
cat << 'EOF' | gh pr review {PR_NUMBER} --approve --body-file -
{Your complete structured review}
EOF
```

**Note:** Use heredoc with 'EOF' (quoted) to preserve all formatting and special characters.

---

## STEP 10: Confirm Completion

After posting successfully:

```
✅ Review posted to PR #{PR_NUMBER}

**Summary:**
- Status: {Approved / Commented / Requested Changes}
- Critical issues: {count}
- Logical issues: {count}
- Potential bugs: {count}
- Improvements: {count}
- Maintenance concerns: {count}

The review has been posted to GitHub. The PR author will be notified.

{If request-changes}: The PR cannot be merged until the requested changes are addressed.
{If approved}: The PR can now be merged (subject to other required approvals).
{If comment}: The PR can be merged, but the suggestions should be considered.
```

---

## Important Guidelines

### DO:
✅ Reference ACTUAL files from our codebase
✅ Compare with EXISTING implementations in our code
✅ Point to SPECIFIC patterns in context files
✅ Reference past incidents from anti-patterns.md
✅ Use "we" language ("In our codebase, we...")
✅ Be constructive and educational
✅ Provide code examples from OUR codebase
✅ Only report issues that ACTUALLY exist

### DON'T:
❌ Give generic advice ("follow best practices")
❌ Invent patterns that don't exist
❌ Reference files that don't exist
❌ Copy/paste from context files without adaptation
❌ Use "you should" language
❌ Ignore the context files
❌ Skip reading changed files completely
❌ Invent issues when code is fine

### Tone:
- Friendly and collaborative
- Educational, not judgmental
- "We" not "you"
- Assume good intent
- Frame as learning opportunity
- Praise good patterns

---

## Error Handling

### If gh commands fail:
```bash
# Verify PR exists
gh pr view {PR_NUMBER} --json number

# If unauthorized
echo "Error: Not authenticated with GitHub. Please run: gh auth login"

# If PR not found
echo "Error: PR #{PR_NUMBER} not found in this repository"
```

### If context files missing:
```
⚠️ **Context files not found!**

I cannot perform a codebase-specific review without context files.

Please run `/build-context.md` first to generate:
- architecture.md
- java-springboot-patterns.md
- mybatis-patterns.md
- typescript-angular-patterns.md
- anti-patterns.md
- review-perspectives.md

After context files are generated, run this workflow again.
```

### If changed files cannot be read:
```bash
# Try alternative path
find . -name "{filename}" | head -1
```

---

## Tips for High-Quality Reviews

1. **Read context files thoroughly** - They contain OUR specific patterns
2. **Compare side-by-side** - Open similar files and compare
3. **Search for examples** - Use search_files to find similar implementations
4. **Check anti-patterns** - Always reference past bugs
5. **Be specific** - Line numbers, file paths, exact issues
6. **Provide solutions** - Not just problems, but how we solve them
7. **Keep learning** - Note patterns to add to context files

---

## Workflow Complete

This workflow provides comprehensive, codebase-specific PR reviews that:
- ✅ Reference YOUR actual code patterns
- ✅ Compare with YOUR existing implementations
- ✅ Learn from YOUR past bugs
- ✅ Follow YOUR architectural decisions
- ✅ Maintain YOUR code quality standards

**Not generic best practices, but YOUR best practices.**