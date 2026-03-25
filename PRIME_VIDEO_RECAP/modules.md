Good catch — classification is actually the **entry point** of the whole pipeline and it changes everything downstream. Let me rethink this properly.

---

## What You Actually Receive as Input

Before we define modules, let me make sure I understand the data landscape correctly.

You have multiple JSON files coming in:

**`because_you_watched.json`** — User-specific recommendations
```json
{
  "userId": "u_123",
  "sourceContentId": "inception",
  "recommendedContents": ["shutter_island", "memento", "the_prestige"]
}
```

**`related_content.json`** — Content-to-content relationships (not user specific)
```json
{
  "contentId": "inception",
  "relatedContents": ["interstellar", "shutter_island", "arrival"]
}
```

And you already have **content metadata** (no need to fetch externally for most signals):
- Description, genre, cast, awards, ratings — already present

TMDb/IMDb would only add signals you don't already have — like real-time trending score or social buzz. Everything else comes from your own metadata.

Is this roughly right? Or are there more input JSON structures I should know about before we go further?

---

## The Classification Problem

This is genuinely the most important step and it's more nuanced than it looks. The same content pair could satisfy multiple recommendation types simultaneously — Inception and Shutter Island could be **A→B** (because you watched), **Genre Match** (both psychological thriller), and **Critically Acclaimed**. 

The classifier needs to pick the **dominant reason** — the one that makes the most compelling explanation video. That's a judgment call, not just a lookup.

---

## Revised Module Breakdown

Let me redefine everything cleanly with explicit inputs and outputs per module.

---

### Module 1 — Input Aggregator
**Responsibility:** Collect and normalize all incoming data for a single recommendation event into one unified context object.

**Input:**
```json
{
  "recommendationEvent": {
    "userId": "u_123",
    "recommendedContentId": "shutter_island",
    "sourceFiles": ["because_you_watched.json", "related_content.json"]
  }
}
```

**Output — Unified Recommendation Context:**
```json
{
  "recommendedContent": {
    "contentId": "shutter_island",
    "metadata": { "genre": ["thriller", "mystery"], "cast": ["DiCaprio"], "awards": [...], "rating": 8.1, "description": "..." }
  },
  "sourceContents": [
    {
      "contentId": "inception",
      "relationship": "BECAUSE_YOU_WATCHED",
      "metadata": { "genre": ["sci-fi", "thriller"], "cast": ["DiCaprio"], "awards": [...] }
    }
  ],
  "availableSignals": ["BECAUSE_YOU_WATCHED", "RELATED_CONTENT"]
}
```

**Dependencies:** Access to all recommendation JSON files + content metadata store.

---

### Module 2 — Recommendation Type Classifier
**Responsibility:** Analyze the unified context and classify into one dominant recommendation type. This is an LLM call — it reads the available signals, compares metadata of source and recommended content, and decides the most compelling reason.

**Input:** Unified Recommendation Context from Module 1

**What the LLM considers:**
- Which source JSON files are present (because_you_watched signals A→B)
- Metadata overlap between source and recommended content (shared cast, genre, themes)
- Content metadata signals (awards → Critically Acclaimed, rating volume → Popular)
- If multiple types qualify, pick the one with the strongest evidence and most compelling narrative potential

**Output — Classification Result:**
```json
{
  "primaryType": "A_TO_B",
  "confidence": "HIGH",
  "evidence": "User watched Inception. Both feature DiCaprio, psychological thriller genre, and mind-bending narrative structure.",
  "secondaryType": "CRITICALLY_ACCLAIMED",
  "secondaryEvidence": "Shutter Island holds 88% RT score and multiple award nominations.",
  "sourceContentId": "inception",
  "recommendedContentId": "shutter_island"
}
```

**Dependencies:** Module 1 output.
**Blocks:** Module 3 — everything downstream depends on the classification result.

---

### Module 3 — Pretag Data Loader
**Responsibility:** Load and normalize pretag files for the relevant content(s). For A→B loads both source and recommended content. For all other types loads recommended content only.

**Input:** Classification Result from Module 2

**Output — Pretag Context:**
```json
{
  "recommendedContent": {
    "contentId": "shutter_island",
    "themes": [{ "name": "Fractured Perception", "rank": 1 }],
    "scenes": [...],
    "keyMoments": [...]
  },
  "sourceContent": {
    "contentId": "inception",
    "themes": [{ "name": "Mind-Bending Reality", "rank": 1 }],
    "scenes": [...],
    "keyMoments": [...]
  }
}
```

**Handles gracefully:** Missing tags, absent theme.json, variable scene lengths, missing key moments.

**Dependencies:** Module 2 output + pretag file storage access.

---

### Module 4 — SRT Spike & Subtitle Fetcher
**Responsibility:** Investigate and implement subtitle extraction from stream URLs. If feasible, extract and cache subtitle data per content.

**This is split into two phases:**

**Phase 4A — Spike (investigative)**
Try ffmpeg extraction against sample stream URLs. Output: yes/no decision + working script if yes.

**Phase 4B — Subtitle Fetcher (if spike succeeds)**
For given contentId + scene window (startTime, endTime), extract relevant subtitle lines only.

**Input:** contentId + startTime + endTime
**Output:**
```json
{
  "contentId": "inception",
  "sceneWindow": { "start": 3480, "end": 3521 },
  "dialogue": [
    { "timestamp": 3482, "text": "We're losing the dream. The levels are collapsing." },
    { "timestamp": 3512, "text": "We wake up. Or we don't." }
  ]
}
```

**Dependencies:** Stream URL access. Independent of all other modules.
**Blocks:** Module 5 clipping precision.

---

### Module 5 — Correlation & Highlight Engine
**Responsibility:** For A→B — find correlation between source and recommended content using themes + metadata. For other types — extract the primary highlight angle using content metadata + external signals if needed.

**Input (A→B):**
- Pretag Context from Module 3 (both contents)
- Classification Result from Module 2
- Content metadata (genre, cast, awards, description) for both contents

**Input (non A→B):**
- Pretag Context from Module 3 (recommended content only)
- Classification Result + type-specific signals (awards for Acclaimed, rating count for Popular etc.)

**Output (A→B) — Correlation Object:**
```json
{
  "correlations": [
    {
      "rank": 1,
      "reason": "Both feature protagonists who cannot distinguish reality from illusion",
      "evidence": {
        "themeMatch": "Mind-Bending Reality ↔ Fractured Perception",
        "metadataMatch": "Shared lead actor, psychological thriller genre"
      },
      "confidence": "HIGH",
      "narrativeAngle": "DOMINANT_MATCH"
    }
  ]
}
```

**Output (non A→B) — Highlight Signal Object:**
```json
{
  "narrativeType": "CRITICALLY_ACCLAIMED",
  "primaryAngle": "Award-winning psychological thriller with near-universal critical praise",
  "dominantTheme": "Fractured Perception",
  "toneDirection": "PRESTIGE"
}
```

**Dependencies:** Module 2 + Module 3.

---

### Module 6 — Scene Selector & Clip Resolver
**Responsibility:** Select the best key moments for the video, determine clip windows using available clipping strategy.

**This is two sequential steps:**

**Step 6A — Scene Selection**
Given correlation/highlight reasons, pick the best key moment(s) from each content. Flag spoiler risk. For A→B picks one from each content. For others picks 1-2 from recommended content.

**Input:** Correlation/Highlight Object + Pretag Context
**Output:**
```json
{
  "selectedScenes": [
    {
      "contentId": "inception",
      "keyMomentNumber": 4,
      "startTime": 3480,
      "endTime": 3521,
      "spoilerRisk": "LOW",
      "narrativePurpose": "Visual hook — reality collapsing"
    }
  ]
}
```

**Step 6B — Clip Resolution**
For each selected scene, determine the precise clip window using available strategy.

**Input:** Selected scenes + subtitle dialogue (Module 4 output if available)
**Output:**
```json
{
  "resolvedClips": [
    {
      "contentId": "inception",
      "clipStart": 3507,
      "clipEnd": 3521,
      "strategy": "SRT_DIALOGUE"
    }
  ]
}
```

**Strategy priority:** SRT_DIALOGUE → FALLBACK_POSITIONAL (key moment as-is)

**Dependencies:** Module 5 + Module 4 (optional, enhances clipping only).

---

### Module 7 — Narrative & Script Generator
**Responsibility:** Generate all human-facing content — tag, one-liner, text overlays, video arc. Tone and content differ significantly per recommendation type.

**Input:** Resolved clips + Correlation/Highlight Object + Classification Result

**Output — Narrative Plan:**
```json
{
  "tag": "Same twisted brilliance",
  "oneLiner": "If Inception left you questioning reality, Shutter Island will finish the job.",
  "videoArc": "Open with Inception's visual spectacle, hard transition with bold text, close on Shutter Island's dread.",
  "clipNarratives": [
    {
      "clipIndex": 1,
      "emotionalIntent": "Hook — familiar pull of unreality",
      "overlays": [
        {
          "text": "You thought you understood reality...",
          "position": "BOTTOM_CENTER",
          "appearAtSecond": 2,
          "holdSeconds": 3,
          "style": "CINEMATIC_BOLD"
        }
      ]
    }
  ],
  "transitionOverlay": {
    "text": "Think again.",
    "position": "CENTER",
    "style": "CINEMATIC_BOLD"
  }
}
```

**Dependencies:** Module 6.

---

### Module 8 — Manifest Builder & Validator
**Responsibility:** Assemble final manifest JSON from all upstream outputs. Validate against schema. Retry LLM calls with corrective prompts if output is invalid or references non-existent scene numbers.

**Input:** All upstream outputs — resolved clips, narrative plan, classification result

**Output — Final `manifest.json`** (as defined in the architecture doc)

**Validation rules:**
- All contentIds exist in pretag data
- clipStart < clipEnd for every clip
- All overlay appearAtSecond values fall within clip duration
- Required fields present per recommendation type

**Dependencies:** Module 7 + schema definition (can be drafted independently).

---

### Module 9 — API Layer
**Responsibility:** Expose the full pipeline as a single callable endpoint.

**Input:**
```json
{
  "userId": "u_123",
  "recommendedContentId": "shutter_island",
  "sourceFiles": ["because_you_watched.json", "related_content.json"]
}
```

**Output:** `manifest.json`

Async handling — LLM chains take time, this should not be a blocking synchronous call.

**Dependencies:** All modules complete.

---

## Full Dependency Map

```
Module 1 (Input Aggregator)
    └──→ Module 2 (Classifier)
              └──→ Module 3 (Pretag Loader)
                        └──→ Module 5 (Correlation/Highlight)
                                  └──→ Module 6 (Scene Selector + Clip Resolver) ←── Module 4 (SRT, optional)
                                            └──→ Module 7 (Narrative Generator)
                                                      └──→ Module 8 (Manifest Builder)
                                                                └──→ Module 9 (API Layer)

Module 4 (SRT Spike) — independent, feeds into Module 6 optionally
```

---

## What Can Start in Parallel Right Now

| Module | Can Start Now? | Why |
|---|---|---|
| Module 1 | Yes | Just needs JSON file access |
| Module 2 | After Module 1 | Needs unified context structure agreed |
| Module 3 | Yes | Just needs pretag file access |
| Module 4 | Yes | Fully independent |
| Module 8 | Yes | Schema can be drafted from the doc |
| Module 9 | Yes | API contract can be designed upfront |

Modules 5, 6, 7 are sequential and form the critical path — start these after 1, 2, 3 are solid.

---

Want to now define the prompt strategy and JSON schemas for each LLM call across modules 2, 5, 6, and 7?
