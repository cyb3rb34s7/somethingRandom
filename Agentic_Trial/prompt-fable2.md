# OpsMindAI — Fable Prompt 2: The Product Layer

---

## Context

This is the second architectural session on OpsMindAI. The first session produced a complete engineering architecture for the core loop: context repo data model (git + Postgres/pgvector dual-store), Writer/Reader interfaces, log pipeline, code graph service, RCA agent v2, eval harness, and a sequenced Phase 1 implementation plan across six workstreams.

That response is included below in full. Read it before proceeding — everything in this session builds on top of it and must be consistent with the decisions already made.

---

## What the first session produced (include full Fable response here)

[PASTE FULL FABLE RESPONSE 1 HERE]

---

## What this session covers

The first session nailed the engineering architecture for the core loop. What it didn't design is the **product layer** — the human-facing surfaces, the remaining agents, the distribution channels, and the business infrastructure. These decisions affect the context repo schema and the agent architecture already designed, so they need to be closed before implementation starts.

There are six areas. Go deep on each. Push back on our raw thinking. Produce production-grade designs.

---

## Area 1: The context repo as a navigable artifact experience

The first session designed the data model and agent-side interfaces excellently. What it didn't design is what a **human sees**.

Our vision: the context repo viewer in the dashboard should feel like navigating a living knowledge product — not browsing files. Think of how Claude produces structured artifacts with diagrams, explainers, and visual components that users can navigate. Each service should feel like a premium technical document that a senior engineer would be proud to have written about their system.

**What we need designed:**

The rendered artifact templates — what does each artifact type actually look like when a human opens it? Specifically:

- `README.md` for a service — the entry point. What sections, what inline visuals, what quick-stats, what navigation links? This is the first thing a new SRE sees when they open the system.
- `architecture/overview.md` — the narrative architecture summary. What structure makes this actually useful vs a wall of generated text?
- The visual service map — we said `.svg` / Mermaid. What does the diagram actually show? What's the right level of detail for an org with 40 services vs 4? How does it stay readable?
- `incidents/{date}-{slug}.md` — the post-mortem artifact. What's the template? What sections are agent-generated vs human-required? How does it link back to the failure signature and the evidence?
- `onboarding/gaps.md` — this drives the quality score and surfaces what the system doesn't know. What does a good gaps artifact look like? How is it prioritised?

**The dashboard context repo viewer:**

How should the web UI render this? We don't want a file browser. We want something that feels like a product. What's the right navigation model — service cards, a graph view, a search-first experience? How does quality score surface visually? How does a human correct something the agent got wrong directly from the UI?

**The artifact generation UX:**

When the onboarding agent is building artifacts in real time, what does the user see? We want it to feel like watching the system build knowledge — not a spinner. Our raw idea is a progress view showing each artifact being written with a live preview. Is that the right pattern? What would you design?

---

## Area 2: The onboarding UX — the connect flow

The first session described the onboarding pipeline as a technical workflow. What it didn't design is the **human experience** of connecting an org.

Our raw thinking on the flow:
1. OAuth to GitHub → pick repos
2. Connect log source (Datadog API key, CloudWatch IAM role, Splunk HEC endpoint)
3. Optional: Slack bot, PagerDuty API key
4. System builds context repo in background, surfaces clarification questions
5. Done — agents operational

Target: 5 minutes to first value.

**What we need designed:**

- The exact connect flow — screens, decisions, error states. What's the minimum viable connection that gets to a working RCA agent? What's optional?
- The clarification agent UX — how do clarification questions get delivered? In the web UI as a queue? In Slack as a DM from Mindy? What's the format of a good clarification question vs a bad one? How many is too many?
- The "first value moment" — what does the user see when onboarding completes? What does a quality score of 0.4 on day one look like in the UI and how do you frame it so it's not demoralising?
- Cold start experience — before any incidents have occurred, before any skills exist, before the learning loops have fired. What does the product feel like in week one? This is what closes or loses the deal. Design the no-priors experience explicitly.
- Incremental onboarding — a customer connects GitHub today, adds CloudWatch next week, adds Confluence the week after. How does the context repo evolve and how does quality score change? What triggers re-synthesis of affected artifacts?

---

## Area 3: The release agent — full design

The first session almost entirely ignored the release agent. It exists in the prototype but has no implementation path in Phase 1. It's a core part of the product and the decisions affect the context repo schema.

**The release agent's job:**
Validates deploys against the context repo. "This deploy changed 3 files that touch the payment entity — run these specific integration tests, monitor these specific metrics, gate on these thresholds."

**Our raw thinking:**
- Triggered by a deploy event (GitHub webhook on push/merge to main, Jenkins webhook, manual trigger)
- Reads the changeset from the deploy event
- Queries the code graph for blast radius: which entities, endpoints, and services are touched by the changed files
- Reads the service's deploy runbook and infra config from the context repo
- Produces a structured release validation report: what changed, what's at risk, what to test, what to monitor, what the gate conditions are
- Posts to Slack / opens a dashboard panel
- Monitors post-deploy metrics for the gating window
- Writes the deploy event to `changes/deploys.jsonl` regardless of outcome

**What we need designed:**

- The full release agent architecture — tools, cognitive loop design, what it reads from the context repo, what it writes back
- The blast radius query — how does it use the code graph to determine what's affected by a changeset? This is a graph traversal problem on the CodeiQ output. What's the query pattern?
- The gate conditions model — how are thresholds defined, stored, and evaluated? Who sets them? How do they evolve from defaults to service-specific learned values?
- The post-deploy monitoring loop — how long does it watch? What triggers an all-clear vs a rollback recommendation? How does this interact with the RCA agent if something goes wrong during the monitoring window?
- Integration with the context repo — what does the release agent write, in what schema, and when?
- Where does it fit in Phase 1 — should it be Phase 1 or Phase 2? What's the minimum viable release agent that's actually useful?

---

## Area 4: Mindy's memory — full design

The first session mentioned org memory and fact supersession as gaps but didn't design them. Mindy's memory is what makes the product feel like it knows your team — it's a key differentiator. It needs a proper design.

**What Mindy accumulates:**
- Team facts: "Sarah is on-call Fridays", "the checkout team owns payment-service"
- Process facts: "we deploy at 6 PM IST", "we never deploy on Mondays", "staging is flaky on Thursdays"
- Relationship facts: "payment-service and order-service share the same Redis cluster"
- Incident patterns: "whenever payment-service latency spikes, check the Redis connection pool first"

**What we need designed:**

- Fact extraction — how does Mindy extract facts from conversation? LLM-based extraction is acceptable for low volume (we said this in the first prompt) but what's the extraction schema? What makes a good extractable fact vs conversational noise?
- Fact storage — where do org facts live in the context repo? `org/team-memory.md` is in the folder structure but the schema isn't designed. How are facts structured so they're queryable by agents?
- Fact supersession — the on-call rotation changes. "Sarah is on-call Fridays" becomes false. How does the system handle contradictory facts? Who wins — the newer fact, the human-confirmed fact, or does it surface the conflict?
- Fact promotion — not every extracted fact should be permanent. How does a raw extraction become a promoted org fact? Is there a confidence threshold, a confirmation step, a decay model?
- Injection at runtime — how do facts get selected and injected into agent prompts? All facts for every interaction would be too many. What's the selection model?
- Cross-agent fact sharing — Mindy learns a fact in Slack. The RCA agent needs it during an incident investigation. How does that work?
- Privacy and sensitivity — some org facts are sensitive (personnel, escalation paths, on-call). How are they scoped so not every agent and not every tenant user can read everything?

---

## Area 5: Slack and Teams integration — full design

The first session put Slack and Teams in Phase 3 with no design. But Mindy living in Slack is core to the day-to-day product story — most interactions happen there. The Slack design affects the agent architecture and the context repo because Slack is a write path for org memory and a read path for incident notifications.

**What we need designed:**

- The Slack bot architecture — how is it deployed? One app per customer workspace or a shared app? How does multi-tenant auth work for Slack (one OpsMind account → multiple Slack workspaces)?
- The interaction model — `@opsmind investigate payment-service latency` should feel natural. What other command patterns matter? How does Mindy handle ambiguous requests in Slack vs the web UI?
- Streaming RCA results into a thread — the investigation streams findings in real time. What does good streaming output look like in Slack? Slack has limitations (message edits, block kit, thread structure). What's the right rendering pattern?
- The notification model — PagerDuty fires → OpsMind auto-investigates → posts to which Slack channel? How does the routing work? Who gets notified and when?
- Mindy learning from Slack — Mindy reads conversations she's mentioned in (or DMs) and extracts org facts. What's the scope of what she reads? How do you handle the privacy concern of a bot reading channel history?
- The approval/correction flow in Slack — "you're wrong, it was the config change" as a Slack reply that feeds back into the signature and post-mortem. How does that interaction work?
- Teams — is the architecture identical to Slack or are there meaningful differences that affect the design?
- Where does Slack fit in the build order — should it move to Phase 1 or Phase 2 given it's core to the GTM story?

---

## Area 6: Business infrastructure — metering, billing, and the weekly digest

The first session mentioned these as gaps but designed none of them. They're not glamorous but they're load-bearing for a SaaS.

**Metering and billing:**

Our pricing model: per repo + per log volume tier. Not per-seat.

- What does the metering infrastructure look like? What units do we measure — repos connected, log lines ingested, LLM tokens consumed, investigations run?
- How does per-tenant cost accounting work alongside the run persistence Fable designed? The `run_steps` table has token counts — how does that roll up to a monthly bill?
- What are the cost controls — per-tenant monthly LLM budgets, graceful degradation when budget is exceeded, circuit breakers?
- What's the right pricing model for an enterprise SaaS in this space? Is per-repo + per-log-volume actually right or is there a better structure?

**The weekly digest:**

"3 new failure signatures learned. 12 incidents auto-resolved. payment-service is highest-risk — 4 incidents this week, all traced to the same Redis connection pool configuration."

- What exactly goes in the digest? Design the full template.
- How is "highest-risk service" computed? What's the scoring model?
- Where is it delivered — email, Slack, dashboard?
- What's the cadence — weekly, daily for high-activity orgs?
- How does the digest drive product engagement — what CTAs make sense?

---

## Constraints and principles

Everything designed here must be:

- **Consistent with the first session's architecture.** The context repo schema, Writer/Reader interfaces, run persistence model, and connector pyramid from session 1 are fixed decisions. Build on top of them.
- **Sequenced into the existing Phase 1 plan.** Each area should conclude with: where does this fit in the build order, what's the minimum viable version for Phase 1, and what gets deferred?
- **Production-grade, not aspirational.** We are building this. Specifics over hand-waving.

As before: push back on anything naive, suggest what we haven't considered, and go deep where depth matters. The artifact rendering design and the release agent architecture are the two areas where we most need your sharpest thinking — they have the most downstream consequences on what's already been designed.
