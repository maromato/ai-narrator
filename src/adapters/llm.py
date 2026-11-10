"""Claude LLM adapter — generates storyboard JSON."""
import json
import logging
import os

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from src.storyboard import Storyboard, build_prompt

logger = logging.getLogger(__name__)


class ClaudeAdapter:
    def __init__(self, config: dict):
        self.config = config
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.usage: dict = {}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def generate_storyboard(self, topic: str, genre: str = "general", lang: str = "en") -> Storyboard:
        logger.info("Generating storyboard for topic: %s (genre: %s, lang: %s)", topic, genre, lang)
        prompt = build_prompt(topic, genre, lang)

        response = self.client.messages.create(
            model=self.config["model"],
            max_tokens=self.config["max_tokens"],
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        self.usage = {
            "model": self.config["model"],
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "estimated_cost_usd": round(
                response.usage.input_tokens * 3e-6
                + response.usage.output_tokens * 15e-6,
                6,
            ),
        }
        logger.info("Storyboard generated (%d output tokens)", response.usage.output_tokens)
        return Storyboard.from_dict(json.loads(raw))
