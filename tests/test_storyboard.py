"""Tests for storyboard schema validation and dataclass creation."""
import pytest

from src.storyboard import Storyboard, validate

VALID_STORYBOARD = {
    "topic": "Test topic",
    "script": "This is the full narration script.",
    "scenes": [
        {
            "scene_id": i,
            "title": f"Scene {i}",
            "image_prompt": f"Detailed photorealistic image prompt for scene {i}",
            "narration": f"Narration for scene {i}.",
            "subtitle": f"Subtitle {i}",
            "camera_effect": effect,
        }
        for i, effect in enumerate(
            ["zoom_in", "pan_right", "zoom_out", "pan_left"], start=1
        )
    ],
}


def test_valid_storyboard_passes_validation():
    validate(VALID_STORYBOARD)


def test_storyboard_from_dict():
    sb = Storyboard.from_dict(VALID_STORYBOARD)
    assert sb.topic == "Test topic"
    assert len(sb.scenes) == 4
    assert sb.scenes[0].camera_effect == "zoom_in"
    assert sb.scenes[1].camera_effect == "pan_right"


def test_storyboard_roundtrip():
    sb = Storyboard.from_dict(VALID_STORYBOARD)
    assert sb.to_dict() == VALID_STORYBOARD


def test_invalid_effect_fails():
    import copy
    data = copy.deepcopy(VALID_STORYBOARD)
    data["scenes"][0]["camera_effect"] = "spin"
    with pytest.raises(Exception):
        validate(data)


def test_wrong_scene_count_fails():
    import copy
    data = copy.deepcopy(VALID_STORYBOARD)
    data["scenes"] = data["scenes"][:3]
    with pytest.raises(Exception):
        validate(data)


def test_missing_field_fails():
    import copy
    data = copy.deepcopy(VALID_STORYBOARD)
    del data["scenes"][0]["narration"]
    with pytest.raises(Exception):
        validate(data)


def test_empty_topic_fails():
    import copy
    data = copy.deepcopy(VALID_STORYBOARD)
    data["topic"] = ""
    with pytest.raises(Exception):
        validate(data)
