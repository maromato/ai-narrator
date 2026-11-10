"""LLM-based topic selector — asks Claude to suggest TikTok-ready topics."""
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_PROMPT = """\
You are a TikTok content strategist specializing in {genre} content.

Suggest {count} compelling video topics for a 30-second TikTok-style short video.

Requirements:
- Each topic must have an unexpected angle, surprising fact, or emotional hook
- Must be fully tellable in 30 seconds
- Should appeal to a {lang_audience} audience
- Genre: {genre}
- Avoid overly well-known topics (e.g. not just "The Fall of Rome" but something more specific or unexpected)

Return ONLY a valid JSON array of topic strings — no explanation, no markdown:
["topic 1", "topic 2", "topic 3", "topic 4", "topic 5"]
"""

_LANG_AUDIENCE = {
    "en": "English-speaking global",
    "ja": "Japanese-speaking",
}


class LLMTopicSelector:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model

    def suggest(self, genre: str = "general", lang: str = "en", count: int = 5) -> list[str]:
        lang_audience = _LANG_AUDIENCE.get(lang, "global")
        prompt = _PROMPT.format(
            genre=genre,
            count=count,
            lang_audience=lang_audience,
        )
        logger.info("Requesting %d topic suggestions (genre=%s, lang=%s)", count, genre, lang)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        topics = json.loads(raw)
        logger.info("Got %d topic suggestions", len(topics))
        return topics

    def select(
        self,
        genre: str = "general",
        lang: str = "en",
        interactive: bool = False,
        count: int = 5,
    ) -> str:
        topics = self.suggest(genre=genre, lang=lang, count=count)

        if not interactive:
            chosen = topics[0]
            logger.info("Auto-selected topic: %s", chosen)
            return chosen

        # Interactive: show numbered list and prompt user
        print("\n--- Topic Suggestions ---")
        for i, t in enumerate(topics, 1):
            print(f"  {i}. {t}")
        print("  0. Enter manually")
        print("-------------------------")

        while True:
            raw = input("Select topic number (0 to enter manually): ").strip()
            if raw == "0":
                return input("Enter your topic: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(topics):
                chosen = topics[int(raw) - 1]
                logger.info("User selected topic: %s", chosen)
                return chosen
            print(f"Please enter a number between 0 and {len(topics)}.")
