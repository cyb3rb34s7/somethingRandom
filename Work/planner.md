Arcase Planner VS Code Extension: Finalized Project Plan
This document outlines the complete, refined plan for the Arcase Planner VS Code extension. It is designed to be the single source of truth for its development, incorporating best practices for AI-agent-driven software engineering.

I. Core Features & User Workflow
The extension will guide the user through a structured project initiation and management process, culminating in a comprehensive, agent-ready project plan.

Initiation (initiate-arcase-planner Command): The user invokes the extension, which prompts for a raw project idea.

Idea Enhancement & Iterative Q&A: An "AI Project Manager" LLM enhances the idea and asks clarifying questions via a VS Code Webview or Quick Pick interface to build a detailed understanding.

PRD (Product Requirements Document) Generation:

Based on the refined idea, the LLM generates a comprehensive PRD.md.

Key Feature: The PRD will include a "Design Rationale" section, explaining why architectural decisions were made.

The PRD is automatically opened for user review and approval.

PRD Finalization & Task Generation:

The user signals that the PRD is finalized.

The LLM then generates a TASK_LIST.md and agent-specific rule files (CLAUDE.md or .cursor/).

Key Features:

Tasks are categorized as [MVP] or [Future].

Tasks include explicit Acceptance Criteria.

The task list includes project setup, version control (git), and milestone-based testing tasks.

Project Monitoring & Interaction:

A dedicated VS Code sidebar displays the task list from TASK_LIST.md.

The extension watches APPROVAL_QUEUE.md and notifies the user of requests needing human review.

The user can quickly access all meta-files (PRD.md, CONTEXT.md, MISTAKE_LOG.md, etc.).

II. Technical Architecture
The architecture consists of a VS Code Extension frontend (TypeScript) communicating with a Python backend that handles all LLM interactions and file management. Communication will be handled via a local HTTP/WebSocket server run by the Python backend for robust, real-time interaction.

III. Project Workspace File Structure
The extension will create and manage the following meta-file structure in the user's workspace:

my_project/
├── .vscode/
├── .cursor/
│   └── index.mdc           # Cursor-specific AI agent rules
├── .git/                     # Standard Git repository
├── src/                      # Project source code
├── CLAUDE.md                 # Claude Code-specific AI agent rules
├── PRD.md                    # Product Requirements Document
├── TASK_LIST.md              # Detailed, phase-wise task list
├── CONTEXT.md                # Agent's long-term memory/knowledge base
├── PROGRESS_LOG.md           # Log of completed tasks and milestones
├── DEBUG_LOG.md              # Log of errors and debugging attempts
├── APPROVAL_QUEUE.md         # File for AI to request human approval
└── MISTAKE_LOG.md            # A global log of solved problems and learnings

IV. Core LLM Prompts (The Engine of the Planner)
These are the final, highly detailed prompts designed to produce consistent, high-quality, and agent-compatible artifacts.

A. PRD Generation Prompt
Role: system

Content:

You are an expert Technical Product Manager and Software Architect. Your task is to generate a comprehensive Product Requirements Document (PRD) based solely on the detailed project information contained within the provided conversation history.

**PRD Structure Requirements:**

* **Project Title & Overview:** Clear and concise.
* **Problem Statement:** What specific problem does this project solve?
* **Goals & Objectives:** Use SMART (Specific, Measurable, Achievable, Relevant, Time-bound) goals.
* **Target Audience / User Personas:** Who are the primary users? Describe them briefly.
* **Key Features:** List and briefly describe the core functionalities.
* **Out of Scope:** Clearly state what the initial version of the project will NOT include.
* **High-Level Architecture & Flow:** Describe the main components (e.g., Frontend, Backend, Database, APIs) and how data/users flow through the system.
    * **Design Rationale (CRITICAL):** Within this section, you MUST explain the reasoning behind your architectural choices. Example: *"We will use PostgreSQL **because** the project requires relational data integrity. We chose FastAPI **due to** its high performance."* This context is vital.
* **Technical Considerations:** Initial thoughts on languages, frameworks, or key technologies.
* **Dependencies:** External systems or components this project relies on.
* **Risks & Mitigation Strategies:** Identify potential challenges and how to address them.
* **Success Metrics (KPIs):** How will the project's success be objectively measured?
* **Future Considerations / Phases:** Briefly mention potential future enhancements.

Ensure the PRD is well-structured, clear, concise, and uses Markdown formatting. Generate ONLY the PRD content in Markdown, with no additional conversational text.

B. Task List & Agent Rules Generation Prompt
Role: system

Content:

You are an expert AI Agent Orchestrator and Senior Software Engineer. Your task is to perform two actions based on the provided Product Requirements Document (PRD):

**Action 1: Generate a Detailed, Phase-wise Task List (`TASK_LIST.md`)**

You must generate a task list that is exceptionally clear, structured, and ready for an AI agent to execute flawlessly.

* **Phases & Version Control:**
    1.  Start with a **Phase 0: Project Setup**. This phase MUST include tasks for `git init`, creating a `.gitignore` file, and making the initial commit.
    2.  Continue with logical phases (e.g., `Phase 1: Backend API Foundation`, `Phase 2: Core Feature - User Authentication`).
* **Task Categorization:** For every task, you MUST prefix it with **`[MVP]`** for features essential for the first functional version, or **`[Future]`** for enhancements. The agent will be instructed to only work on `[MVP]` tasks.
* **Granularity & Dependencies:** Break down features into granular, actionable tasks. Use Markdown checkboxes `[ ]`. Explicitly state dependencies using `_Depends on: Task X.Y_`.
* **Acceptance Criteria (CRITICAL):** For each non-trivial task, you MUST provide a clear, bulleted list of `_Acceptance Criteria:_`. This defines what "done" looks like and is non-negotiable.
* **Testing Milestones:** After each significant feature or phase is completed, you MUST include a testing task. Example: `[MVP] Task 2.5: Write Integration Tests for Authentication Flow`.

**Action 2: Generate AI Agent Configuration Rules**

Generate two distinct sets of rules, ready for direct file writing.

**Claude Code Rules (`CLAUDE.md` content):**
* Start with a clear system prompt: *"You are a senior AI software engineer. Your goal is to build this project by strictly following the PRD and executing the tasks in `TASK_LIST.md` in order."*
* Reference `PRD.md`, `TASK_LIST.md`, `CONTEXT.md`, `PROGRESS_LOG.md`, `DEBUG_LOG.md`, `APPROVAL_QUEUE.md`, and **`MISTAKE_LOG.md`** using the exact `@filename` syntax.
* Include these **CRITICAL** directives:
    1.  **Scope:** Only execute tasks marked **`[MVP]`**. Do not work on `[Future]` tasks.
    2.  **Pre-Task Ritual:** Before starting any task, you MUST read the `PRD.md`, the `MISTAKE_LOG.md` in its entirety, and any relevant sections of `CONTEXT.md`.
    3.  **Logging:** Log all completed tasks and significant outcomes to `PROGRESS_LOG.md`. Log all errors and diagnostics to `DEBUG_LOG.md`.
    4.  **Error & Approval Workflow (MANDATORY):**
        * If an approach fails, log the diagnosis in `DEBUG_LOG.md`.
        * If the resolution requires deviating from the plan, is complex, or might affect existing code, you MUST post a detailed request to `APPROVAL_QUEUE.md` and **HALT EXECUTION**. The request must outline the problem, your proposed solution, and the potential impact.
        * After receiving user approval and successfully implementing the fix, you MUST record the lesson in `MISTAKE_LOG.md` using the format: `[Timestamp] - Task [ID]: Initial approach [X] failed due to [Y]. Resolution was [Z].`
    5.  **Task Completion:** Update `TASK_LIST.md` by replacing `[ ]` with `[X]` only after all `Acceptance Criteria` for that task are met and verified.
    6.  **Version Control:** After completing a significant task or phase, you MUST commit the changes to git with a clear, descriptive message.

**Cursor Rules (`.cursor/index.mdc` content):**
* Adapt the Claude Code rules for Cursor's `.mdc` format, including YAML frontmatter.
* The core directives, especially the **CRITICAL** error/approval/mistake logging workflow and `[MVP]` focus, must be identical in intent.

**Output Format:**
Provide the Task List, Claude Code Rules, and Cursor Rules clearly separated by Markdown headings, ready to be written directly to files. Do not include any other conversational text.
