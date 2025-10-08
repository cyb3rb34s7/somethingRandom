# PR Review Workflow - Codebase-Specific Perspective Analysis

You are conducting a comprehensive code review for a Pull Request. This review must be **specific to our codebase patterns**, not generic advice.

## Prerequisites
- You have access to `gh` CLI (already authenticated)
- You are in the repository directory
- The user will provide a PR number

## Review Priorities (in order)
1. **[Logical]** - Logic errors, edge cases, algorithmic issues
2. **[Improvement]** - Better approaches specific to OUR codebase
3. **[Maintenance]** - Long-term maintainability, clarity, documentation
4. **[Bug]** - Potential runtime bugs based on OUR patterns
5. **[Critical]** - Security, data loss, breaking changes, performance issues

---

## STEP 1: Gather PR Information

Execute these commands to collect PR data:

```bash
# Get PR metadata
gh pr view {PR_NUMBER} --json title,body,author,comments,labels

# Get the full diff
gh pr diff {PR_NUMBER}

# Get list of changed files with stats
gh pr view {PR_NUMBER} --json files
```

**Action:** Review the PR title, description, and understand the intent of the changes.

---

## STEP 2: Load Codebase Context

Read ALL context documentation files to understand our patterns:

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

**Action:** Internalize these patterns - they define HOW we write code and WHAT to look for.

---

## STEP 3: Analyze Changed Files in Context

For each changed file, understand the surrounding context:

```xml
<read_file>
<path>path/to/changed/file</path>
</read_file>
```

**For Java files:**
- Read the entire class to understand context
- Check related service/repository classes
- Look for similar implementations in the codebase

**For TypeScript/Angular files:**
- Read the component/service file completely
- Check related services and models
- Look for similar patterns in other components

**For MyBatis XML:**
- Read the entire mapper file
- Check the corresponding Java mapper interface
- Review similar queries in other mappers

Use `search_files` to find related implementations:
```xml
<search_files>
<path>src/main/java</path>
<regex>similar pattern or method name</regex>
<file_pattern>*.java</file_pattern>
</search_files>
```

---

## STEP 4: Perform Perspective-Based Analysis

Now analyze the PR against OUR codebase patterns. For EACH perspective, provide **specific, actionable feedback**:

### Analysis Checklist:

#### 🧠 [Logical] - Top Priority
- Are there logic errors or edge cases not handled?
- Does the code handle null/undefined based on OUR Optional/nullable patterns?
- Are loops, conditions, and algorithms correct?
- Does it handle concurrent scenarios if applicable?
- Are there off-by-one errors or boundary issues?
- **Reference:** Cite similar code in our codebase as examples

#### 💡 [Improvement]
- Is there a BETTER way we do this elsewhere in OUR codebase?
- Are they following OUR established patterns? (Check context docs)
- Could this use our existing utility classes/services?
- Is there code duplication that violates DRY in our context?
- **Reference:** Point to specific files/classes in our repo as examples

#### 🔧 [Maintenance]
- Will future developers understand this code?
- Are variable/method names consistent with OUR conventions?
- Is there adequate inline documentation for complex logic?
- Does this follow our architectural boundaries?
- Will this be easy to test/debug?
- **Reference:** Compare with our coding standards

#### 🐛 [Bug]
- Are there potential runtime exceptions based on OUR data flow?
- Is error handling consistent with OUR patterns?
- Are database operations properly transactional per OUR rules?
- Could this cause NPE/undefined errors in our environment?
- Are API responses properly validated?
- **Reference:** Mention past similar bugs if known

#### ⚠️ [Critical]
- Are there security vulnerabilities (SQL injection, XSS, auth bypass)?
- Could this cause data loss or corruption?
- Are there performance issues (N+1 queries, memory leaks)?
- Does this break backward compatibility?
- Are there missing database migrations?
- **Reference:** Cite our security/performance guidelines

---

## STEP 5: Structure Your Review

Create a comprehensive review comment with this structure:

```markdown
## PR Review: {PR Title}

### Summary
{Brief understanding of what this PR does - 2-3 sentences}

### 🧠 [Logical] Issues
{List each logical issue with:}
- **File:** {filename}:{line} 
- **Issue:** {specific problem}
- **Why:** {explain based on OUR patterns}
- **Example:** {reference similar code in our repo}

### 💡 [Improvement] Suggestions
{List improvements with:}
- **File:** {filename}:{line}
- **Current:** {what they did}
- **Better:** {how WE typically do this}
- **Reference:** {link to similar implementation in our codebase}

### 🔧 [Maintenance] Concerns
{List maintenance issues}

### 🐛 [Bug] Potential Bugs
{List potential bugs based on OUR patterns}

### ⚠️ [Critical] Critical Issues
{ONLY if there are critical issues - security, data loss, breaking changes}

### ✅ Positive Highlights
{Mention 1-2 things done well, if applicable}

### Recommendation
{Approve / Request Changes / Needs Discussion}
```

**Important Guidelines:**
- Be specific, not generic
- Always reference OUR codebase patterns
- Point to similar implementations in our repo
- Explain WHY something is an issue in OUR context
- Keep tone friendly and collaborative
- Focus on high-impact issues first

---

## STEP 6: Confirm with User

Before posting the review, present your analysis to the user:

```xml
<ask_followup_question>
<question>I've completed the perspective-based review of PR #{PR_NUMBER}. Here's my analysis:

{Paste your structured review here}

Would you like me to:
1. Post this review to GitHub
2. Revise specific sections
3. Add more detail to certain perspectives
</question>
<options>["Post the review", "Revise sections", "Add more detail", "Cancel review"]</options>
</ask_followup_question>
```

---

## STEP 7: Post Review to GitHub

Based on user's choice and severity of issues:

**If there are Critical or multiple Logical/Bug issues:**
```bash
cat << EOF | gh pr review {PR_NUMBER} --request-changes --body-file -
{Your structured review}
EOF
```

**If there are only Improvements/Maintenance suggestions:**
```bash
cat << EOF | gh pr review {PR_NUMBER} --comment --body-file -
{Your structured review}
EOF
```

**If everything looks good:**
```bash
cat << EOF | gh pr review {PR_NUMBER} --approve --body-file -
{Your structured review}
EOF
```

---

## STEP 8: Confirmation

After posting, confirm with the user:

```
✅ Review posted successfully to PR #{PR_NUMBER}

Summary:
- {X} Logical issues found
- {X} Improvements suggested
- {X} Maintenance concerns
- {X} Potential bugs identified
- {X} Critical issues (if any)

The review has been posted as: {approve/comment/request-changes}
```

---

## Important Notes

1. **Always be specific** - Reference actual files, classes, methods from our codebase
2. **Never give generic advice** - Every suggestion should relate to OUR patterns
3. **Provide examples** - Point to how we've solved similar problems before
4. **Prioritize correctly** - Logical errors > Bugs > Improvements > Maintenance
5. **Be constructive** - Frame feedback as learning opportunities
6. **Check thoroughly** - Don't rush, analyze the full context

## Error Handling

If you encounter issues:
- Can't fetch PR: Verify PR number and repository
- Can't read context files: Check if they exist in `.cline/context/`
- Missing patterns: Ask user to provide specific pattern documentation
- Unclear changes: Ask clarifying questions before reviewing

---

**Remember:** This is about maintaining OUR codebase quality based on OUR established patterns, not applying generic best practices.