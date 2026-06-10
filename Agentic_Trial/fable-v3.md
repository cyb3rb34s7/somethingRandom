# OpsMindAI — Fable Prompt 3: Enterprise Onboarding and the Context Layer

---

## Framing

This is a focused deep-dive session. The previous two sessions established the full product vision and a complete engineering architecture for the runtime, agents, log pipeline, and product layer. All of that is fixed context.

This session has one job: **design the onboarding system and the context layer it produces, at enterprise scale, with the depth and precision required to actually build it.**

The previous sessions touched onboarding but didn't go deep enough. The previous session's architecture hand-waved through the hardest problems — how you actually process thousands of Confluence docs, a decade of Jira history, 50-100 services with mixed codebases, architecture diagrams, business decision trails, API specs in every format imaginable — and what the resulting context layer actually looks like, how it's stored, how it stays current, and how every agent in the system accesses it efficiently at runtime.

That is what this session must design. Do not be conservative. This is the most important part of the product. If the context layer is weak, every agent built on top of it is weak. If the context layer is excellent, every agent becomes excellent almost for free.

You are free to reason from first principles. You are free to propose approaches that don't exist yet. You are free to reject conventional wisdom about RAG, vector stores, and document processing if you have better ideas. The goal is not a list of known tools — it is a complete, production-grade architecture for solving the enterprise onboarding problem in a way that has not been solved well before.

---

## Background: What the Previous Sessions Decided

Read this section carefully. Everything you design must be consistent with these fixed decisions.

**The context repo** is git-canonical (one repo per tenant, lives in the customer's GitHub org) with a derived index (Postgres + pgvector) as the query plane. The git repo is the source of truth, audit trail, and human-editable surface. The index is derived, disposable, and always rebuildable from git.

**The block-ownership mechanism** is the write primitive. Every markdown artifact is composed of blocks delimited by `<!-- omd:block -->` comments with three owner classes: `renderer` (deterministic projection of structured data, always regenerated), `agent` (bounded LLM narrative, regenerated when sources change), `human` (never touched by any agent, survives every regeneration). `ContextRepoWriter.merge_update` operates at block granularity.

**The Writer/Reader split** is absolute. `ContextRepoWriter` is the sole write path — agents never touch git or the index directly. `ContextRepoReader` is the sole read path — with typed fast lookups, hybrid FTS+vector search, and `compile(task, budget)` as the workhorse that assembles task-scoped context for agents.

**The provenance ladder** is: `observed` (deterministic extraction — CodeiQ, parsed config, parsed API spec) > `human-confirmed` > `derived` (LLM synthesis from observed facts) > `inferred` (LLM reasoning without direct evidence). Every artifact and every fact carries provenance. Agents cite provenance in their outputs.

**CodeiQ** is the static analysis layer for code — runs per service, produces a structured graph (nodes: modules, methods, classes, endpoints, entities; edges: imports, calls, contains). It is not enough on its own — it gives structure but not meaning. It does not understand business logic, does not resolve dynamic dispatch, and does not connect code to the documents and decisions that explain why it exists.

**Temporal** is the workflow engine for all multi-step, partially-failing, resumable pipelines. Onboarding is a Temporal workflow.

**The knowledge graph** lives in Postgres. Nodes and edges with typed schemas. Recursive CTE queries for traversal. No separate graph database. pgvector for embeddings on text-content nodes.

**The connector pyramid**: pull connectors (OAuth, read-only credentials) are the primary pattern. OTel-native intake for telemetry. No proprietary sidecar. The system is designed to be the best consumer of data that already exists, not another data collector.

---

## The Problem Statement — State This Precisely Before Designing

You are designing an onboarding system for an enterprise engineering organisation. Here is what that actually means at scale:

**The code estate:**
- 50–100 services, potentially more
- Mixed languages and frameworks — Python, Java, Go, Node, .NET, Ruby, whatever accumulated over a decade
- Monorepos containing 20+ services alongside single-service repos
- Codebases ranging from 5,000 to 500,000 lines
- Legacy code with no tests, no docstrings, no comments
- CodeiQ gives you the structural skeleton but not the meaning — you still don't know what a 10,000-line Java service actually does, what its business rules are, what its failure modes are, or why it was built the way it was

**The document estate:**
- Confluence spaces with 500–5,000 pages accumulated over years
- Architecture Decision Records written by people who have left
- Runbooks that were accurate three infrastructure generations ago
- API specifications in Swagger, OpenAPI 3, Postman collections, Word documents, PDFs, Google Docs, Notion pages, or a README with curl examples
- Architecture diagrams in Confluence, Miro, Lucidchart, draw.io, or embedded as images in documents
- Design docs, RFC documents, post-mortems, incident reports
- Some of this is gold. Most of this is noise. You don't know which is which until you've read it.

**The decision trail:**
- Years of architectural decisions buried in Jira comments, Confluence pages, Slack threads, and the memories of senior engineers
- "We moved away from RabbitMQ in 2021" lives in a Jira ticket comment from someone who left
- "The checkout service is intentionally synchronous because of a compliance requirement from 2019" lives nowhere but in the head of the founding CTO
- ADRs exist for maybe 20% of actual decisions if the team was disciplined. Usually less.

**The Jira corpus:**
- 5,000–50,000 tickets across years
- Bug reports, feature requests, incident tickets, post-mortems, migration trackers, compliance tasks
- Signal-to-noise ratio is brutal — a Jira ticket titled "INFRA-4821: update redis version" contains one useful sentence about why Redis was pinned to that version
- The signal is extraordinarily valuable — recurring bug patterns, service ownership history, the real story of why the architecture looks the way it does

**The business context:**
- What does the company actually do?
- What are the critical paths — what happens if payment-service goes down in business terms?
- What are the SLAs, the compliance requirements, the regulatory constraints?
- Who are the customers and what do they care about?
- None of this is in any system — it lives in people's heads and in sales/product docs that engineering never reads

**The scale problems:**
- You cannot fit 5,000 Confluence pages into any context window
- You cannot afford to run a deep LLM pass over every document at ingestion time
- Embeddings degrade in quality at retrieval time as the corpus grows unless you have strong structure
- Static analysis on a 500,000-line Java monolith is slow and memory-intensive
- You have to handle partial failures — if the Confluence connector times out on page 3,000, the pipeline must resume from page 3,001, not restart
- The corpus is never static — new commits, new docs, new tickets every day
- Human edits to the context repo must survive re-ingestion of updated sources
- A fact extracted from a 2019 Confluence page must be clearly marked as potentially stale, not treated as current truth

---

## What Needs to Be Designed

Design the complete onboarding architecture. Every section below is a design requirement. Go deep. Propose concrete implementations, specific tools, specific schemas, specific algorithms. Where conventional approaches are inadequate, propose new ones. Where you are uncertain, say so and explain why — don't paper over uncertainty with confident-sounding generalities.

---

### 1. The Ingestion Layer — Source Connectors

Design a connector architecture that is genuinely adaptable to any enterprise document source.

The sources that must be supported, and the specific challenges of each:

**GitHub/GitLab** — code, READMEs, commit history, PR descriptions, code review comments. The PR history and commit messages are underexploited signal — architectural decisions made in code review are as valuable as ADRs.

**Confluence** — the primary enterprise doc source. Specific challenges: nested page hierarchies (a page's position in the hierarchy is semantic signal), page history (the 2019 version of an architecture page is different from today's version — which one is authoritative?), inline images and diagrams (non-trivial to extract meaning from), macros and structured content that don't survive HTML export cleanly, spaces that are "official" vs spaces that are personal/abandoned.

**Jira** — tickets at scale. Specific challenges: comment threads (the resolution is often in comment 7, not the ticket body), linked tickets (a chain of linked tickets tells a story), custom fields that vary by project/org, distinguishing signal tickets from noise tickets without reading them all.

**Google Docs / Notion / Sharepoint** — less structured than Confluence, more varied. Google Docs in particular often contains the most recent thinking precisely because it's informal.

**PDFs and Word documents** — API specs emailed around, compliance documents, architecture diagrams exported from Visio. OCR may be required. Tables and diagrams need special handling.

**Architecture diagrams** — images embedded in docs, Miro boards, Lucidchart exports, draw.io XML. What can you actually extract from these? What tools exist? What are the limits?

**API specifications** — OpenAPI 3, Swagger 2, RAML, gRPC proto files, GraphQL schemas, Postman collections. These are some of the highest-value documents in the corpus — a machine-readable API spec is almost free to process into structured facts.

**Slack/Teams history** — the most informal but often the most current source of architectural truth. "Why is the payment service still using v1?" gets answered in Slack, not Confluence. Specific challenges: noise ratio is extremely high, threading is complex, the same conversation involves many different people and topics, privacy constraints are real.

**Runbook repositories** — often in GitHub as markdown, sometimes in Confluence, sometimes in a dedicated tool like PagerDuty runbooks or Notion.

**Meeting transcripts** — Zoom/Gong/Fireflies recordings, speaker-diarized. The highest-provenance source for architectural decisions — a CTO saying "we made this decision because X" in a recorded architecture review is gold.

For each source: what is the connector architecture, what are the authentication patterns, what are the rate limits and how do you respect them, what are the failure modes, how do you handle incremental updates, and what raw format does the data arrive in before processing?

Also design the **connector registry** — how do new source types get added by the team without touching core pipeline code, and how does the system gracefully handle a source it doesn't have a deep connector for (generic web scraping fallback? manual upload? partial processing?).

---

### 2. The Processing Pipeline — Turning Raw Data into Structured Knowledge

This is the hardest part and where the most interesting design decisions live.

**The fundamental problem:** you have millions of tokens of raw text, structured data, images, and code. You need to turn this into a knowledge graph of structured facts with provenance, confidence, and staleness metadata — at a cost and latency that makes the product viable.

Design a multi-stage processing pipeline. For each stage, be specific about:
- What tools or libraries handle it (open source preferred, justify commercial choices)
- Where LLM calls happen and where deterministic processing is sufficient
- How you handle failure and partial processing
- What the output schema looks like
- How it scales to enterprise corpus sizes

Specifically address:

**Document classification and triage** — before deep processing, you need to know what you're dealing with. How do you classify 5,000 Confluence pages by type (ADR, runbook, meeting notes, design doc, stale/obsolete, etc.) and by quality/relevance signal without reading them all deeply? What signals are available without LLM calls (page age, view count, labels, position in hierarchy, link density, author tenure)? What's the right classification architecture?

**Chunking strategy** — this is not a solved problem. Fixed-size chunking destroys semantic coherence. Naive paragraph chunking misses cross-paragraph context. For code, function-boundary chunking is obvious but what about long functions? For prose documents, what's the right chunking strategy for a 50-page architecture doc? How do you chunk a Jira comment thread where each comment is 2 sentences? Propose a chunking strategy that is genuinely better than what most RAG systems do.

**Fact extraction** — extracting structured facts from unstructured text. "We use Redis for session caching" → `{subject: payment-service, predicate: uses, object: redis, purpose: session-caching, confidence: 0.9, source: confluence:page-4821}`. This is where a lot of the value lives and also where hallucination risk is highest. What's the extraction architecture? How do you validate extracted facts? How do you handle contradictory facts from different sources?

**Relationship extraction** — more important than fact extraction. "The checkout service calls payment-service synchronously on the critical path" is a relationship between two entities with operational significance. How do you extract these from prose documents at scale? How do you reconcile relationships extracted from documents with relationships inferred from code analysis?

**Semantic deduplication** — at enterprise scale you will have the same fact stated in 50 different documents. "Payment service uses Postgres" appears in the architecture overview, the runbook, the onboarding guide, and 20 Jira tickets. How do you deduplicate facts without losing provenance? How do you weight a fact that appears in 50 sources vs a fact that appears once?

**Staleness detection and resolution** — a 2019 architecture doc says "we use MySQL." A 2022 doc says "we migrated to Postgres." How do you detect this contradiction, resolve it (newer wins, but with what confidence?), and flag the old doc as potentially stale in related areas?

**Architecture diagram processing** — this is genuinely hard. An architecture diagram embedded in a Confluence page may contain the most accurate topology information in the entire corpus. What tools exist for extracting meaning from diagrams? What can you actually do with Miro/Lucidchart exports vs embedded images? When is the right answer "extract the diagram as a visual asset, let humans annotate it" vs "attempt automated extraction"?

**Code semantic extraction beyond CodeiQ** — CodeiQ gives structure. How do you get meaning? Specifically: for a 10,000-line Java service with no docstrings, how do you extract: what this service does in business terms, what its critical paths are, what its failure modes are, what business rules are encoded in the logic? What's the right combination of AST analysis, selective deep reading, call graph analysis, and bounded LLM calls? How do you identify which functions are worth reading deeply?

**The knowledge graph construction** — after extraction, how do entities and relationships from different sources get reconciled into a unified graph? Entity resolution (the "payment-service" mentioned in Confluence and the `payment-service` detected by CodeiQ and the `PAYMENT-*` Jira project are the same thing — how do you know?) is a hard problem. Propose a concrete approach.

---

### 3. The Knowledge Graph Schema

Design the complete schema for the knowledge graph that sits beneath the context repo.

This is the queryable layer that `ContextRepoReader` operates over. It must support:
- "What are all the facts about payment-service?" (service-scoped compilation)
- "What architectural decisions affected the checkout flow?" (relationship traversal)
- "What does the failure pattern 'redis_connection_refused' look like in the codebase?" (semantic + structural)
- "What changed in the last 30 days that affects my incident investigation?" (temporal + scoped)
- "What's the blast radius if payments_db goes down?" (graph traversal)

Design the node types, edge types, property schemas, and indexing strategy. Be specific about Postgres schema — tables, columns, indexes, constraints. The graph must be queryable efficiently at runtime (sub-100ms for typed lookups, under 500ms for graph traversal at 50-service scale).

Also design the **embedding strategy** — what gets embedded, at what granularity, with what model, and how embeddings are kept current as the corpus updates.

---

### 4. The Context Repo Shape at Enterprise Scale

Given everything above, design the complete context repo folder structure for a 50-100 service enterprise org.

The structure must:
- Be navigable by a human who has never seen it before
- Be queryable by an agent that needs specific facts in milliseconds
- Handle the full range of source types — code, docs, decisions, tickets, diagrams, API specs, business context
- Scale to thousands of documents without becoming a file dump
- Clearly communicate quality and staleness at every level
- Support the block-ownership mechanism from session 2

Specifically address: what does the `knowledge-base/` layer look like — how do you render processed Confluence docs, decisions, and Jira patterns in a way that is genuinely useful rather than a flat dump? What's the right level of granularity — one file per Confluence page, or synthesised per topic? How do you handle the org-level knowledge (the ADRs that affect everything, the business context, the decision trail) separately from service-level knowledge?

---

### 5. The Quality Model — Making Context Better Over Time

The context layer is not a one-time ingestion. It must improve continuously.

Design a concrete quality model that answers:

**How do you score quality at every level?** Per-artifact, per-service, per-org. The session 2 formula (`completeness × provenance × freshness × verification`) is a starting point — improve it. What additional signals are available? How do you weight operational criticality (a gap in payment-service's runbooks matters more than a gap in an internal tooling service)?

**How do you identify the highest-leverage gaps?** Given a quality score, which specific gaps should be addressed first? This should be data-driven — a gap that would improve RCA accuracy for a service with 4 incidents/week is more valuable than a gap in a service with 0 incidents.

**How do you improve quality from agent usage?** When the RCA agent successfully resolves an incident, what can be written back to improve the context repo? When the RCA agent fails or produces a low-confidence output, what does that tell you about which part of the context is weak?

**How do you handle the cold start?** Day one, there are no incident histories, no confirmed signatures, no validated facts. The quality score is 0.3 and the context is mostly code-derived. What makes the product useful before the learning loops have fired? What synthetic enrichment is possible at onboarding time?

**How do you keep it current?** Design the incremental update architecture. A new commit, a new Confluence page, a new Jira ticket — how does each trigger the minimal necessary reprocessing? How do you avoid full re-ingestion while ensuring staleness is detected?

---

### 6. Tools and Technologies — What Exists vs What You Build

Do the research. For every major component of the pipeline, propose specific tools with honest assessment of their fit:

**Document processing and extraction:**
- What are the best open-source libraries for PDF extraction that actually handle complex PDFs (not just pdfminer)?
- What tools handle Confluence export formats well?
- What's the state of the art for extracting structured information from architecture diagrams?
- What chunking libraries exist and what are their actual tradeoffs?

**Code intelligence beyond CodeiQ:**
- What tools exist for semantic code understanding across multiple languages?
- What's the state of the art for extracting business logic from legacy Java/C# codebases?
- What role does a language server (LSP) play vs AST analysis vs LLM-based extraction?

**Knowledge graph and fact extraction:**
- What open-source tools exist for entity and relationship extraction from text?
- What NLP libraries are genuinely useful for fact extraction at scale vs heuristic approaches?
- Propose a specific embedding model (or combination of models) for the different content types in this corpus — code, prose documentation, structured data. Be specific about why.

**Log parsing and template mining:**
- Drain3, Logram, Spell — what are the actual tradeoffs for enterprise log corpora?

**Workflow and pipeline orchestration:**
- Temporal is decided. What Temporal patterns (activities, signals, queries, schedules) are the right abstractions for each part of the pipeline?

**Scalable processing:**
- At what scale does in-process processing break and you need a proper task queue?
- What's the right architecture for processing a 5,000-page Confluence space without running out of memory or hitting API rate limits?

Be honest about what doesn't exist yet and needs to be built. Be honest about where the state of the art is genuinely insufficient and you're proposing something new.

---

### 7. Enterprise-Specific Problems — Go Deep on These

These are the problems that will kill the product in enterprise if they're not solved. Most RAG and knowledge management products fail on exactly these. Think hard about each one.

**The staleness cliff.** An enterprise Confluence space has docs from 2016 to 2026. The 2016 docs describe an architecture that no longer exists. An agent citing a 2016 doc as authoritative is worse than an agent that says "I don't know." How do you solve staleness detection at the document level, the fact level, and the relationship level — automatically, without requiring humans to manually tag every old doc?

**The authority problem.** There are 15 different documents describing how the payment service works. They contradict each other. Which one is authoritative? How do you compute authority from signals like recency, author seniority, edit frequency, view count, link count, and proximity to the actual code?

**The tribal knowledge problem.** The most important operational facts are the ones that live nowhere — in the heads of senior engineers, in Slack threads that were deleted, in conversations that were never recorded. How do you elicit this knowledge systematically during onboarding without making it feel like an interrogation? How do you design the clarification agent to extract high-value tribal knowledge efficiently?

**The diagram problem.** An architecture diagram in a Confluence page contains more information about service topology than 50 text pages. But it's an image. What do you actually do with it? What's possible today with vision models? What's the failure mode when extraction is wrong?

**The scale cliff.** Processing works fine for 10 services and 200 Confluence pages. At 50 services and 5,000 Confluence pages with rate-limited APIs, what breaks? Design specifically for the scale cliff — what needs to be batched, what needs to be parallelized, what needs to be tiered (deep processing for important content, shallow for the long tail)?

**The entity resolution problem.** "payment-service" in Confluence, "payment_service" in Jira, "PaymentService" in Java code, "pay-svc" in Kubernetes configs, "payment" in Datadog — these are all the same thing. How do you build an entity resolver that handles the messy real-world naming inconsistency of an enterprise org?

**The access control problem.** Some Confluence pages are restricted. Some Jira projects are confidential. Some code repos are sensitive. The context repo reflects the access level of the integration credentials. How do you handle the case where an agent during an incident needs facts that were extracted from a restricted doc, and the requesting user doesn't have access to that doc? How do you model document-level access control in the knowledge graph?

**The multi-language codebase problem.** A Java monolith, 3 Python microservices, 2 Node.js services, a Go API gateway, and a C# legacy service. Each needs different processing. How do you build a processing architecture that handles language diversity without special-casing every language?

**The "we don't use any of those tools" problem.** An enterprise using SVN instead of Git, MediaWiki instead of Confluence, Bugzilla instead of Jira, on-premise document servers instead of cloud storage. How adaptable is your architecture? What's the fallback for sources you don't have a connector for?

---

### 8. The Onboarding Experience — What the Human Sees

Design the complete onboarding flow from the perspective of the human connecting their org — not the technical pipeline, but the experience.

Specifically:
- What is the minimum connection that gets to first value, and what does "first value" mean realistically (not in 5 minutes — be honest)?
- How do you manage expectations about what the system knows vs doesn't know at each stage of onboarding?
- How do you design the clarification agent to efficiently extract tribal knowledge without overwhelming the team?
- What does the "onboarding complete" state look like for an org where full processing took 4 hours?
- How do you handle the politics of onboarding — different teams with different levels of trust, a CTO who is bought in but a team lead who is skeptical, sensitive architecture knowledge that some teams don't want shared broadly?

---

### 9. A New Approach — What Hasn't Been Done Before

Here is an open invitation: if you see a better way to solve any part of this problem that doesn't follow conventional patterns, propose it.

Some specific provocations:

**Is a folder-based context repo even the right structure at 100-service scale?** Or does it become a navigation nightmare? Is there a better primary representation?

**Is the write-everything-to-git approach the right call for the document corpus?** Git works well for structured artifacts (service.yaml, signatures.json, small markdown files). Does it still work when you're committing processed representations of 5,000 Confluence pages? What breaks?

**Is there a better mental model than "knowledge graph" for the relationships between enterprise facts?** Knowledge graphs have been tried for decades and the quality problem (garbage in, garbage out) is persistent. Is there a way to structure operational knowledge that is more naturally self-correcting?

**What would it look like to treat the context layer as a living organism rather than a static database?** One that continuously repairs contradictions, decays stale knowledge, strengthens frequently-validated facts, and atrophies facts that are never used?

**What if the onboarding agent's primary job was not ingestion but curation?** Instead of trying to process everything, what if it explicitly chose what not to ingest, maintained a tight, high-quality core rather than a comprehensive-but-noisy corpus?

Reason freely. The goal is a context layer that is genuinely better than anything that exists today.

---

## Output Requirements

Produce a complete architecture document for the onboarding system and the context layer it produces. Structure it as an implementable spec, not a conceptual overview.

Include:
- Concrete component designs with interfaces and schemas
- Specific tool recommendations with honest tradeoff assessments
- The complete knowledge graph schema (Postgres tables and indexes)
- The complete context repo folder structure at enterprise scale
- The processing pipeline stages with failure handling
- The quality model with scoring formula
- The incremental update architecture
- An honest assessment of what is hardest, what is most likely to fail, and what requires further research before implementation

This document should be the thing an engineer reads before writing the first line of code for the onboarding system. It should make the hard decisions, not defer them.

Do not summarise the problem. Design the solution.
