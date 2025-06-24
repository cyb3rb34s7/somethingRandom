Arcase Planner VS Code Extension: Finalized Project Plan
This document is the single source of truth for the Arcase Planner VS Code extension. It outlines the complete project plan, from user workflow and technical architecture to the specific AI prompts required for its operation, incorporating best practices for AI-agent-driven software engineering.

I. Core Features & User Workflow
The extension guides a user through a structured project initiation and management process, from a raw idea to a complete, agent-ready project plan.

Initiation (initiate-arcase-planner Command)

Invocation: The user invokes the extension via a VS Code command.

Prompt: A Quick Pick input box appears: "Welcome to Arcase Planner! Let's start with your raw project idea. What do you want to build, and what problem does it solve?"

Idea Enhancement & Iterative Q&A (AI-Assisted)

AI Enhancement: The raw idea is sent to a backend LLM (acting as an "AI Project Manager"), which enhances it and identifies ambiguities.

Iterative Q&A: The LLM generates clarifying questions (e.g., "Who are the target users?"), presented via a VS Code Webview or sequential Quick Picks.

Refinement: Each user response is fed back to the LLM, which refines its understanding and asks follow-up questions as needed.

Confirmation: Once sufficient information is gathered, the LLM presents a summary and asks for confirmation to proceed with PRD generation.

PRD (Product Requirements Document) Generation

Notification: The user is notified: "Great! I'm now working on generating your comprehensive Product Requirements Document (PRD)..."

LLM Generation: The LLM uses the full conversation history to generate PRD.md, including the critical "Design Rationale" section explaining why architectural decisions were made.

File Creation & Auto-Open: The PRD.md file is created and automatically opened in a new VS Code tab for immediate user review.

PRD Finalization & Task Generation

Finalization Signal: The user signals that the PRD is finalized via a command or a UI button.

LLM Generation: The finalized PRD content is sent to the LLM to generate the TASK_LIST.md and agent-specific rule files (CLAUDE.md, .cursor/index.mdc).

Key Task List Features:

Tasks are categorized as [MVP] or [Future].

Tasks include explicit Acceptance Criteria.

The list includes tasks for git setup, environment configuration, and milestone-based testing.

Project Monitoring & Interaction

Sidebar View: A dedicated "Arcase Tasks" sidebar parses and displays TASK_LIST.md with clear progress indicators.

Quick Access: The sidebar provides links to quickly open all meta-files (PRD.md, MISTAKE_LOG.md, etc.).

Approval Workflow: The extension watches APPROVAL_QUEUE.md for new entries. When a request is detected, a VS Code notification alerts the user, allowing for quick review and response.

II. Technical Architecture & Implementation Details
The solution consists of a VS Code Extension frontend and a Python backend, communicating via a local server.

graph TD
    subgraph VS Code Environment
        A[User] -- Interacts with --> B(VS Code Extension - TypeScript);
        B -- Sends User Input --> C{Local HTTP/WebSocket Server};
        C --  Streams AI Responses/Updates --> B;
        B -- Updates --> D[UI Components: Webview, Sidebar, Notifications];
    end

    subgraph Backend Environment
        C --  Forwards Request --> E(Python Backend - FastAPI/Flask);
        E --  Sends Formatted Prompt --> F(LLM API - Gemini/Claude/OpenAI);
        F -- Returns Raw Text --> E;
        E -- Manages --> G[File System: PRD.md, TASK_LIST.md, etc.];
    end

    style A fill:#d4edda
    style F fill:#f8d7da

VS Code Extension (TypeScript/JavaScript)
Main Logic (extension.ts): Handles extension activation, command registration, and orchestrates UI components.

UI Management: Manages Webviews for interactive Q&A and a TreeView for the "Arcase Tasks" sidebar.

File System Watchers: Uses vscode.workspace.createFileSystemWatcher to monitor changes to meta-files (APPROVAL_QUEUE.md, TASK_LIST.md) and trigger UI updates or notifications.

Backend Communication: Implements a client to communicate with the Python backend via a local HTTP/WebSocket server. This is more robust for long-running, real-time interactions than a simple child process.

Python Backend
LLM Integration: Acts as the core AI brain, using official client libraries (e.g., google-generativeai) to handle prompt engineering for each stage of the workflow.

File Management: Contains robust functions for creating, reading, and writing all project meta-files.

Rule Generation: Dynamically generates the precise Markdown content for CLAUDE.md and Cursor's .mdc files.

Local Server: Exposes a lightweight server (e.g., using FastAPI) to receive requests from the VS Code extension and stream back responses.

III. Project Workspace File Structure
The extension creates and manages the following meta-file structure in the user's workspace:

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

IV. Key Implementation Considerations
LLM Token Management: For complex projects, the conversation history will be summarized before being sent in subsequent prompts to stay within the LLM's context window.

User Experience (UX): The UI will be designed to be intuitive, with clear instructions and non-blocking feedback during LLM generation.

Error Handling: The extension will have robust internal error handling for LLM API failures, network issues, and unexpected responses.

Security: API keys will be handled securely using VS Code's SecretStorage API or environment variables, never hardcoded.

Version Control: The user will be encouraged to commit all meta-files to Git to preserve project history and agent context.

V. Core LLM Prompts
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
