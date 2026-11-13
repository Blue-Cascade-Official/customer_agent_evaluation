from __future__ import annotations

import io
import re
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

FILLER_RE = re.compile(r"\b(um+|uh+|erm+|like|you know|sort of|kind of)\b", re.I)


def _normalize_turns(transcript: list[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
    if transcript is None:
        return []
    if isinstance(transcript, list):
        return transcript
    if isinstance(transcript, dict) and isinstance(transcript.get("transcript"), list):
        return transcript["transcript"]
    return []


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def evaluate_audio(
    audio_bytes: bytes | None,
    transcript: list[dict[str, Any]] | dict[str, Any] | None,
    duration_secs: float | None = None,
) -> dict[str, Any]:
    turns = _normalize_turns(transcript)
    user_turns = [t for t in turns if t.get("role") == "user"]
    agent_turns = [t for t in turns if t.get("role") == "agent"]

    user_text = " ".join((t.get("message") or "") for t in user_turns)
    total_user_words = _word_count(user_text)
    filler_count = len(FILLER_RE.findall(user_text))
    filler_word_rate = (filler_count / total_user_words) if total_user_words else 0.0

    # Timing from transcript timestamps
    user_times = [float(t.get("time_in_call_secs") or 0) for t in user_turns]
    agent_times = [float(t.get("time_in_call_secs") or 0) for t in agent_turns]
    interruption_count = sum(1 for t in turns if t.get("interrupted"))

    avg_pause_sec = 0.0
    if len(user_times) >= 2:
        gaps = [max(0.0, user_times[i] - user_times[i - 1]) for i in range(1, len(user_times))]
        avg_pause_sec = float(np.mean(gaps)) if gaps else 0.0

    latencies: list[float] = []
    for ut in user_turns:
        ut_t = float(ut.get("time_in_call_secs") or 0)
        prior_agents = [float(a.get("time_in_call_secs") or 0) for a in agent_turns if float(a.get("time_in_call_secs") or 0) <= ut_t]
        if prior_agents:
            latencies.append(max(0.0, ut_t - max(prior_agents)))
    avg_response_latency_sec = float(np.mean(latencies)) if latencies else 0.0

    # Estimate speaking duration from consecutive user turn spans
    speaking_secs = 0.0
    if len(user_times) >= 2:
        speaking_secs = max(1.0, user_times[-1] - user_times[0])
    elif duration_secs:
        speaking_secs = max(1.0, duration_secs * 0.4)
    else:
        speaking_secs = max(1.0, float(len(user_turns)) * 4.0)

    speaking_rate_wpm = (total_user_words / speaking_secs) * 60.0 if speaking_secs else 0.0

    # Signal features via librosa when audio is available
    silence_ratio = 0.0
    rms_variance = 0.0
    audio_duration = duration_secs or 0.0
    if audio_bytes:
        try:
            import librosa
            import soundfile as sf

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            try:
                # soundfile may not read mp3; use librosa.load which uses audioread/ffmpeg if needed
                y, sr = librosa.load(tmp_path, sr=16000, mono=True)
            except Exception:
                # Fallback: try as wav-like raw via BytesIO if already wav
                try:
                    y, sr = sf.read(io.BytesIO(audio_bytes), always_2d=False)
                    if getattr(y, "ndim", 1) > 1:
                        y = np.mean(y, axis=1)
                    y = y.astype(np.float32)
                except Exception:
                    y = np.array([], dtype=np.float32)
                    sr = 16000
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            if y.size > 0:
                audio_duration = float(len(y) / sr)
                frame_length = 2048
                hop_length = 512
                rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
                threshold = float(np.percentile(rms, 30))
                silence_frames = np.sum(rms < threshold)
                silence_ratio = float(silence_frames / max(1, len(rms)))
                rms_variance = float(np.var(rms))
        except Exception:
            # Keep transcript-only metrics if audio decode fails
            pass

    # Score heuristics (0-100)
    # Ideal WPM ~120-160
    if speaking_rate_wpm <= 0:
        fluency_wpm = 40.0
    elif 110 <= speaking_rate_wpm <= 170:
        fluency_wpm = 90.0
    elif 80 <= speaking_rate_wpm < 110 or 170 < speaking_rate_wpm <= 200:
        fluency_wpm = 70.0
    else:
        fluency_wpm = 50.0

    pause_penalty = min(40.0, avg_pause_sec * 6.0)
    silence_penalty = silence_ratio * 40.0
    filler_penalty = min(30.0, filler_word_rate * 200.0)
    fluency_score = max(0.0, min(100.0, fluency_wpm - pause_penalty * 0.3 - silence_penalty * 0.3 - filler_penalty))

    short_answer_ratio = 0.0
    if user_turns:
        short = sum(1 for t in user_turns if _word_count(t.get("message") or "") < 6)
        short_answer_ratio = short / len(user_turns)

    reluctance_score = max(
        0.0,
        min(
            100.0,
            silence_ratio * 40
            + min(30.0, avg_pause_sec * 5)
            + short_answer_ratio * 30
            + filler_word_rate * 100,
        ),
    )
    # Higher reluctance is worse for overall; invert partially
    overall_audio_score = max(
        0.0,
        min(
            100.0,
            fluency_score * 0.55
            + (100 - reluctance_score) * 0.25
            + max(0.0, 100 - interruption_count * 8) * 0.1
            + max(0.0, 100 - avg_response_latency_sec * 15) * 0.1,
        ),
    )

    summary = (
        f"Speaking rate about {speaking_rate_wpm:.0f} WPM with silence ratio {silence_ratio:.0%}. "
        f"Avg pause {avg_pause_sec:.1f}s, response latency {avg_response_latency_sec:.1f}s, "
        f"{interruption_count} interruptions, filler rate {filler_word_rate:.1%}. "
        f"Fluency {fluency_score:.0f}/100; reluctance {reluctance_score:.0f}/100."
    )

    return {
        "speaking_rate_wpm": round(speaking_rate_wpm, 1),
        "silence_ratio": round(silence_ratio, 3),
        "avg_pause_sec": round(avg_pause_sec, 2),
        "interruption_count": interruption_count,
        "avg_response_latency_sec": round(avg_response_latency_sec, 2),
        "filler_word_rate": round(filler_word_rate, 3),
        "rms_variance": round(rms_variance, 6),
        "reluctance_score": round(reluctance_score, 1),
        "fluency_score": round(fluency_score, 1),
        "overall_audio_score": round(overall_audio_score, 1),
        "audio_duration_secs": round(audio_duration, 1) if audio_duration else None,
        "user_word_count": total_user_words,
        "summary": summary,
    }
