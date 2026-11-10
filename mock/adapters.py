"""
Mock adapters — test the full pipeline without paid API calls.
  MockLLMAdapter      : returns hardcoded storyboard for "A morning in Ancient Rome"
  MockImageGenAdapter : generates a colored PIL placeholder image
  MockTTSAdapter      : writes a 5-second silent WAV file
"""
import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from src.storyboard import Storyboard

_MOCK_STORYBOARD = {
    "topic": "A morning in Ancient Rome",
    "tone": "dramatic",
    "target_audience": "18-35, history enthusiasts",
    "hashtags": ["#AncientRome", "#History", "#LearnOnTikTok", "#RomanEmpire", "#HistoryFacts"],
    "script": (
        "What if everything you knew about Rome's fall was wrong? "
        "For centuries, Rome stood as the mightiest empire on Earth. "
        "Then cracks began to form — corruption, invasion, economic collapse. "
        "In 410 AD, the Visigoths breached the Eternal City's walls. "
        "The empire fractured, and an era ended forever. "
        "But Rome never truly died — it lives on in our laws, our language, our world."
    ),
    "scenes": [
        {
            "scene_id": 1,
            "title": "The Hook",
            "image_prompt": (
                "Dramatic aerial view of ancient Rome burning at night, flames reflecting on "
                "the Tiber River, Colosseum silhouette, cinematic chiaroscuro, "
                "photorealistic, portrait vertical composition"
            ),
            "narration": "What if everything you knew about Rome's fall was wrong?",
            "subtitle": "WHAT REALLY DESTROYED ROME?",
            "camera_effect": "zoom_in",
        },
        {
            "scene_id": 2,
            "title": "Rome at Its Peak",
            "image_prompt": (
                "Ancient Rome at its peak glory, marble temples, crowded forums, "
                "legions marching, golden sunlight, photorealistic, portrait vertical composition"
            ),
            "narration": "For centuries, Rome stood as the mightiest empire on Earth.",
            "subtitle": "THE GREATEST EMPIRE EVER BUILT",
            "camera_effect": "pan_right",
        },
        {
            "scene_id": 3,
            "title": "Cracks Appear",
            "image_prompt": (
                "Roman senator in corrupt court, shadowy figures exchanging gold, "
                "decaying marble columns, dramatic torchlight, portrait vertical composition"
            ),
            "narration": "Then cracks began to form — corruption, invasion, economic collapse.",
            "subtitle": "CORRUPTION FROM WITHIN",
            "camera_effect": "zoom_out",
        },
        {
            "scene_id": 4,
            "title": "The Visigoths",
            "image_prompt": (
                "Visigoth warriors breaching the gates of Rome, battle chaos, "
                "dust and fire, Roman soldiers overwhelmed, cinematic, portrait vertical composition"
            ),
            "narration": "In 410 AD, the Visigoths breached the Eternal City's walls.",
            "subtitle": "THE WALLS FINALLY FELL",
            "camera_effect": "pan_left",
        },
        {
            "scene_id": 5,
            "title": "The Collapse",
            "image_prompt": (
                "Abandoned Roman ruins overtaken by nature, broken aqueducts, "
                "fallen columns, dramatic sunset, photorealistic, portrait vertical composition"
            ),
            "narration": "The empire fractured, and an era ended forever.",
            "subtitle": "AN ERA ENDED FOREVER",
            "camera_effect": "zoom_in",
        },
        {
            "scene_id": 6,
            "title": "Legacy",
            "image_prompt": (
                "Modern city skyline blending with ancient Roman architecture, "
                "timeless continuity, golden hour light, portrait vertical composition"
            ),
            "narration": "But Rome never truly died — it lives on in our laws, our language, our world.",
            "subtitle": "ROME NEVER TRULY DIED",
            "camera_effect": "zoom_out",
        },
    ],
}

_SCENE_COLORS = [
    (120, 60, 180),   # purple-ish
    (60, 120, 200),   # blue
    (200, 110, 50),   # orange
    (50, 160, 100),   # green
    (180, 60, 80),    # red
    (80, 160, 160),   # teal
]


class MockLLMAdapter:
    usage = {"model": "mock", "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0}

    def generate_storyboard(self, topic: str, genre: str = "general", lang: str = "en") -> Storyboard:
        data = dict(_MOCK_STORYBOARD)
        data["topic"] = topic
        return Storyboard.from_dict(data)


class MockImageGenAdapter:
    def __init__(self):
        self.usage = {"model": "mock", "images_generated": 0, "estimated_cost_usd": 0.0}

    def generate_image(self, prompt: str, output_path: Path) -> Path:
        scene_idx = int(output_path.stem.split("_")[-1]) - 1 if output_path.stem[-1].isdigit() else 0
        color = _SCENE_COLORS[scene_idx % len(_SCENE_COLORS)]

        img = Image.new("RGB", (1024, 1792), color)
        draw = ImageDraw.Draw(img)

        # Title text
        label = f"[MOCK] Scene {scene_idx + 1}"
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((1024 - tw) // 2, (1792 - th) // 2), label, fill="white", font=font)
        img.save(str(output_path))

        self.usage["images_generated"] += 1
        return output_path


class MockTTSAdapter:
    def __init__(self):
        self.usage = {"model": "mock", "characters": 0, "estimated_cost_usd": 0.0}

    def synthesize(self, text: str, output_path: Path) -> Path:
        duration = max(3.0, len(text) / 15)  # ~15 chars/sec estimate
        sample_rate = 44100
        n_frames = int(duration * sample_rate)

        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))

        self.usage["characters"] += len(text)
        return output_path
