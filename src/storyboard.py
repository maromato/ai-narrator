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
        "ultra-photorealistic 8K historical documentary photograph, "
        "real people in accurate period costumes and architecture, "
        "dramatic natural torchlight or golden-hour sunlight, "
        "shot on location, emotionally expressive faces, shallow depth of field, "
        "looks like an actual photograph taken in ancient times — not a painting or illustration"
    ),
    "science": (
        "ultra-photorealistic 8K real photograph, "
        "actual NASA or BBC Planet Earth documentary photography style, "
        "real macro close-up or real astronomical image, "
        "dramatic natural lighting, vivid saturated colors, "
        "looks like a genuine scientific photograph — not CGI or illustration"
    ),
    "animals": (
        "ultra-photorealistic 8K wildlife documentary photograph, "
        "real animal in natural habitat, National Geographic photography style, "
        "dramatic natural lighting, shallow depth of field, "
        "emotionally expressive animal faces captured in a real candid moment — "
        "not illustrated, not animated, looks like an actual wildlife photo"
    ),
    "religion": (
        "ultra-photorealistic 8K real documentary photograph, "
        "actual sacred site — ancient temple, cathedral, holy landscape, "
        "real god-rays or golden-hour light captured on camera, "
        "deeply atmospheric and spiritual, genuine human devotion or awe, "
        "looks like a real photograph — not VFX or illustration"
    ),
    "lifestyle": (
        "ultra-photorealistic 8K lifestyle photography, "
        "real person in a beautiful everyday moment, "
        "warm soft natural window light, shallow bokeh background, "
        "authentic candid feel — not posed stock photo, "
        "the kind of real photo that stops you while scrolling"
    ),
    "selfhelp": (
        "ultra-photorealistic 8K real outdoor photograph, "
        "lone real person against a vast natural landscape — mountain summit, open road, wide ocean, "
        "genuine golden hour or dawn light, powerful emotional atmosphere, "
        "looks like an actual photograph taken on location — not illustration or compositing"
    ),
    "workplace": (
        "ultra-photorealistic 8K real workplace photograph, "
        "real people in genuine human moments — focus, tension, breakthrough, collaboration, "
        "authentic office or urban environment with natural dramatic lighting, "
        "candid documentary style — not posed, not stock photo"
    ),
    "japan_travel": (
        "ultra-photorealistic 8K real travel photograph of Japan, "
        "actual location — Kyoto temple, Tokyo street, mountain onsen, rural countryside, "
        "magical real atmospheric light — golden hour mist, cherry blossom petals, autumn color, fresh snow, "
        "shot on professional camera, wide angle, the kind of real photo that makes viewers want to book a flight"
    ),
    "japan_zen": (
        "ultra-photorealistic 8K real photograph of Japanese Zen environment, "
        "actual stone garden, moss temple, bamboo grove, or candlelit meditation hall, "
        "real soft morning light filtering through shoji screens or bamboo, "
        "profound stillness and silence captured on camera — "
        "looks like a genuine photograph, not a painting or digital art"
    ),
    "romance": (
        "ultra-photorealistic 8K real photograph, "
        "beautiful young Japanese couple in intimate relatable everyday moments, "
        "soft natural golden bokeh lighting, heartfelt genuine emotions, "
        "candid documentary style — the kind of real photo that makes viewers think 'this is exactly me'"
    ),
    "mens_life": (
        "ultra-photorealistic 8K real photograph, "
        "confident stylish young Japanese man in authentic real-life situation in Tokyo or modern Japanese city, "
        "dramatic natural or street lighting, genuine emotional expression — "
        "candid documentary style, not posed, deeply relatable to men aged 20-35"
    ),
    "academia": (
        "ultra-photorealistic 8K real photograph, "
        "actual Ivy League or prestigious university setting — grand library, stone lecture hall, Gothic courtyard, "
        "real atmospheric indoor lighting, genuine student or scholar in deep thought, "
        "leather books, handwritten equations on chalkboard, "
        "looks like a real documentary photograph — intellectually awe-inspiring"
    ),
    "general": (
        "ultra-photorealistic 8K real photograph, "
        "dramatic natural lighting, vivid colors, emotionally compelling real-world scene"
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


_NARRATIVE_STRUCTURES: dict[str, str] = {
    "academia": (
        "- Scene 1 (HOOK): Open with a 'Harvard teaches this but nobody talks about it' or 'top students all do this one thing' hook.\n"
        "- Scene 2 (SETUP): Introduce the concept — make it feel like insider knowledge from elite circles.\n"
        "- Scene 3 (THE INSIGHT): The core idea explained simply — smart but accessible, not a lecture.\n"
        "- Scene 4 (SURPRISE): A counterintuitive twist or 'even experts get this wrong' moment.\n"
        "- Scene 5 (APPLICATION): How to apply this in real life — make it immediately useful.\n"
        "- Scene 6 (CTA): A curiosity-driven closer like 'save this, most people never learn it' or 'share with someone smart'."
    ),
    "romance": (
        "- Scene 1 (HOOK): Start with a relatable, funny, or 'omg that's me' moment about love or dating.\n"
        "- Scene 2 (SETUP): Introduce the cute situation or problem — keep it light and fun.\n"
        "- Scene 3 (THE TRICK): Share the first tip or insight with a playful twist.\n"
        "- Scene 4 (SURPRISE): Drop a 'wait, really?' fact or unexpected technique.\n"
        "- Scene 5 (PAYOFF): The satisfying moment — what happens when it works.\n"
        "- Scene 6 (CTA): A fun, shareable closer like 'send this to your crush' or 'save for later'."
    ),
    "mens_life": (
        "- Scene 1 (HOOK): Open with a bold 'guys who do this are instantly more attractive' or 'stop doing this' hook — make men nod immediately.\n"
        "- Scene 2 (SETUP): Paint the relatable everyday situation — specific, funny, not preachy.\n"
        "- Scene 3 (THE TIP): One simple, concrete thing to do differently — practical not philosophical.\n"
        "- Scene 4 (SURPRISE): A 'wait, really?' fact or unexpected reason why it works.\n"
        "- Scene 5 (PAYOFF): What actually changes — keep it fun and tangible, not motivational-speech.\n"
        "- Scene 6 (CTA): A light closer like 'send this to a friend who needs it' or 'try this today'."
    ),
}

_DEFAULT_NARRATIVE = (
    "- Scene 1 (HOOK): Open with a shocking fact, provocative question, or dramatic visual. Must grab attention in the first 2 seconds.\n"
    "- Scene 2 (CONTEXT): Set the stage — where, when, who, or what this is about.\n"
    "- Scene 3 (DEVELOPMENT): Deepen the story. Introduce tension, surprise, or complexity.\n"
    "- Scene 4 (REVELATION): Deliver the key insight, twist, or surprising truth.\n"
    "- Scene 5 (CLIMAX): The emotional or intellectual peak of the story.\n"
    "- Scene 6 (RESOLUTION): A powerful closing line that leaves the viewer thinking, moved, or wanting to share."
)


def build_prompt(topic: str, genre: str = "general", lang: str = "en") -> str:
    style = GENRE_STYLES.get(genre, GENRE_STYLES["general"])
    genre_label = genre.upper()
    narrative_structure = _NARRATIVE_STRUCTURES.get(genre, _DEFAULT_NARRATIVE)

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
You are a viral short-form video creator specializing in {genre_label} content for TikTok.

Create a 6-scene storyboard for a 30-second TikTok-style portrait video (1080×1920).

NARRATIVE STRUCTURE — follow this order exactly:
{narrative_structure}

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
