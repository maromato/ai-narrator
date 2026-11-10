"""Tests for mock asset generation (images and audio)."""
import wave
from pathlib import Path

import pytest
from PIL import Image

from mock.adapters import MockImageGenAdapter, MockTTSAdapter


@pytest.fixture
def tmp(tmp_path):
    return tmp_path


def test_mock_image_creates_file(tmp):
    adapter = MockImageGenAdapter()
    out = tmp / "scene_1.png"
    result = adapter.generate_image("some image prompt", out)
    assert result.exists()
    assert result.stat().st_size > 0


def test_mock_image_correct_size(tmp):
    adapter = MockImageGenAdapter()
    out = tmp / "scene_1.png"
    adapter.generate_image("prompt", out)
    with Image.open(out) as img:
        assert img.size == (1024, 1792)


def test_mock_image_increments_usage(tmp):
    adapter = MockImageGenAdapter()
    for i in range(1, 4):
        adapter.generate_image("prompt", tmp / f"scene_{i}.png")
    assert adapter.usage["images_generated"] == 3


def test_mock_tts_creates_wav(tmp):
    adapter = MockTTSAdapter()
    out = tmp / "narration_1.wav"
    result = adapter.synthesize("Hello ancient Rome.", out)
    assert result.exists()


def test_mock_tts_is_valid_wav(tmp):
    adapter = MockTTSAdapter()
    out = tmp / "narration_1.wav"
    adapter.synthesize("Hello ancient Rome.", out)
    with wave.open(str(out), "r") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 44100
        assert wf.getnframes() > 0


def test_mock_tts_duration_scales_with_text(tmp):
    adapter = MockTTSAdapter()
    short = tmp / "short.wav"
    long_ = tmp / "long.wav"
    adapter.synthesize("Hi.", short)
    adapter.synthesize("This is a much longer narration sentence for testing.", long_)
    with wave.open(str(short)) as s, wave.open(str(long_)) as l:
        assert l.getnframes() > s.getnframes()
