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
    "history": (
        "- Topics must be hyper-specific and surprising — not 'The Fall of Rome' but "
        "'The 16-year-old nobody who was Rome's last emperor' or "
        "'The single letter Julius Caesar ignored that got him killed'. "
        "Focus on one person, one object, one day, one decision — not grand sweeping events. "
        "The more specific and human, the better.\n"
    ),
    "science": (
        "- Topics must be one extreme, jaw-dropping fact — either impossibly small or impossibly large scale. "
        "Think 'the tardigrade that survived in space', 'the sound a black hole makes', "
        "'what your body does in the first second after death'. "
        "Must make viewers say 'wait, this is actually real?' — not textbook science, mind-bending reality.\n"
    ),
    "animals": (
        "- ALL topics must be about dogs. Focus on cuteness, charm, heartwarming intelligence, "
        "and the deep emotional bond between dogs and humans. "
        "Think 'why dogs tilt their head when you talk', 'the science behind a dog's happy face', "
        "'dogs who waited years for owners'. Make viewers want to hug their dog immediately.\n"
    ),
    "academia": (
        "- ALL topics must be specifically about Harvard University — Harvard secrets, "
        "surprising Harvard research, famous Harvard dropouts and what they learned first, "
        "what Harvard's most exclusive courses teach, little-known Harvard traditions. "
        "Must feel like insider access to the world's most elite institution. "
        "Think 'The Harvard study that changed how we understand happiness' or "
        "'The one class Harvard teaches that no other school does'.\n"
    ),
    "elite_edu": (
        "- Topics must be practical knowledge from Harvard, MIT, or Stanford — "
        "study techniques backed by research, business frameworks taught in top MBA programs, "
        "productivity systems used by elite students, thinking models from Nobel laureates. "
        "Think 'The MIT study method that beats cramming', 'Stanford's design thinking applied to everyday decisions', "
        "'The one habit Harvard MBA graduates share'. "
        "Must feel immediately useful and aspirationally elite — knowledge that gives viewers a real edge.\n"
    ),
    "finance": (
        "- Topics must be practical money tips that feel urgent and immediately actionable — "
        "'the savings trick most people learn too late', 'why keeping money in a regular savings account is a mistake', "
        "'the tax deduction 90% of people miss'. "
        "Make viewers feel they are getting access to knowledge that rich people already know. "
        "Avoid generic advice — be specific with numbers and situations.\n"
    ),
    "psychology": (
        "- Topics must be about surprising human behaviors or cognitive biases that viewers recognize in themselves — "
        "'why you buy things you don't need', 'the reason you can't stop checking your phone', "
        "'the psychological trick that makes people like you instantly'. "
        "Must feel like a revelation about their own mind. "
        "Reference real psychological effects by name when possible.\n"
    ),
    "romance": (
        "- Keep topics light, fun, and relatable — everyday couple moments, "
        "cute ways to get attention, flirty texting habits, things that make hearts skip a beat. "
        "Think 'how to make him think of you' not 'the philosophy of love'.\n"
    ),
    "japan_travel": (
        "- Topics must be hidden gems, lesser-known places, or underrated experiences in Japan — "
        "not Shibuya crossing or Mount Fuji, but secret onsen towns, forgotten castle towns, "
        "rural villages with incredible food, festivals only locals know, "
        "neighborhoods even most Tokyo residents have never visited. "
        "Must make international viewers think 'I had no idea this existed in Japan — I need to go'. "
        "Bright, exciting, story-driven — not a travel guide, a personal discovery.\n"
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
