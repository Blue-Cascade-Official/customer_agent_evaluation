from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy.orm import Session

from app.models.eval_settings import EvalSettingsRow

AUDIO_PARAMS: list[dict[str, Any]] = [
    {
        "key": "speaking_rate_wpm",
        "label": "Speaking rate (WPM)",
        "description": "Words per minute from the internee's spoken turns. Ideal band is roughly 110–170 WPM.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "silence_ratio",
        "label": "Silence ratio",
        "description": "Share of call time with low audio energy. Higher values often mean hesitation or long gaps.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "avg_pause_sec",
        "label": "Average pause length",
        "description": "Average gap between the internee's successive speaking turns, in seconds.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "interruption_count",
        "label": "Interruptions",
        "description": "How often the internee interrupted or overlapped the agent.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "avg_response_latency_sec",
        "label": "Response latency",
        "description": "Average delay from the end of an agent turn to the internee's reply.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "filler_word_rate",
        "label": "Filler word rate",
        "description": "Density of fillers such as um, uh, like, you know in internee speech.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "rms_variance",
        "label": "Volume stability",
        "description": "Variance of audio energy (RMS). Unstable volume can signal nervous delivery.",
        "group": "audio",
        "default_enabled": False,
    },
    {
        "key": "reluctance_score",
        "label": "Reluctance",
        "description": "Composite of long pauses, short answers, silence, and fillers. Higher = more reluctance.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "fluency_score",
        "label": "English fluency",
        "description": "Composite fluency score from speaking rate, pause regularity, silence, and fillers.",
        "group": "audio",
        "default_enabled": True,
    },
    {
        "key": "overall_audio_score",
        "label": "Overall audio score",
        "description": "Weighted roll-up of enabled audio metrics into a single 0–100 score.",
        "group": "audio",
        "default_enabled": True,
    },
]

KNOWLEDGE_PARAMS: list[dict[str, Any]] = [
    {
        "key": "factual_accuracy",
        "label": "Factual accuracy",
        "description": "How well internee statements match retrieved company knowledge.",
        "group": "knowledge",
        "default_enabled": True,
    },
    {
        "key": "coverage",
        "label": "Topic coverage",
        "description": "Whether important company topics raised in the call were addressed correctly.",
        "group": "knowledge",
        "default_enabled": True,
    },
    {
        "key": "hallucination",
        "label": "Hallucination / inventing",
        "description": "Higher means more unsupported or invented claims relative to the knowledge base.",
        "group": "knowledge",
        "default_enabled": True,
    },
    {
        "key": "relevance",
        "label": "Relevance",
        "description": "Whether the internee stayed on company/product topics.",
        "group": "knowledge",
        "default_enabled": True,
    },
    {
        "key": "completeness",
        "label": "Completeness",
        "description": "Whether answers had enough detail for the agent's questions.",
        "group": "knowledge",
        "default_enabled": True,
    },
    {
        "key": "confidence_hedging",
        "label": "Confidence vs hedging",
        "description": "Higher = clearer, confident answers; lower = excessive hedging or content reluctance.",
        "group": "knowledge",
        "default_enabled": True,
    },
    {
        "key": "overall_knowledge_score",
        "label": "Overall knowledge score",
        "description": "Roll-up of enabled knowledge rubric scores into a single 0–100 score.",
        "group": "knowledge",
        "default_enabled": True,
    },
]

CATALOG = AUDIO_PARAMS + KNOWLEDGE_PARAMS


def default_enabled_map() -> dict[str, bool]:
    return {p["key"]: bool(p["default_enabled"]) for p in CATALOG}


def get_or_create_settings(db: Session) -> EvalSettingsRow:
    row = db.query(EvalSettingsRow).filter(EvalSettingsRow.id == 1).one_or_none()
    if row is None:
        row = EvalSettingsRow(id=1, enabled=default_enabled_map())
        db.add(row)
        db.commit()
        db.refresh(row)
    elif not row.enabled:
        row.enabled = default_enabled_map()
        db.commit()
        db.refresh(row)
    else:
        # Merge new catalog keys without wiping user choices
        merged = default_enabled_map()
        merged.update({k: bool(v) for k, v in (row.enabled or {}).items()})
        if merged != row.enabled:
            row.enabled = merged
            db.commit()
            db.refresh(row)
    return row


def settings_payload(db: Session) -> dict[str, Any]:
    row = get_or_create_settings(db)
    enabled = row.enabled or {}
    audio = []
    knowledge = []
    for param in CATALOG:
        item = {
            **param,
            "enabled": bool(enabled.get(param["key"], param["default_enabled"])),
        }
        if param["group"] == "audio":
            audio.append(item)
        else:
            knowledge.append(item)
    return {"audio": audio, "knowledge": knowledge, "enabled": enabled}


def update_settings(db: Session, enabled: dict[str, bool]) -> dict[str, Any]:
    row = get_or_create_settings(db)
    current = deepcopy(row.enabled or default_enabled_map())
    for key, value in enabled.items():
        if key in current:
            current[key] = bool(value)
    row.enabled = current
    db.commit()
    db.refresh(row)
    return settings_payload(db)


def filter_scores(scores: dict[str, Any] | None, enabled: dict[str, bool], group: str) -> dict[str, Any]:
    if not scores:
        return {}
    keys = {p["key"] for p in CATALOG if p["group"] == group}
    out: dict[str, Any] = {}
    for key, value in scores.items():
        if key in ("summary", "citations", "retrieved_chunk_ids", "model"):
            out[key] = value
            continue
        if key not in keys:
            out[key] = value
            continue
        if enabled.get(key, True):
            out[key] = value
    return out
