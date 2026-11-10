"""
Storyboard schema definition, validation, and dataclass.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import jsonschema

CAMERA_EFFECTS = Literal["zoom_in", "zoom_out", "pan_left", "pan_right"]

SCHEMA = {
    "type": "object",
    "required": ["topic", "script", "scenes"],
    "properties": {
        "topic":           {"type": "string", "minLength": 1},
        "tone":            {"type": "string", "minLength": 1},
        "target_audience": {"type": "string", "minLength": 1},
        "hashtags":        {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "script":          {"type": "string", "minLength": 1},
        "scenes": {
            "type": "array",
            "minItems": 6,
            "maxItems": 8,
            "items": {
                "type": "object",
                "required": [
                    "scene_id", "title", "image_prompt",
                    "narration", "subtitle", "camera_effect"
                ],
                "properties": {
                    "scene_id":      {"type": "integer", "minimum": 1},
                    "title":         {"type": "string", "minLength": 1},
                    "image_prompt":  {"type": "string", "minLength": 10},
                    "narration":     {"type": "string", "minLength": 5},
                    "subtitle":      {"type": "string", "minLength": 1},
                    "camera_effect": {
                        "type": "string",
                        "enum": ["zoom_in", "zoom_out", "pan_left", "pan_right"]
                    }
                },
                "additionalProperties": False
            }
        }
    },
    "additionalProperties": False
}


# Genre → visual style prefix injected into every image prompt
GENRE_STYLES: dict[str, str] = {
    "history": (
        "epic Hollywood historical epic cinematic style, "
        "ultra-photorealistic 8K, dramatic golden-hour or torchlit lighting, "
        "emotionally expressive faces, accurate period costumes and architecture, "
        "depth of field, movie still quality, intense atmosphere — "
        "like a frame from Gladiator or Kingdom of Heaven"
    ),
    "science": (
        "stunning science visualization, ultra-high-definition photorealistic, "
        "dramatic contrast and vivid saturated colors, "
        "awe-inspiring scale — vast cosmos or extreme macro close-up, "
        "cinematic lighting, BBC Planet Earth / NASA photography quality, "
        "visually breathtaking and emotionally powerful"
    ),
    "animals": (
        "Pixar / DreamWorks 3D animation style, ultra-detailed expressive character design, "
        "warm cinematic lighting, rich lush natural environment, "
        "emotionally resonant facial expressions, soft volumetric light, "
        "vibrant color palette, movie-quality render"
    ),
    "religion": (
        "epic sacred cinematic photography, divine volumetric god-rays piercing through clouds, "
        "monumental awe-inspiring scale, deeply emotional and spiritual atmosphere, "
        "rich warm golden tones, dramatic chiaroscuro, "
        "cinematic composition that evokes wonder and reverence — "
        "like a visual effects scene from Ben-Hur or The Ten Commandments reimagined in 8K"
    ),
    "lifestyle": (
        "modern aesthetic lifestyle photography, ultra-clean minimalist composition, "
        "warm soft natural lighting, cozy and aspirational atmosphere, "
        "Instagram-meets-cinema quality, beautiful everyday moments, "
        "rich warm tones, shallow depth of field, emotionally inviting"
    ),
    "selfhelp": (
        "cinematic motivational photography, lone figure against vast inspiring landscape, "
        "golden hour light symbolizing hope and transformation, "
        "powerful silhouettes, uplifting and emotional atmosphere, "
        "ultra-photorealistic 8K, visually metaphorical — "
        "like a movie poster for personal triumph"
    ),
    "workplace": (
        "dynamic modern workplace cinematic photography, "
        "confident expressive professionals in real human moments, "
        "dramatic office or urban environment lighting, "
        "emotionally authentic — not stock photo, ultra-photorealistic 8K, "
        "storytelling composition that captures tension or breakthrough"
    ),
    "japan_travel": (
        "breathtaking cinematic photography of Japan, ultra-photorealistic 8K, "
        "magical atmospheric lighting — golden hour, morning mist, cherry blossoms, autumn leaves or snow, "
        "serene and awe-inspiring Japanese landscapes, ancient temples, hidden onsen, "
        "rich cultural details, wide-angle cinematic composition, "
        "the kind of image that makes viewers immediately want to book a flight to Japan"
    ),
    "japan_zen": (
        "deeply atmospheric Japanese Zen aesthetic, cinematic ultra-photorealistic 8K, "
        "minimalist sacred beauty — stone gardens, moss-covered temples, candlelit meditation halls, "
        "soft volumetric morning light filtering through bamboo or shoji screens, "
        "profound stillness and spiritual depth, "
        "ink wash painting meets high-end cinema photography, "
        "visually meditative and emotionally moving"
    ),
    "general": (
        "cinematic movie-trailer quality, ultra-photorealistic 8K, "
        "dramatic lighting, vivid colors, emotionally compelling composition"
    ),
}


@dataclass
class Scene:
    scene_id: int
    title: str
    image_prompt: str
    narration: str
    subtitle: str
    camera_effect: str


@dataclass
class Storyboard:
    topic: str
    script: str
    scenes: list[Scene]
    tone: str = ""
    target_audience: str = ""
    hashtags: list[str] = None

    def __post_init__(self):
        if self.hashtags is None:
            self.hashtags = []

    @classmethod
    def from_dict(cls, data: dict) -> "Storyboard":
        validate(data)
        return cls(
            topic=data["topic"],
            script=data["script"],
            scenes=[Scene(**s) for s in data["scenes"]],
            tone=data.get("tone", ""),
            target_audience=data.get("target_audience", ""),
            hashtags=data.get("hashtags", []),
        )

    @classmethod
    def from_json(cls, path: Path) -> "Storyboard":
        return cls.from_dict(json.loads(path.read_text()))

    def to_dict(self) -> dict:
        return {
            "topic":           self.topic,
            "tone":            self.tone,
            "target_audience": self.target_audience,
            "hashtags":        self.hashtags,
            "script":          self.script,
            "scenes": [
                {
                    "scene_id":      s.scene_id,
                    "title":         s.title,
                    "image_prompt":  s.image_prompt,
                    "narration":     s.narration,
                    "subtitle":      s.subtitle,
                    "camera_effect": s.camera_effect,
                }
                for s in self.scenes
            ],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


def validate(data: dict) -> None:
    jsonschema.validate(instance=data, schema=SCHEMA)


def build_prompt(topic: str, genre: str = "general", lang: str = "en") -> str:
    style = GENRE_STYLES.get(genre, GENRE_STYLES["general"])
    genre_label = genre.upper()

    if lang == "ja":
        lang_instruction = (
            "- narration と subtitle は必ず日本語で書くこと。\n"
            "- subtitle は最大12文字、インパクトのある日本語フレーズ。\n"
            "- image_prompt は英語のまま（画像生成AIのため）。\n"
            "- script（全体ナレーション）も日本語で書くこと。"
        )
        subtitle_rule = "字幕（subtitle）は最大12文字の日本語、感情的でインパクトのあるフレーズ。"
        narration_rule = "narration は日本語で1〜3文、読み上げ時4〜6秒程度。"
    else:
        lang_instruction = ""
        subtitle_rule = "Subtitles must be ALL CAPS, max 6 words, punchy and emotional."
        narration_rule = "Each narration ~4-6 seconds when spoken aloud (do NOT make them too long)."

    return f"""\
You are a viral short-form video creator specializing in {genre_label} content.

Create a 6-scene storyboard for a 30-second TikTok-style portrait video (1080×1920).

NARRATIVE STRUCTURE — follow this order exactly:
- Scene 1 (HOOK): Open with a shocking fact, provocative question, or dramatic visual. Must grab attention in the first 2 seconds.
- Scene 2 (CONTEXT): Set the stage — where, when, who, or what this is about.
- Scene 3 (DEVELOPMENT): Deepen the story. Introduce tension, surprise, or complexity.
- Scene 4 (REVELATION): Deliver the key insight, twist, or surprising truth.
- Scene 5 (CLIMAX): The emotional or intellectual peak of the story.
- Scene 6 (RESOLUTION): A powerful closing line that leaves the viewer thinking, moved, or wanting to share.

VISUAL STYLE for all images: {style}, vertical portrait composition (9:16), no text in image.

Return ONLY valid JSON — no markdown, no extra text — matching this exact schema:
{{
  "topic": "<topic string>",
  "tone": "<overall emotional tone, e.g. dramatic / inspiring / mysterious / heartwarming / educational>",
  "target_audience": "<primary viewer demographic, e.g. '18-34, history enthusiasts'>",
  "hashtags": ["<hashtag1>", "<hashtag2>", "<hashtag3>", "<hashtag4>", "<hashtag5>"],
  "script": "<full narration joined together, ~30 seconds at natural speaking pace>",
  "scenes": [
    {{
      "scene_id": 1,
      "title": "<short scene title>",
      "image_prompt": "<detailed image prompt in English incorporating the visual style above, explicitly portrait/vertical 9:16 composition>",
      "narration": "<1-3 sentences spoken for this scene>",
      "subtitle": "<short punchy text shown on screen>",
      "camera_effect": "<zoom_in|zoom_out|pan_left|pan_right>"
    }}
  ]
}}

Rules:
- Exactly 6 scenes.
- {narration_rule}
- Vary camera_effect — no two consecutive scenes the same effect.
- {subtitle_rule}
- image_prompt must always be in English and specify the visual style and vertical/portrait framing.
- hashtags: 5 relevant tags including platform-appropriate ones (e.g. #LearnOnTikTok).
- No field may be null or empty.
- The story must feel genuinely compelling — not like a Wikipedia summary.
{lang_instruction}
Topic: {topic}"""


# Keep backward-compatible alias
LLM_PROMPT_TEMPLATE = """\
You are a creative director for short-form educational videos.

Given a topic, produce a 6-scene storyboard for a ~30-second portrait video (1080×1920).

Return ONLY valid JSON — no markdown, no extra text — matching this exact schema:
{{
  "topic": "<topic string>",
  "script": "<full English narration, ~30 seconds when read at natural pace>",
  "scenes": [
    {{
      "scene_id": 1,
      "title": "<short scene title>",
      "image_prompt": "<detailed photorealistic image prompt, explicitly portrait/vertical composition>",
      "narration": "<1-2 sentences spoken for this scene>",
      "subtitle": "<max 6 words ALL CAPS shown on screen>",
      "camera_effect": "<zoom_in|zoom_out|pan_left|pan_right>"
    }}
  ]
}}

Rules:
- Exactly 6 scenes.
- Each narration ~4-6 seconds when spoken aloud.
- Image prompts must specify photorealistic style and vertical/portrait framing.
- Vary camera_effect across scenes.
- No field may be null or empty.

Topic: {topic}"""
