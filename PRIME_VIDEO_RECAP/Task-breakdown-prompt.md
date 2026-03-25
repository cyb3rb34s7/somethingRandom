# Explainable Recommendation Pipeline
## Prompt Strategy, JSON Schemas & Task Assignment

---

## Task Assignment Table

| # | Module | One-liner | Input | Output |
|---|---|---|---|---|
| T1 | Input Aggregator | Collect and normalize all recommendation JSON files and content metadata into one unified context object | Recommendation event + because_you_watched.json + related_content.json + content metadata store | Unified Recommendation Context JSON |
| T2 | Recommendation Type Classifier | LLM call that reads unified context and decides the dominant recommendation type (A→B, Trending, Acclaimed etc.) | Unified Recommendation Context | Classification Result with type, confidence, evidence |
| T3 | Pretag Data Loader | Load and normalize scenes.json, theme.json, key_moments.json for relevant content(s) based on classification type | Classification Result + pretag file storage | Normalized Pretag Context for 1 or 2 contents |
| T4 | SRT Spike & Subtitle Fetcher | Investigate if subtitles can be extracted from stream URLs; if yes, build fetcher that slices dialogue to scene windows | Stream URL + contentId + scene startTime/endTime | Timestamped dialogue lines for a scene window, or NO_SRT decision |
| T5 | Correlation & Highlight Engine | LLM call that finds why two contents are related (A→B) or extracts the highlight angle (other types) using themes + metadata | Pretag Context + Classification Result + content metadata | Correlation Object (A→B) or Highlight Signal Object (others) |
| T6A | Scene Selector | LLM call that picks the best key moment(s) from each content based on correlation/highlight reason, with spoiler flagging | Correlation/Highlight Object + Pretag Context | Selected scenes with spoiler risk and narrative purpose |
| T6B | Clip Resolver | Determines precise clip window (clipStart, clipEnd) per selected scene using SRT dialogue if available, else full key moment | Selected scenes + SRT dialogue (optional) | Resolved clips with timestamps and clipping strategy used |
| T7 | Narrative & Script Generator | LLM call that generates tag, one-liner, text overlays, timing, positions and video arc — tone varies per recommendation type | Resolved clips + Correlation/Highlight Object + Classification Result | Narrative Plan with overlays per clip |
| T8 | Manifest Builder & Validator | Assembles final manifest.json, validates schema, retries LLM calls with corrective prompts if output is invalid | All upstream outputs | Final validated manifest.json |
| T9 | API Layer | FastAPI wrapper exposing the full pipeline as an async endpoint | Recommendation event (userId, recommendedContentId, sourceFiles) | manifest.json |

---

## LLM Call Design

There are **5 LLM calls** in this pipeline. Each section below defines the system prompt, user prompt structure, expected output schema, and validation rules.

---

### LLM Call 1 — Recommendation Type Classifier (T2)

**Goal:** Given what we know about the recommendation event and content metadata, decide the single most compelling recommendation type to build the explanation video around.

**Model guidance:** Keep input small — only send theme names (not full scene data), metadata summary, and available signal types. This call should be fast and cheap.

---

**System Prompt:**
```
You are a recommendation classification engine for a video streaming platform.

Your job is to analyze a recommendation event and classify it into exactly ONE primary recommendation type from this list:
- A_TO_B: User watched content A, recommended content B based on watch history or similarity
- TRENDING: Content is currently spiking in views or engagement
- POPULAR: Content has high all-time viewership or vote count
- CRITICALLY_ACCLAIMED: Content has high critic scores, awards wins or nominations
- SOCIALLY_BUZZING: Content has high community discussion or social mentions
- GENRE_MOOD_MATCH: Recommendation is based on user's genre or mood watching patterns
- FRANCHISE_CREATOR: Same director, actor, franchise or shared creative universe
- REWATCH: User previously watched this content and has high affinity for it

Rules:
- Always pick the SINGLE most compelling type — the one that would make the best explanation video
- If multiple types qualify, prefer the one with the strongest evidence
- A_TO_B takes priority when because_you_watched signal is present AND there is clear content similarity
- Output ONLY valid JSON, no preamble, no explanation outside the JSON

Output schema:
{
  "primaryType": "<TYPE>",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "evidence": "<one sentence explaining why this type was chosen>",
  "secondaryType": "<TYPE or null>",
  "secondaryEvidence": "<one sentence or null>",
  "sourceContentId": "<contentId or null — only for A_TO_B and FRANCHISE_CREATOR>",
  "recommendedContentId": "<contentId>"
}
```

**User Prompt Template:**
```
Classify the following recommendation event.

Available signals: {{availableSignals}}

Recommended content:
- ID: {{recommendedContentId}}
- Genre: {{recommendedGenre}}
- Description: {{recommendedDescription}}
- Rating: {{recommendedRating}}
- Awards: {{recommendedAwards}}
- Top themes: {{recommendedTopThemes}}

Source content (if available):
- ID: {{sourceContentId}}
- Genre: {{sourceGenre}}
- Description: {{sourceDescription}}
- Top themes: {{sourceTopThemes}}
- Shared cast: {{sharedCast}}
- Shared genre: {{sharedGenre}}
```

**Validation rules:**
- `primaryType` must be one of the 8 defined types
- `sourceContentId` must be non-null when primaryType is A_TO_B
- `confidence` must be HIGH, MEDIUM, or LOW
- Retry once with corrective prompt if JSON is malformed

---

### LLM Call 2 — Correlation & Highlight Engine (T5)

This call has two modes depending on classification result. Use separate prompts per mode.

---

#### Mode A — A_TO_B Correlation

**Goal:** Find the strongest thematic and metadata-level reason why content B was recommended after watching content A.

**System Prompt:**
```
You are a film analyst for a video streaming platform.

Your job is to find the most compelling correlation between two pieces of content — explaining why a viewer who enjoyed content A would also enjoy content B.

You will be given:
- The top-ranked themes from each content's pretag analysis
- Metadata for both contents (genre, cast, description, awards)

Rules:
- Find up to 3 correlation reasons, ranked by strength
- Use BOTH theme overlap AND metadata signals (shared cast, genre, tonal similarity)
- narrativeAngle should be DOMINANT_MATCH when correlation is on rank-1 themes of both contents
- narrativeAngle should be HIDDEN_CONNECTION when correlation is on secondary themes — this signals a more surprising, intriguing narrative angle
- Do NOT reference specific plot points that could be spoilers
- Output ONLY valid JSON

Output schema:
{
  "correlations": [
    {
      "rank": 1,
      "themeA": "<theme name from content A>",
      "themeB": "<theme name from content B>",
      "reason": "<one sentence explaining the connection a viewer would feel>",
      "metadataSignals": "<shared cast, genre or tonal notes that reinforce this>",
      "confidence": "HIGH" | "MEDIUM" | "LOW",
      "narrativeAngle": "DOMINANT_MATCH" | "HIDDEN_CONNECTION"
    }
  ]
}
```

**User Prompt Template:**
```
Find correlations between these two contents.

Content A — {{contentIdA}}
Themes (ranked): {{themeListA}}
Genre: {{genreA}}
Cast: {{castA}}
Description: {{descriptionA}}

Content B — {{contentIdB}}
Themes (ranked): {{themeListB}}
Genre: {{genreB}}
Cast: {{castB}}
Description: {{descriptionB}}
```

---

#### Mode B — Non A_TO_B Highlight Extraction

**Goal:** Identify the primary narrative angle for a single content based on its recommendation type signal.

**System Prompt:**
```
You are a film marketing analyst for a video streaming platform.

Your job is to identify the most compelling narrative angle for an explanation video about a content recommendation.

You will be given the recommendation type, content metadata, and top themes.

Tone directions per type:
- TRENDING: Urgent, FOMO — "the moment everyone is talking about"
- POPULAR: Confident, social proof — "millions of viewers can't be wrong"
- CRITICALLY_ACCLAIMED: Prestige, cinematic — "recognized as genuinely great"
- SOCIALLY_BUZZING: Energetic, community — "fans can't stop discussing this"
- GENRE_MOOD_MATCH: Atmospheric, mood-first — "matches exactly what you're in the mood for"
- FRANCHISE_CREATOR: Familiar, fan-service — "more of what you already love"
- REWATCH: Nostalgic, warm — "some stories are worth experiencing twice"

Output ONLY valid JSON.

Output schema:
{
  "narrativeType": "<recommendation type>",
  "primaryAngle": "<one sentence — the core message of the explanation video>",
  "dominantTheme": "<top theme name from pretag data>",
  "toneDirection": "<PRESTIGE | URGENT | SOCIAL_PROOF | ENERGETIC | ATMOSPHERIC | FAMILIAR | NOSTALGIC>",
  "highlightSignals": {
    "rating": "<rating value if relevant>",
    "awards": "<key award if relevant or null>",
    "popularityNote": "<short note on popularity signal or null>"
  }
}
```

**User Prompt Template:**
```
Extract the highlight angle for this recommendation.

Recommendation type: {{recommendationType}}
Content ID: {{contentId}}
Description: {{description}}
Genre: {{genre}}
Rating: {{rating}}
Awards: {{awards}}
Top themes (ranked): {{themeList}}
External signals: {{externalSignals}}
```

---

### LLM Call 3 — Scene Selector (T6A)

**Goal:** Given the correlation or highlight reason, pick the best key moment(s) from each content for the explanation video.

**System Prompt:**
```
You are a film editor selecting scenes for a short recommendation explanation video on a streaming platform.

Your job is to select the single best key moment from each content that visually communicates the recommendation reason without spoiling the story.

Rules:
- Prefer scenes that establish atmosphere, character, or premise — NOT scenes that resolve the story
- Flag spoilerRisk as HIGH if the description implies: a twist, a death, a final confrontation, or a revelation
- If spoilerRisk is HIGH, do NOT select that scene — pick the next best option
- For A_TO_B: select one key moment from each content
- For other types: select 1-2 key moments from the recommended content only
- narrativePurpose should explain what this clip will make the viewer FEEL, not what happens in it
- Output ONLY valid JSON

Output schema:
{
  "selectedScenes": [
    {
      "contentId": "<contentId>",
      "keyMomentNumber": <number>,
      "title": "<scene title>",
      "startTime": <seconds>,
      "endTime": <seconds>,
      "durationSeconds": <number>,
      "spoilerRisk": "LOW" | "MEDIUM" | "HIGH",
      "spoilerReason": "<why flagged or null>",
      "narrativePurpose": "<what this clip makes the viewer feel>"
    }
  ]
}
```

**User Prompt Template:**
```
Select the best key moment(s) for this explanation video.

Recommendation reason: {{correlationReasonOrHighlightAngle}}
Recommendation type: {{recommendationType}}

{{#if A_TO_B}}
Key moments from Content A ({{contentIdA}}):
{{keyMomentsA}}

Key moments from Content B ({{contentIdB}}):
{{keyMomentsB}}
{{else}}
Key moments from {{contentId}}:
{{keyMoments}}
{{/if}}
```

---

### LLM Call 4 — Clip Resolver (T6B)

**This call only happens when SRT dialogue is available.** If no SRT, clip resolution is rule-based (use full key moment, output USE_OPENING or USE_CLOSING based on simple positional heuristic from scene description).

**Goal:** Given a scene's subtitle dialogue, identify the single most hook-worthy moment and output a precise clip window around it.

**System Prompt:**
```
You are a film editor selecting the best 12-15 second clip window from a scene for a streaming platform recommendation video.

You will be given the scene description and timestamped dialogue from within that scene.

Rules:
- Pick the single most hook-worthy, emotionally resonant, or intriguing line of dialogue
- Output a clip window of 12-15 seconds centered around that line
- Do NOT pick lines that reveal plot twists, deaths, or story resolutions
- clipStart and clipEnd must fall within the scene's startTime and endTime bounds
- Output ONLY valid JSON

Output schema:
{
  "contentId": "<contentId>",
  "selectedLine": "<the dialogue line chosen>",
  "selectedLineTimestamp": <seconds>,
  "clipStart": <seconds>,
  "clipEnd": <seconds>,
  "clipDurationSeconds": <number>,
  "strategy": "SRT_DIALOGUE",
  "reasoning": "<one sentence on why this line was chosen>"
}
```

**User Prompt Template:**
```
Select the best clip window from this scene.

Content: {{contentId}}
Scene: {{sceneTitle}}
Scene description: {{sceneDescription}}
Scene bounds: {{startTime}}s → {{endTime}}s

Dialogue within scene:
{{#each dialogueLines}}
{{timestamp}}s: "{{text}}"
{{/each}}
```

**Fallback (no SRT) — rule-based, no LLM needed:**
```
if scene description contains words like ["realizes", "discovers", "reveals", "finally", "confronts"]:
    positionHint = USE_CLOSING
else:
    positionHint = USE_OPENING

clipStart = startTime + (duration * 0.6) if USE_CLOSING else startTime
clipEnd = min(clipStart + 20, endTime)
strategy = FALLBACK_POSITIONAL
```

---

### LLM Call 5 — Narrative & Script Generator (T7)

**Goal:** Generate all human-facing content — tag, one-liner, text overlays with timing and position per clip. This is the most creative call and the tone must match the recommendation type.

**System Prompt:**
```
You are a creative director writing the script for a short explanation video on a streaming platform.

Your job is to generate a tag, one-liner, and text overlay plan for a recommendation explanation video.

Tone guide per type:
- A_TO_B: Intimate and comparative — draw a direct emotional line between the two contents
- TRENDING: Urgent — create FOMO, make the viewer feel they are missing a cultural moment
- POPULAR: Confident — social proof, bold statements about quality
- CRITICALLY_ACCLAIMED: Cinematic and prestige — reverent, authoritative
- SOCIALLY_BUZZING: Energetic — community, conversation, excitement
- GENRE_MOOD_MATCH: Atmospheric — sensory, mood-driven language
- FRANCHISE_CREATOR: Warm and familiar — fan-service, continuity
- REWATCH: Nostalgic — emotional recall, warmth

Overlay style guide:
- CINEMATIC_BOLD: Large, centered, high-impact text. Use for opening hooks and transitions.
- SUBTLE: Smaller, lower-third text. Use for supporting context mid-clip.
- BRAND: Clean, minimal. End cards only.

Rules:
- Tag must be 2-5 words maximum
- One-liner must be a single sentence, punchy, no more than 15 words
- Each clip should have 1-2 overlays maximum — do not clutter
- appearAtSecond must be >= 1 (never show text at exact clip start)
- appearAtSecond + holdSeconds must be <= clip duration
- transitionOverlay appears during the crossfade between clips — keep it 1-3 words, bold
- Output ONLY valid JSON

Output schema:
{
  "tag": "<2-5 word tag>",
  "oneLiner": "<single punchy sentence>",
  "videoArc": "<one sentence describing the emotional journey of the full video>",
  "clipNarratives": [
    {
      "clipIndex": <number>,
      "contentId": "<contentId>",
      "emotionalIntent": "<what this clip should make the viewer feel>",
      "overlays": [
        {
          "text": "<overlay text>",
          "position": "TOP_CENTER" | "BOTTOM_CENTER" | "CENTER",
          "appearAtSecond": <number>,
          "holdSeconds": <number>,
          "style": "CINEMATIC_BOLD" | "SUBTLE" | "BRAND"
        }
      ]
    }
  ],
  "transitionOverlay": {
    "text": "<1-3 words>",
    "position": "CENTER",
    "style": "CINEMATIC_BOLD"
  },
  "endCard": {
    "text": "<content title — Watch Now>",
    "durationSeconds": 2,
    "style": "BRAND"
  }
}
```

**User Prompt Template:**
```
Write the explanation video script for this recommendation.

Recommendation type: {{recommendationType}}
{{#if A_TO_B}}
Correlation reason: {{topCorrelationReason}}
Narrative angle: {{narrativeAngle}}
{{else}}
Highlight angle: {{primaryAngle}}
Tone direction: {{toneDirection}}
{{/if}}

Clips:
{{#each resolvedClips}}
Clip {{clipIndex}} — {{contentId}}
Duration: {{clipDuration}}s
Narrative purpose: {{narrativePurpose}}
{{/each}}
```

---

## Retry & Validation Strategy (T8)

Every LLM call output must pass validation before being passed downstream. Here is the retry logic:

```
function validateAndRetry(llmOutput, schema, originalPrompt, maxRetries = 2):
    for attempt in range(maxRetries):
        errors = validate(llmOutput, schema)
        if no errors:
            return llmOutput
        
        correctionPrompt = f"""
        Your previous output had the following errors:
        {errors}
        
        Original prompt was:
        {originalPrompt}
        
        Fix only the errors listed. Output ONLY valid JSON matching the required schema.
        """
        llmOutput = callLLM(correctionPrompt)
    
    raise PipelineError("LLM output failed validation after max retries")
```

**Key validation rules per call:**

| Call | Critical Validations |
|---|---|
| Classifier (T2) | primaryType in allowed list, sourceContentId present for A_TO_B |
| Correlation (T5) | At least 1 correlation, narrativeAngle in allowed values |
| Scene Selector (T6A) | All contentIds exist in pretag data, startTime < endTime |
| Clip Resolver (T6B) | clipStart >= scene startTime, clipEnd <= scene endTime, duration 10-20s |
| Narrative Generator (T7) | appearAtSecond >= 1, appearAtSecond + holdSeconds <= clip duration, tag <= 5 words |

---

## Prompt Engineering Notes

A few things that will save iteration time when building these prompts:

**Always end system prompts with "Output ONLY valid JSON"** — even with structured output modes enabled, this reduces preamble and explanation text leaking into the response.

**Pass metadata summaries, not raw JSON blobs** — for the correlation call especially, format the theme list as a clean readable list rather than dumping the full theme.json. LLMs reason better over clean formatted text than nested JSON.

**Scene descriptions are your most valuable signal** — they are richer than theme names alone. Always include the scene description text in scene selection and clip resolver calls, not just the title.

**The narrative generator needs emotional vocabulary** — the `narrativePurpose` field from scene selection is the bridge between "what scene this is" and "what the script should say about it." Make sure T6A outputs this field thoughtfully — it directly shapes the quality of T7's output.

**Temperature settings:**
- T2 (Classifier): 0.1 — deterministic, factual
- T5 (Correlation): 0.3 — some reasoning flexibility
- T6A (Scene Selector): 0.1 — deterministic, rule-following
- T6B (Clip Resolver): 0.1 — deterministic, timestamp math
- T7 (Narrative): 0.7 — creative, varied output desired
