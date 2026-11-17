"""
Storyboard evaluator — uses Claude to score a storyboard on TikTok effectiveness criteria.
"""
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

# RPM multiplier per genre based on 2026 market research
# (education/finance = highest advertiser demand, animals/romance = lower CPM)
RPM_FACTORS: dict[str, float] = {
    "academia":    1.35,
    "elite_edu":   1.35,
    "finance":     1.30,
    "psychology":  1.25,
    "history":     1.15,
    "science":     1.15,
    "workplace":   1.10,
    "selfhelp":    1.05,
    "japan_travel":1.00,
    "japan_zen":   1.00,
    "mens_life":   0.95,
    "lifestyle":   0.90,
    "romance":     0.90,
    "animals":     0.90,
    "religion":    0.85,
    "general":     1.00,
    "beauty":      1.05,
    "investor":    1.40,
    "religion2":   0.85,
    "drama_kdrama":  1.10,
    "drama_romance": 1.05,
    "drama_bl":         1.05,
    "drama_korean_bl":  1.10,
    "kdrama_intro":  1.10,
    "bl_intro":      1.05,
}

_EVAL_PROMPT = """\
You are a TikTok content strategist with deep expertise in viral short-form video.

Evaluate this 30-second TikTok storyboard on 6 criteria. Score each 1–10.

CRITERIA:
1. hook_power        — Does Scene 1 grab attention within 2 seconds? Shocking/provocative/irresistible?
2. shareability      — Would viewers save, share, or tag friends? Is there a clear emotional reason to share?
3. specificity       — Is the topic hyper-specific and fresh? (Generic = low score. "The 16-year-old who was Rome's last emperor" = high score.)
4. emotional_impact  — Does it create a strong emotion: surprise, laughter, awe, warmth, or urgency?
5. tiktok_fit        — Does the pacing, structure, and CTA match TikTok's short attention span and algorithm?
6. replay_value      — Would viewers watch again, quote it, or talk about it?

Return ONLY valid JSON — no markdown, no explanation:
{{
  "hook_power":       <1-10>,
  "shareability":     <1-10>,
  "specificity":      <1-10>,
  "emotional_impact": <1-10>,
  "tiktok_fit":       <1-10>,
  "replay_value":     <1-10>,
  "verdict": "<one sharp sentence: what makes this work or fail>"
}}

STORYBOARD TOPIC: {topic}
TONE: {tone}
TARGET AUDIENCE: {target_audience}

SCRIPT:
{script}

SCENES:
{scenes}
"""


class StoryboardEvaluator:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model

    def evaluate(self, storyboard: dict, genre: str) -> dict:
        scenes_text = "\n".join(
            f"Scene {s['scene_id']}: [{s['title']}] {s['narration']} | Subtitle: {s['subtitle']}"
            for s in storyboard["scenes"]
        )
        prompt = _EVAL_PROMPT.format(
            topic=storyboard["topic"],
            tone=storyboard.get("tone", ""),
            target_audience=storyboard.get("target_audience", ""),
            script=storyboard["script"],
            scenes=scenes_text,
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        start, end = raw.find("{"), raw.rfind("}")
        scores = json.loads(raw[start:end + 1])

        criteria = ["hook_power", "shareability", "specificity", "emotional_impact", "tiktok_fit", "replay_value"]
        content_score = sum(scores[k] for k in criteria) / len(criteria)
        rpm_factor = RPM_FACTORS.get(genre, 1.0)
        final_score = round(content_score * rpm_factor, 2)

        scores["content_score"] = round(content_score, 2)
        scores["rpm_factor"] = rpm_factor
        scores["final_score"] = final_score
        scores["genre"] = genre
        scores["topic"] = storyboard["topic"]
        return scores
