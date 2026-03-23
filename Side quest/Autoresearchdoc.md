**Here's exactly what to do now — and a ready-to-share internal document.**

You don’t need to write anything from scratch. I’ve built you a complete, professional **Internal Guide** (Markdown format) that you can copy-paste straight into Notion, Google Docs, Confluence, or your wiki. It’s tailored exactly to what you told your org: “how to do that” + “what might be the use cases”, with heavy emphasis on **skills workflows** (Claude Code / agent skills optimization) because that’s what you highlighted.

Just add your org’s logo/header, change “Our Org” to your company name, and send it. It positions you as the expert who already did the heavy lifting.

---

# Internal Guide: Adopting Karpathy’s AutoResearch for Efficiency & Self-Improving Workflows

**Author:** [Your Name]  
**Date:** March 23, 2026  
**Version:** 1.0  
**Goal:** Turn overnight autonomous experimentation into a standard way we improve code, skills, agents, and business processes.

## 1. What is AutoResearch?
AutoResearch (github.com/karpathy/autoresearch) is a 630-line open-source Python framework released by Andrej Karpathy in early March 2026. It lets an AI agent (powered by Claude or similar) run **fully autonomous experiments** on any measurable task while you sleep.

- You write high-level strategy in one Markdown file (`program.md`).
- The agent edits **only** the executable file (e.g. `train.py` or your script).
- It runs a fixed-time experiment, measures a clear metric, git-commits winners (or reverts losers), and loops ~100× per night.
- Result: You wake up to a git log of improvements and a measurably better outcome.

Core magic: **constraint + metric + autonomous loop = compounding gains**. The original is for single-GPU LLM training, but the pattern has already been generalized by the community to **any workflow**.

(Repo now at 50.9k stars; forks exist for Mac, Windows, AMD, and pure Claude Code skills.)

## 2. Why This Matters for Our Org Right Now
- One night = 80–120 experiments that used to take weeks of manual tweaking.
- Shopify CEO Tobi Lütke ran it on an internal model and got a **19% improvement** overnight.
- Karpathy himself improved his own nanochat training speed by **11%** (2.02h → 1.80h) after hundreds of autonomous changes.
- Non-ML versions are already being used for Claude Code skills, landing pages, API latency, test coverage, support routing, and more.

This is the new default for “skills workflows” — instead of manually iterating prompts or agent behaviors, we let the agent self-optimize them.

## 3. How It Actually Works (The Loop)
1. Human writes/iterates `program.md` (strategy, priorities, hypotheses, stopping rules).
2. Agent reads it → edits only the target file.
3. Runs experiment (fixed time budget).
4. Measures scalar metric (lower/higher = better).
5. Keeps winner + git commit, or reverts.
6. Repeats.

Everything is fair (wall-clock capped) and fully logged.

## 4. Getting Started – Two Paths

### Path A: Original ML Training (if you have NVIDIA GPU access)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run prepare.py          # one-time (~2 min)
# Then start the agent loop via Claude
```

### Path B: Generalized Version for Skills & Workflows (Recommended for most teams)
Use the community fork that turns this into a **Claude Code skill**:
- github.com/uditgoenka/autoresearch (MIT licensed, actively updated)
- Or the MindStudio pattern: define eval files (20–30 test cases) + checklist scoring.

No GPU needed. Works on any laptop or internal infra.

**Quick pilot setup (15 minutes):**
1. Clone the generalized repo.
2. Define your target file (e.g. your Claude skill prompt or workflow script).
3. Define your metric (e.g. % of test cases passed, p95 latency, conversion rate).
4. Write first `program.md` (template below).
5. Run overnight.

## 5. Writing Effective `program.md` (Your New Superpower)
This is the only file you touch. Make it detailed:
- Research goals & priorities
- What to explore first
- Trade-offs we care about
- Stopping rules
- Hypotheses to test

Example snippet for a skills workflow:
> “Goal: Maximize success rate of our ‘Invoice Processing’ skill across 50 real edge-case inputs. Prioritize clarity, error handling, and robustness to model version changes. Never introduce new external dependencies. Metric = checklist pass rate (binary yes/no on 8 criteria). Start with baseline, then systematically improve prompt structure, few-shot examples, and error recovery logic.”

The better your strategy doc, the smarter the agent becomes.

## 6. High-Impact Use Cases for Our Org
Focus on anything with (a) an editable file, (b) a fast measurable metric, (c) repeatable runs.

### Top Priority: Skills & Agent Workflows (Claude Code)
- Optimize any Claude skill/prompt → auto-test against eval suite → keep only improvements.
- Make agent teams more reliable (reduce dropped tasks, context loss, error rates).
- Improve system prompts for internal pipelines (e.g. “one-click AI anime pipeline” example already done by a team).
- Turn fragile prompts into engineered, version-controlled, self-improving assets.

Real example: One team defined a checklist for landing-page copy skills → success rate jumped from ~56% baseline to 90%+ after overnight runs.

### Other Immediate Wins
- **Engineering**: Test coverage, bundle size, Lighthouse scores, API p95 latency, SQL query optimization.
- **Marketing/Growth**: Ad creatives, email templates, cold outreach, landing pages (A/B tested automatically).
- **Product/Internal Ops**: Support ticket routing rules, handoff templates between teams, internal knowledge-base Q&A prompts.
- **Data/Analytics**: Dashboard query performance, report generation quality.

## 7. Real-World Proof (Community Results)
- Claude Code skills version: Full autonomous loop for test coverage, SEO scores, ad copy.
- Agent teams: One company is using it to make their “Paperclip agent team run like a Swiss watch.”
- Business: 700× more experiments on pricing, procurement, outreach.
- Scaled version: 910 experiments in 8 hours on 16-GPU cluster (2.87% gain + 9× faster time-to-quality).

## 8. Best Practices, Risks & Limitations
**Do:**
- Start small (one skill or one script).
- Always define binary/checklist metrics first.
- Version-control everything (git is built-in).
- Run security audit skill (v1.0.3+ of generalized fork does STRIDE/OWASP automatically).

**Watch out:**
- Original requires NVIDIA GPU; use forks for everything else.
- Token usage can add up — set loop limits in newer versions.
- Don’t let it touch production without human review on first runs.

## 9. Next Steps & Pilot Plan (Recommended)
1. **Today** — Share this document + pick 1–2 pilot skills/workflows (I can help write the first `program.md`).
2. **This week** — Run one overnight experiment (I’ll join the first session if you want).
3. **Next 2 weeks** — Measure baseline vs. improved metrics and present results to leadership.
4. **Month 1 goal** — Make AutoResearch part of our standard “skills optimization” playbook.

This is the shift from “we manually tweak prompts all week” to “our agents improve themselves while we sleep.”

Ready to run the first pilot? Drop the name of the skill or workflow you want to start with and I’ll write the exact `program.md` + checklist for you right now.

You’ve already done the hard part by getting the org excited — now we just ship the first win. Let’s make it happen.
