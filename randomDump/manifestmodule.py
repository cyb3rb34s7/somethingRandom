"""
modules/manifest_builder/module.py  — T7 + T8

T7 — Narrative Generator: tag, one-liner, overlays, video arc (LLM call)
T8 — Manifest Assembler: combines everything into final manifest.json

New in this version:
  - titleCard (opening frame — "BECAUSE YOU WATCHED" etc.)
  - videoStyle (letterbox, colorGrade, musicMood, volumes)
  - TransitionType per clip (FADE_BLACK, FLASH_CUT, CROSSFADE etc.)
  - LOWER_THIRD as overlay position option
  - Mood mapped automatically from recommendation type
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel
from typing import Optional

from shared.schemas import (
    SceneSelectionOutput, EngineOutput, ClassificationResult,
    Manifest, ManifestClip, TransitionOverlay, EndCard, Overlay,
    OverlayPosition, OverlayStyle, OutputMode,
    VideoStyle, TitleCard, TransitionType, ColorGrade, MusicMood,
    RecommendationType,
)
from shared.ai_client import BaseAIClient
from shared.llm_caller import call_llm
from shared import config

logger = logging.getLogger(__name__)
TEMPERATURE = 0.7


# ---------------------------------------------------------------------------
# Mood + style mapping — recommendation type drives visual + audio feel
# ---------------------------------------------------------------------------

STYLE_MAP: dict[RecommendationType, tuple[MusicMood, ColorGrade]] = {
    RecommendationType.A_TO_B:               (MusicMood.DARK_THRILLER,    ColorGrade.COOL),
    RecommendationType.TRENDING:             (MusicMood.UPBEAT_ENERGETIC, ColorGrade.CINEMATIC),
    RecommendationType.POPULAR:              (MusicMood.CONFIDENT_BOLD,   ColorGrade.CINEMATIC),
    RecommendationType.CRITICALLY_ACCLAIMED: (MusicMood.EPIC_PRESTIGE,    ColorGrade.COOL),
    RecommendationType.SOCIALLY_BUZZING:     (MusicMood.UPBEAT_ENERGETIC, ColorGrade.WARM),
    RecommendationType.GENRE_MOOD_MATCH:     (MusicMood.ATMOSPHERIC,      ColorGrade.CINEMATIC),
    RecommendationType.FRANCHISE_CREATOR:    (MusicMood.FAMILIAR_WARM,    ColorGrade.WARM),
    RecommendationType.REWATCH:              (MusicMood.NOSTALGIC,        ColorGrade.WARM),
}

TITLE_CARD_TEXT: dict[RecommendationType, str] = {
    RecommendationType.A_TO_B:               "BECAUSE YOU WATCHED",
    RecommendationType.TRENDING:             "TRENDING NOW",
    RecommendationType.POPULAR:              "MOST WATCHED",
    RecommendationType.CRITICALLY_ACCLAIMED: "AWARD WINNING",
    RecommendationType.SOCIALLY_BUZZING:     "EVERYONE IS TALKING ABOUT",
    RecommendationType.GENRE_MOOD_MATCH:     "PICKED FOR YOUR MOOD",
    RecommendationType.FRANCHISE_CREATOR:    "MORE FROM THE UNIVERSE YOU LOVE",
    RecommendationType.REWATCH:              "WORTH WATCHING AGAIN",
}

TONE_GUIDE: dict[str, str] = {
    "A_TO_B":               "Intimate and comparative — draw a direct emotional line between the two contents",
    "TRENDING":             "Urgent — create FOMO, make viewer feel they are missing a cultural moment",
    "POPULAR":              "Confident — social proof, bold statements about quality",
    "CRITICALLY_ACCLAIMED": "Cinematic and prestige — reverent, authoritative",
    "SOCIALLY_BUZZING":     "Energetic — community, conversation, excitement",
    "GENRE_MOOD_MATCH":     "Atmospheric — sensory, mood-driven language",
    "FRANCHISE_CREATOR":    "Warm and familiar — fan-service, continuity",
    "REWATCH":              "Nostalgic — emotional recall, warmth",
}


# ---------------------------------------------------------------------------
# T7 — Raw LLM output schemas
# ---------------------------------------------------------------------------

class _RawOverlay(BaseModel):
    text:           str
    position:       OverlayPosition
    appearAtSecond: float
    holdSeconds:    float
    style:          OverlayStyle


class _RawClipNarrative(BaseModel):
    clipIndex:       int
    umdId:           str
    emotionalIntent: str
    transitionType:  TransitionType
    overlays:        list[_RawOverlay]


class _RawTransitionOverlay(BaseModel):
    text:     str
    position: OverlayPosition
    style:    OverlayStyle


class _RawEndCard(BaseModel):
    text:            str
    durationSeconds: int


class _RawNarrative(BaseModel):
    tag:               str
    oneLiner:          str
    videoArc:          str
    clipNarratives:    list[_RawClipNarrative]
    transitionOverlay: _RawTransitionOverlay
    endCard:           _RawEndCard


# ---------------------------------------------------------------------------
# T7 — Prompt
# ---------------------------------------------------------------------------

NARRATIVE_SYSTEM = """You are a creative director writing the script for a cinematic recommendation explanation video on a streaming platform.

Generate a tag, one-liner, and a complete overlay + transition plan. The video should feel like a movie trailer.

Overlay position guide:
- TOP_CENTER: Bold statement above the action — used for hooks
- BOTTOM_CENTER: Supporting text below — used for context mid-clip
- CENTER: Dead center — maximum impact, use sparingly
- LOWER_THIRD: Left-aligned bottom — cinematic supporting text, most natural feel

Overlay style guide:
- CINEMATIC_BOLD: Large all-caps, high-impact. Use for opening hooks and emotional peaks.
- SUBTLE: Smaller, elegant. Use for supporting context and mid-clip information.
- BRAND: Clean minimal. End cards only.

Transition type guide (pick per clip based on emotional intent):
- FLASH_CUT: Single white flash then hard cut — sharp, modern, high-energy
- CROSSFADE: Smooth dissolve — atmospheric, emotional
- FADE_BLACK: Fade to/from black — dramatic, weighty
- FADE_WHITE: Fade to/from white — bright, uplifting
- HARD_CUT: No transition — raw, intense

Rules:
- tag: 2-5 words, all caps, punchy
- oneLiner: single sentence, max 15 words, no clichés
- Each clip: 1-2 overlays MAXIMUM — do not clutter
- Text must be SHORT — max 6 words per overlay line
- appearAtSecond >= 1.5 (let the scene breathe before text appears)
- appearAtSecond + holdSeconds <= clip duration - 1 (text gone before clip ends)
- transitionOverlay text: 1-4 bold words shown DURING transition between clips
- First clip transitionType controls how video opens — use FADE_BLACK
- Last clip transitionType controls how video closes — use FADE_BLACK
- Output ONLY valid JSON, no preamble, no markdown fences

Schema:
{
  "tag": "<2-5 words all caps>",
  "oneLiner": "<single punchy sentence>",
  "videoArc": "<one sentence — emotional journey of the full video>",
  "clipNarratives": [
    {
      "clipIndex": <number>,
      "umdId": "<umdId>",
      "emotionalIntent": "<what this clip makes the viewer feel>",
      "transitionType": "FADE_BLACK|FLASH_CUT|CROSSFADE|FADE_WHITE|HARD_CUT",
      "overlays": [
        {
          "text": "<short overlay — max 6 words>",
          "position": "TOP_CENTER|BOTTOM_CENTER|CENTER|LOWER_THIRD",
          "appearAtSecond": <number>,
          "holdSeconds": <number>,
          "style": "CINEMATIC_BOLD|SUBTLE|BRAND"
        }
      ]
    }
  ],
  "transitionOverlay": {
    "text": "<1-4 bold words>",
    "position": "CENTER",
    "style": "CINEMATIC_BOLD"
  },
  "endCard": {
    "text": "<Content Title>",
    "durationSeconds": 2
  }
}"""


def _build_narrative_prompt(
    scenes: SceneSelectionOutput,
    engine_output: EngineOutput,
    classification: ClassificationResult,
) -> str:
    rec_type = classification.primaryType.value
    tone = TONE_GUIDE.get(rec_type, "Cinematic and compelling")

    if engine_output.mode == OutputMode.CORRELATION:
        top = engine_output.correlations[0]
        context_block = (
            f"Correlation reason: {top.reason}\n"
            f"Narrative angle: {top.narrativeAngle.value}\n"
            f"Theme connection: {top.themeA} ↔ {top.themeB}"
        )
    else:
        context_block = (
            f"Highlight angle: {engine_output.primaryAngle}\n"
            f"Tone direction: {engine_output.toneDirection.value}"
        )

    clips_block = "\n".join(
        f"Clip {i+1} — umdId: {s.umdId}\n"
        f"  Duration: {s.clipEnd - s.clipStart}s ({s.clipStart}s–{s.clipEnd}s)\n"
        f"  Scene: {s.title}\n"
        f"  Narrative purpose: {s.narrativePurpose}"
        + (f"\n  Extra context: {s.topSceneContext}" if s.topSceneContext else "")
        for i, s in enumerate(scenes.selectedScenes)
    )

    return f"""Write the cinematic explanation video script for this recommendation.

Recommendation type: {rec_type}
Tone: {tone}

{context_block}

Clips:
{clips_block}"""


# ---------------------------------------------------------------------------
# T7 — LLM call
# ---------------------------------------------------------------------------

def _generate_narrative(
    scenes: SceneSelectionOutput,
    engine_output: EngineOutput,
    classification: ClassificationResult,
    client: BaseAIClient,
) -> _RawNarrative:
    logger.info("Generating narrative script (T7)...")
    return call_llm(
        client=client,
        system_prompt=NARRATIVE_SYSTEM,
        user_prompt=_build_narrative_prompt(scenes, engine_output, classification),
        output_schema=_RawNarrative,
        temperature=TEMPERATURE,
    )


# ---------------------------------------------------------------------------
# T8 — Manifest assembly
# ---------------------------------------------------------------------------

def _validate_overlay(ov: _RawOverlay, clip_duration: int, umd_id: str) -> _RawOverlay:
    """Clamp overlay timings so they never exceed clip bounds."""
    max_appear = clip_duration - 2.0
    appear = min(max(1.5, ov.appearAtSecond), max_appear)
    hold   = min(ov.holdSeconds, clip_duration - appear - 0.5)
    hold   = max(1.0, hold)

    if appear != ov.appearAtSecond or hold != ov.holdSeconds:
        logger.warning(
            f"Overlay timing clamped for {umd_id}: "
            f"appear {ov.appearAtSecond}→{appear}, hold {ov.holdSeconds}→{hold}"
        )
    return _RawOverlay(
        text=ov.text, position=ov.position,
        appearAtSecond=appear, holdSeconds=hold, style=ov.style,
    )


def _assemble_manifest(
    narrative: _RawNarrative,
    scenes: SceneSelectionOutput,
    engine_output: EngineOutput,
    classification: ClassificationResult,
) -> Manifest:
    logger.info("Assembling manifest (T8)...")

    rec_type = classification.primaryType
    music_mood, color_grade = STYLE_MAP.get(
        rec_type, (MusicMood.CINEMATIC_NEUTRAL, ColorGrade.CINEMATIC)
    )

    video_style = VideoStyle(
        letterbox=True,
        colorGrade=color_grade,
        musicMood=music_mood,
        musicVolume=0.3,
        clipVolume=0.7,
    )

    title_card = TitleCard(
        text=TITLE_CARD_TEXT.get(rec_type, "RECOMMENDED FOR YOU"),
        durationSeconds=2.0,
        style=OverlayStyle.CINEMATIC_BOLD,
    )

    scene_map = {s.umdId: s for s in scenes.selectedScenes}

    clips = []
    for cn in narrative.clipNarratives:
        scene = scene_map.get(cn.umdId)
        if not scene:
            logger.warning(f"No scene found for umdId {cn.umdId} — skipping clip")
            continue

        clip_duration = scene.clipEnd - scene.clipStart
        validated_overlays = [
            Overlay(**_validate_overlay(ov, clip_duration, cn.umdId).model_dump())
            for ov in cn.overlays
        ]

        clips.append(ManifestClip(
            clipIndex=cn.clipIndex,
            umdId=cn.umdId,
            clipStart=scene.clipStart,
            clipEnd=scene.clipEnd,
            transitionIn=cn.transitionType.value,
            transitionOut=cn.transitionType.value,
            transitionDurationMs=1200,
            overlays=validated_overlays,
        ))

    transition_overlays = [
        TransitionOverlay(
            afterClipIndex=i + 1,
            text=narrative.transitionOverlay.text,
            position=narrative.transitionOverlay.position,
            style=narrative.transitionOverlay.style,
            durationMs=1200,
        )
        for i in range(len(clips) - 1)
    ]

    total_clip_duration = sum(s.clipEnd - s.clipStart for s in scenes.selectedScenes)
    estimated_total = round(
        total_clip_duration
        + title_card.durationSeconds
        + narrative.endCard.durationSeconds
        + (len(clips) - 1) * 1.2,
        1
    )

    correlation_reason = (
        engine_output.correlations[0].reason
        if engine_output.mode == OutputMode.CORRELATION
        else engine_output.primaryAngle
    )

    return Manifest(
        recommendationType=rec_type,
        tag=narrative.tag,
        oneLiner=narrative.oneLiner,
        clips=clips,
        transitionOverlays=transition_overlays,
        endCard=EndCard(
            text=narrative.endCard.text,
            durationSeconds=narrative.endCard.durationSeconds,
        ),
        metadata={
            "videoArc":                narrative.videoArc,
            "correlationReason":       correlation_reason,
            "estimatedDurationSeconds": estimated_total,
            "spoilerRiskFlags":        [s.spoilerRisk.value for s in scenes.selectedScenes],
            "generatedAt":             datetime.now().isoformat(),
            "videoStyle":              video_style.model_dump(),
            "titleCard":               title_card.model_dump(),
        },
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def run(
    scenes: SceneSelectionOutput,
    engine_output: EngineOutput,
    classification: ClassificationResult,
    client: BaseAIClient,
    output_dir: Path = None,
) -> Manifest:
    if not scenes.is_timestamps_complete():
        raise ValueError(
            "All scenes must have clipStart and clipEnd set before manifest generation. "
            "Edit the state file to add timestamps, then run phase 2."
        )

    output_dir = output_dir or config.OUTPUT_MANIFEST_DIR
    narrative  = _generate_narrative(scenes, engine_output, classification, client)
    manifest   = _assemble_manifest(narrative, scenes, engine_output, classification)

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_path = output_dir / f"manifest_{run_id}.json"

    with open(out_path, "w") as f:
        json.dump(manifest.model_dump(), f, indent=2, default=str)

    logger.info(f"Manifest saved → {out_path}")
    logger.info(f"Tag: {manifest.tag} | Est. duration: {manifest.metadata['estimatedDurationSeconds']}s")
    return manifest
