"""
shared/schemas.py

Single source of truth for all data contracts between modules.
Every module imports from here — nothing defines its own schemas.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RecommendationType(str, Enum):
    A_TO_B                = "A_TO_B"
    TRENDING              = "TRENDING"
    POPULAR               = "POPULAR"
    CRITICALLY_ACCLAIMED  = "CRITICALLY_ACCLAIMED"
    SOCIALLY_BUZZING      = "SOCIALLY_BUZZING"
    GENRE_MOOD_MATCH      = "GENRE_MOOD_MATCH"
    FRANCHISE_CREATOR     = "FRANCHISE_CREATOR"
    REWATCH               = "REWATCH"

class Confidence(str, Enum):
    HIGH   = "HIGH"
    MEDIUM = "MEDIUM"
    LOW    = "LOW"

class NarrativeAngle(str, Enum):
    DOMINANT_MATCH    = "DOMINANT_MATCH"
    HIDDEN_CONNECTION = "HIDDEN_CONNECTION"

class ToneDirection(str, Enum):
    PRESTIGE     = "PRESTIGE"
    URGENT       = "URGENT"
    SOCIAL_PROOF = "SOCIAL_PROOF"
    ENERGETIC    = "ENERGETIC"
    ATMOSPHERIC  = "ATMOSPHERIC"
    FAMILIAR     = "FAMILIAR"
    NOSTALGIC    = "NOSTALGIC"

class SpoilerRisk(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"

class OverlayPosition(str, Enum):
    TOP_CENTER    = "TOP_CENTER"
    BOTTOM_CENTER = "BOTTOM_CENTER"
    CENTER        = "CENTER"
    LOWER_THIRD   = "LOWER_THIRD"   # left-aligned bottom — cinematic feel

class OverlayStyle(str, Enum):
    CINEMATIC_BOLD = "CINEMATIC_BOLD"
    SUBTLE         = "SUBTLE"
    BRAND          = "BRAND"

class OutputMode(str, Enum):
    CORRELATION = "CORRELATION"
    HIGHLIGHT   = "HIGHLIGHT"

class PipelineStatus(str, Enum):
    AWAITING_TIMESTAMPS = "AWAITING_TIMESTAMPS"
    COMPLETE            = "COMPLETE"


# ---------------------------------------------------------------------------
# UMD metadata models
# ---------------------------------------------------------------------------

class UMDAward(BaseModel):
    organization: str
    name:         str
    year:         Optional[int] = None
    status:       Optional[str] = None   # "nominated" | "won"

class UMDDescription(BaseModel):
    text:     str
    language: str
    type:     str    # "plot"
    size:     int    # word count proxy — 10 = short, 100 = long

class UMDTitle(BaseModel):
    title:    str
    language: str
    type:     str    # "main"

class UMDCoreInfo(BaseModel):
    program_type:    str
    program_subtype: Optional[str] = None
    release_date:    Optional[str] = None
    running_time:    Optional[int] = None   # seconds
    genres:          list[str]     = []

class UMDProgram(BaseModel):
    program_id:   int
    core_info:    UMDCoreInfo
    titles:       list[UMDTitle]       = []
    descriptions: list[UMDDescription] = []
    awards:       list[UMDAward]       = []

    @property
    def umd_id(self) -> str:
        return str(self.program_id)

    @property
    def main_title(self) -> str:
        for t in self.titles:
            if t.type == "main" and t.language == "en":
                return t.title
        return self.titles[0].title if self.titles else str(self.program_id)

    @property
    def short_description(self) -> str:
        candidates = sorted(
            [d for d in self.descriptions if d.type == "plot"],
            key=lambda d: d.size,
        )
        return candidates[0].text if candidates else ""

    @property
    def long_description(self) -> str:
        candidates = sorted(
            [d for d in self.descriptions if d.type == "plot"],
            key=lambda d: d.size, reverse=True,
        )
        return candidates[0].text if candidates else ""

    @property
    def genres(self) -> list[str]:
        return self.core_info.genres

    @property
    def formatted_awards(self) -> list[str]:
        return [
            f"{a.organization} - {a.name} ({a.year or 'N/A'}, {a.status or 'N/A'})"
            for a in self.awards
        ]


# ---------------------------------------------------------------------------
# Normalized internal content metadata (derived from UMDProgram)
# ---------------------------------------------------------------------------

class ContentMetadata(BaseModel):
    umdId:            str
    title:            str
    shortDescription: str
    longDescription:  str
    genres:           list[str]
    awards:           list[str]      # pre-formatted strings
    runningTime:      Optional[int]  = None
    releaseDate:      Optional[str]  = None

    @classmethod
    def from_umd(cls, program: UMDProgram) -> "ContentMetadata":
        return cls(
            umdId=program.umd_id,
            title=program.main_title,
            shortDescription=program.short_description,
            longDescription=program.long_description,
            genres=program.genres,
            awards=program.formatted_awards,
            runningTime=program.core_info.running_time,
            releaseDate=program.core_info.release_date,
        )


# ---------------------------------------------------------------------------
# Pretag scene model — normalized from raw PascalCase pretag files
# ---------------------------------------------------------------------------

class Theme(BaseModel):
    name: str
    rank: int

class Scene(BaseModel):
    number:      int
    title:       str
    description: str
    thumbnail:   Optional[str]   = None
    startTime:   int
    endTime:     int
    tags:        list[str]       = []
    score:       Optional[float] = None   # present on theme-grouped scenes
    rank:        Optional[int]   = None   # present on theme-grouped scenes

    @property
    def duration(self) -> int:
        return self.endTime - self.startTime

    @classmethod
    def from_raw(cls, raw: dict) -> "Scene":
        """Normalize PascalCase raw pretag dict to Scene."""
        return cls(
            number=raw.get("Number", raw.get("number", 0)),
            title=raw.get("Title", raw.get("title", "")),
            description=raw.get("Description", raw.get("description", "")),
            thumbnail=raw.get("ThumbNail", raw.get("thumbnail")),
            startTime=raw.get("startTime", raw.get("StartTime", 0)),
            endTime=raw.get("endTime", raw.get("EndTime", raw.get("enTime", 0))),
            tags=raw.get("tag", raw.get("Tag", raw.get("tags", []))),
            score=raw.get("score", raw.get("Score")),
            rank=raw.get("rank", raw.get("Rank")),
        )


# ---------------------------------------------------------------------------
# T1 — Input Aggregator output
# ---------------------------------------------------------------------------

class UnifiedContext(BaseModel):
    recommendationType: RecommendationType
    recommendedContent: ContentMetadata
    sourceContent:      Optional[ContentMetadata] = None
    availableSignals:   list[str]                 = []

    @model_validator(mode="after")
    def validate_a_to_b(self):
        if self.recommendationType == RecommendationType.A_TO_B and not self.sourceContent:
            raise ValueError("sourceContent required for A_TO_B")
        return self


# ---------------------------------------------------------------------------
# T2 — Classifier output
# ---------------------------------------------------------------------------

class ClassificationResult(BaseModel):
    primaryType:          RecommendationType
    confidence:           Confidence
    evidence:             str
    secondaryType:        Optional[RecommendationType] = None
    secondaryEvidence:    Optional[str]                = None
    sourceContentId:      Optional[str]                = None   # umdId
    recommendedContentId: str                                   # umdId


# ---------------------------------------------------------------------------
# T3 — Pretag Loader output
# ---------------------------------------------------------------------------

class ContentPretag(BaseModel):
    umdId:      str
    themes:     list[Theme]
    scenes:     list[Scene]          # from scenes.json — short clips, primary stitching unit
    topScenes:  list[Scene]          # from top-scenes.json — longer, context only

    def scenes_for_theme(self, theme_name: str) -> list[Scene]:
        """Return scenes belonging to a theme, sorted by score desc."""
        return sorted(
            [s for s in self.scenes if s.rank is not None],
            key=lambda s: (s.score or 0), reverse=True,
        )

    def enrich_scene_with_top_context(self, scene: Scene) -> Optional[str]:
        """
        Find a top-scene that overlaps with this scene's time window.
        Returns its description as additional context, or None.
        """
        for ts in self.topScenes:
            if ts.startTime <= scene.startTime and ts.endTime >= scene.endTime:
                return ts.description
            if scene.startTime <= ts.startTime <= scene.endTime:
                return ts.description
        return None


class PretagContext(BaseModel):
    recommendedContent: ContentPretag
    sourceContent:      Optional[ContentPretag] = None


# ---------------------------------------------------------------------------
# T5 — Correlation / Highlight Engine output
# ---------------------------------------------------------------------------

class CorrelationEntry(BaseModel):
    rank:            int
    themeA:          str
    themeB:          str
    reason:          str
    metadataSignals: str
    confidence:      Confidence
    narrativeAngle:  NarrativeAngle

class CorrelationOutput(BaseModel):
    mode:                 OutputMode = OutputMode.CORRELATION
    recommendationType:   RecommendationType
    sourceContentId:      str
    recommendedContentId: str
    correlations:         list[CorrelationEntry]

    @field_validator("correlations")
    @classmethod
    def at_least_one(cls, v):
        if not v:
            raise ValueError("correlations must have at least one entry")
        return sorted(v, key=lambda c: c.rank)

class HighlightSignals(BaseModel):
    awards:        Optional[str]  = None
    popularityNote: Optional[str] = None

class HighlightOutput(BaseModel):
    mode:                 OutputMode = OutputMode.HIGHLIGHT
    recommendationType:   RecommendationType
    recommendedContentId: str
    primaryAngle:         str
    dominantTheme:        str
    toneDirection:        ToneDirection
    highlightSignals:     HighlightSignals

EngineOutput = CorrelationOutput | HighlightOutput


# ---------------------------------------------------------------------------
# T6A — Scene Selector output
# ---------------------------------------------------------------------------

class SelectedScene(BaseModel):
    umdId:            str
    sceneNumber:      int
    title:            str
    startTime:        int            # full scene bounds — human reference
    endTime:          int
    durationSeconds:  int
    thumbnail:        Optional[str]  = None
    topSceneContext:  Optional[str]  = None   # enriched context from top-scenes
    spoilerRisk:      SpoilerRisk
    spoilerReason:    Optional[str]  = None
    narrativePurpose: str
    clipStart:        Optional[int]  = None   # set manually after human review
    clipEnd:          Optional[int]  = None   # set manually after human review

class SceneSelectionOutput(BaseModel):
    selectedScenes: list[SelectedScene]

    def is_timestamps_complete(self) -> bool:
        return all(
            s.clipStart is not None and s.clipEnd is not None
            for s in self.selectedScenes
        )


# ---------------------------------------------------------------------------
# T7 / T8 — Manifest Builder output
# ---------------------------------------------------------------------------

class Overlay(BaseModel):
    text:           str
    position:       OverlayPosition
    appearAtSecond: float
    holdSeconds:    float
    style:          OverlayStyle

class ManifestClip(BaseModel):
    clipIndex:            int
    umdId:                str
    clipStart:            int
    clipEnd:              int
    transitionIn:         str
    transitionOut:        str
    transitionDurationMs: int
    overlays:             list[Overlay]

class TransitionOverlay(BaseModel):
    afterClipIndex: int
    text:           str
    position:       OverlayPosition
    style:          OverlayStyle
    durationMs:     int

class EndCard(BaseModel):
    text:            str
    durationSeconds: int
    style:           OverlayStyle = OverlayStyle.BRAND

class Manifest(BaseModel):
    manifestVersion:    str = "1.0"
    recommendationType: RecommendationType
    tag:                str
    oneLiner:           str
    clips:              list[ManifestClip]
    transitionOverlays: list[TransitionOverlay]
    endCard:            EndCard
    metadata:           dict


# ---------------------------------------------------------------------------
# Additions for stitching pipeline support
# ---------------------------------------------------------------------------

class TransitionType(str, Enum):
    FADE_BLACK  = "FADE_BLACK"    # fade to/from black — atmospheric
    FADE_WHITE  = "FADE_WHITE"    # fade to/from white — bright/energetic
    FLASH_CUT   = "FLASH_CUT"    # single white flash frame — sharp, modern
    CROSSFADE   = "CROSSFADE"    # dissolve — smooth
    HARD_CUT    = "HARD_CUT"     # no transition — raw, intense


class ColorGrade(str, Enum):
    CINEMATIC   = "CINEMATIC"    # contrast up, saturation down slightly
    WARM        = "WARM"         # pushed warm — nostalgic/familiar feel
    COOL        = "COOL"         # pushed cool — thriller/prestige feel
    NONE        = "NONE"         # no grading — use source as-is


class MusicMood(str, Enum):
    DARK_THRILLER      = "dark_thriller"
    EPIC_PRESTIGE      = "epic_prestige"
    UPBEAT_ENERGETIC   = "upbeat_energetic"
    ATMOSPHERIC        = "atmospheric"
    FAMILIAR_WARM      = "familiar_warm"
    NOSTALGIC          = "nostalgic"
    CONFIDENT_BOLD     = "confident_bold"
    CINEMATIC_NEUTRAL  = "cinematic_neutral"


class VideoStyle(BaseModel):
    letterbox:   bool        = True              # 2.39:1 cinematic bars
    colorGrade:  ColorGrade  = ColorGrade.CINEMATIC
    musicMood:   MusicMood   = MusicMood.CINEMATIC_NEUTRAL
    musicVolume: float       = 0.3               # 0.0–1.0, music track volume
    clipVolume:  float       = 0.7               # 0.0–1.0, original clip audio volume


class TitleCard(BaseModel):
    text:            str
    durationSeconds: float = 2.0
    style:           OverlayStyle = OverlayStyle.CINEMATIC_BOLD
