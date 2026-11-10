"""Tests for video module — command generation and output validation."""
import struct
import wave
from pathlib import Path

import pytest

from src.video import _escape, _zoompan_expr, get_audio_duration


# ── Unit tests: helper functions ──────────────────────────────────────────────

def test_escape_colon():
    assert "\\:" in _escape("time: 10:00")


def test_escape_apostrophe():
    assert "\\'" in _escape("it's here")


def test_escape_percent():
    assert "\\%" in _escape("100%")


def test_zoompan_zoom_in_contains_min():
    expr = _zoompan_expr("zoom_in", frames=150)
    assert "min(zoom+" in expr


def test_zoompan_zoom_out_contains_if():
    expr = _zoompan_expr("zoom_out", frames=150)
    assert "if(eq(on,1)" in expr


def test_zoompan_pan_right_uses_on():
    expr = _zoompan_expr("pan_right", frames=150)
    assert "on/150" in expr


def test_zoompan_pan_left_uses_1_minus():
    expr = _zoompan_expr("pan_left", frames=150)
    assert "(1-on/150)" in expr


def test_all_effects_produce_z_and_x(tmp_path):
    for effect in ["zoom_in", "zoom_out", "pan_left", "pan_right"]:
        expr = _zoompan_expr(effect, frames=150)
        assert "z='" in expr
        assert "x='" in expr


# ── Integration test: audio duration probe ───────────────────────────────────

def _make_silent_wav(path: Path, duration: float = 3.0, rate: int = 44100) -> Path:
    n = int(duration * rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n, *([0] * n)))
    return path


def test_get_audio_duration(tmp_path):
    wav = _make_silent_wav(tmp_path / "test.wav", duration=4.0)
    duration = get_audio_duration(wav)
    assert abs(duration - 4.0) < 0.1


# ── End-to-end mock pipeline test ─────────────────────────────────────────────

def test_mock_pipeline_produces_mp4(tmp_path, monkeypatch):
    """Run the full pipeline in mock mode and verify a playable MP4 is created."""
    import json
    import shutil

    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")

    # Patch output dir to tmp_path
    config_path = Path(__file__).parent.parent / "config.json"
    config = json.loads(config_path.read_text())
    config["pipeline"]["output_dir"] = str(tmp_path)

    from mock.adapters import MockImageGenAdapter, MockLLMAdapter, MockTTSAdapter
    from src.pipeline import run as pipeline_run

    video_path, report = pipeline_run(
        topic="A morning in Ancient Rome",
        llm_adapter=MockLLMAdapter(),
        image_adapter=MockImageGenAdapter(),
        tts_adapter=MockTTSAdapter(),
        config=config,
        mock=True,
    )

    assert video_path.exists(), "final.mp4 not created"
    assert video_path.stat().st_size > 0, "final.mp4 is empty"
    assert report.video_duration_seconds > 0
    assert report.errors == []
