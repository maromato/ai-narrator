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
{genre_hint}
Return ONLY a valid JSON array of topic strings — no explanation, no markdown:
["topic 1", "topic 2", "topic 3", "topic 4", "topic 5"]
"""

_GENRE_HINTS: dict[str, str] = {
    "animals": (
        "- At least 2 of the topics must be about dogs — cute behaviors, surprising facts, "
        "heartwarming stories, or things dogs do that most owners don't know. "
        "The rest can be other animals.\n"
    ),
    "academia": (
        "- Topics should feel like 'elite secret knowledge' — psychology insights, decision-making science, "
        "surprising things top universities research, counterintuitive life lessons from Nobel laureates. "
        "Think 'Harvard researchers discovered that...' or 'what straight-A students do differently'. "
        "Make it feel like insider knowledge most people never get access to.\n"
    ),
    "romance": (
        "- Keep topics light, fun, and relatable — everyday couple moments, "
        "cute ways to get attention, flirty texting habits, things that make hearts skip a beat. "
        "Think 'how to make him think of you' not 'the philosophy of love'.\n"
    ),
    "mens_life": (
        "- Topics must be light, fun, and instantly relatable to men aged 18-35 — "
        "small daily habits, style/grooming quick wins, things women actually notice, "
        "social situations guys mess up without knowing. "
        "Think 'guys who do X are instantly more likeable' not abstract life philosophy. "
        "Make it the kind of content men forward to their group chat.\n"
    ),
}

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
        genre_hint = _GENRE_HINTS.get(genre, "")
        prompt = _PROMPT.format(
            genre=genre,
            count=count,
            lang_audience=lang_audience,
            genre_hint=genre_hint,
        )
        logger.info("Requesting %d topic suggestions (genre=%s, lang=%s)", count, genre, lang)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        # Extract the JSON array robustly regardless of surrounding text
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]

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
