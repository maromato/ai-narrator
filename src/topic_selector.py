"""LLM-based topic selector — asks Claude to suggest TikTok-ready topics."""
import json
import logging
import os
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_PATH = Path(__file__).parent.parent / "used_topics.json"

_PROMPT = """\
You are a TikTok content strategist specializing in {genre} content.

Suggest {count} compelling video topics for a 30-second TikTok-style short video.

Requirements:
- Each topic must have an unexpected angle, surprising fact, or emotional hook
- Must be fully tellable in 30 seconds
- Should appeal to a {lang_audience} audience
- Genre: {genre}
- Avoid overly well-known topics (e.g. not just "The Fall of Rome" but something more specific or unexpected)
{genre_hint}{avoid_hint}
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
        "Think 'The secret entrance exam Harvard uses that never appears on the application' or "
        "'The one class Harvard teaches that no other school does'. "
        "Do NOT suggest anything related to happiness research or the 75-year happiness study — that topic is overused. "
        "Do NOT suggest anything related to the library, rare books, or cursed books — that angle is overused.\n"
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
        "- Topics must feel like 週刊SPA の爆益・一攫千金特集 — real stories of ordinary Japanese people who made serious money "
        "through unconventional, edgy, or surprising methods. Make viewers think 'え、これで稼げるの？'.\n"
        "- Target: Japanese men and women in their 20s-40s who dream of escaping salary life.\n"
        "- REQUIRED: Every topic must have a built-in 逆転・オチ・教訓 (reversal or lesson). "
        "Bad: 「競馬AIで稼いだ会社員」(no lesson) → "
        "Good: 「競馬AIで年収超えた会社員が『勝てた理由は馬を見ていなかったから』と語った話」(has lesson/reversal).\n"
        "- Format template: 「[具体的な人物像]が[具体的な方法・数字]で[結果]——でも本当の理由は[意外な教訓]だった」\n"
        "- Think: 競馬AIで年収超えた会社員が最後に気づいた『損切りの一線』, "
        "仮想通貨で1000万作った人がたった一つやめたこと, "
        "副業で月30万超えた人が本業を続けた意外な理由, "
        "NFTで失敗した人と成功した人の行動の唯一の違い, "
        "元手10万スタートのFXトレーダーが最初の3ヶ月でやったことだけ.\n"
        "- Include specific numbers (age, capital, duration, return) whenever possible.\n"
        "- Energy: aspirational, slightly dangerous, 'I shouldn't be telling you this' — not responsible financial advice.\n"
        "- STRICT PROHIBITION: Do NOT suggest anything about 株・四季報・日経・個別銘柄・外国人保有比率・PER・チャート分析・セクターローテーション "
        "— those belong to the 'investor' genre, not this one.\n"
        "- Write topics in Japanese.\n"
    ),
    "psychology": (
        "- Topics must be about surprising human behaviors or cognitive biases that viewers recognize in themselves — "
        "'why you buy things you don't need', 'the reason you can't stop checking your phone', "
        "'the psychological trick that makes people like you instantly'. "
        "Must feel like a revelation about their own mind. "
        "Reference real psychological effects by name when possible.\n"
    ),
    "romance": (
        "- Topics should mix light romantic tension with mildly suggestive angles — "
        "flirty everyday moments, the psychology of physical attraction, "
        "things couples do that secretly drive each other crazy, "
        "the science behind a touch that sends a shiver, "
        "what makes someone irresistible at close distance. "
        "Think 'the spot men instinctively touch first and what it means', "
        "'why skin contact before sleep changes the relationship', "
        "'the 3-second eye contact rule that creates instant chemistry'. "
        "Keep it suggestive and charged — not explicit, but the kind of content that makes viewers "
        "blush slightly and immediately save to watch again. "
        "Avoid anything graphic — the tension is in what's implied, not stated.\n"
    ),
    "japan_travel": (
        "- Topics must be hidden gems, lesser-known places, or underrated experiences in Japan — "
        "not Shibuya crossing or Mount Fuji, but secret onsen towns, forgotten castle towns, "
        "rural villages with incredible food, festivals only locals know, "
        "neighborhoods even most Tokyo residents have never visited. "
        "Must make international viewers think 'I had no idea this existed in Japan — I need to go'. "
        "Bright, exciting, story-driven — not a travel guide, a personal discovery. "
        "Do NOT suggest 白川郷 — that destination is overused.\n"
    ),
    "mens_life": (
        "- Topics must be light, fun, and instantly relatable to men aged 18-35 — "
        "small daily habits, style/grooming quick wins, things women actually notice, "
        "social situations guys mess up without knowing. "
        "Think 'guys who do X are instantly more likeable' not abstract life philosophy. "
        "Make it the kind of content men forward to their group chat.\n"
    ),
    "religion2": (
        "- Topics must radiate pure positive energy — 開運, 金運, 引き寄せ, 豊かさ, スピリチュアル, パワーストーン, 満月の儀式.\n"
        "- Every topic must feel UPLIFTING and HOPEFUL — 'これをやると運気が上がる' not 'これをやると運気が下がる'.\n"
        "- Target: Japanese women in their 20s-40s who want to invite abundance, love, and good fortune into their lives.\n"
        "- Think: 朝起きてすぐやると一日の運気が変わる3つの習慣, "
        "持つだけで金運が上がるパワーストーンと正しい浄化方法, "
        "満月の夜に紙に書いて燃やすと願いが叶う理由, "
        "玄関をこの色にするだけで良い縁が舞い込んでくる風水の法則, "
        "引き寄せが加速する『感謝日記』の書き方——豊かさを呼ぶ言葉の選び方.\n"
        "- STRICTLY POSITIVE: No scary warnings, no 'NG', no 'これをやると運気が下がる' angles — only light, abundance, and hope.\n"
        "- Write topics in Japanese.\n"
    ),
    "investor": (
        "- Topics must be advanced, expert-level investment strategies that serious investors actually use — "
        "NOT beginner tips. Target: experienced traders and investors aged 30-50 who already know the basics.\n"
        "- Think: セクターローテーションの実践タイミング、空売りの仕掛け方と損切りライン、"
        "オプションのデルタヘッジ戦略、機関投資家が決算前にやること、"
        "レイ・ダリオのオールウェザー戦略の日本株版、信用取引の逆張り手法.\n"
        "- Must include specific numbers, indicators, or named strategies — vague advice scores zero.\n"
        "- The hook must feel like forbidden insider knowledge: 'プロが絶対に言わない' or '機関投資家だけが知る'.\n"
        "- Write topics in Japanese, specific enough that a professional would want to watch.\n"
    ),
    "drama_kdrama": (
        "- Each topic is a one-line drama premise (ワンライン) for a 30-second mini Korean drama episode.\n"
        "- Must have a clear emotional conflict and two characters with chemistry.\n"
        "- Think: 財閥御曹司×平凡な女性、記憶喪失、身分差の禁断愛、幼馴染との再会、病院での偶然の出会い.\n"
        "- The premise must be instantly addictive — viewers should feel 'next episode please' after 30 seconds.\n"
        "- Avoid slice-of-life — every premise needs a dramatic hook: a secret, a misunderstanding, a forbidden feeling.\n"
        "- Write the topic AS the drama premise in Japanese, e.g. '財閥の御曹司に契約結婚を迫られた地下アイドルの30日間'.\n"
    ),
    "drama_romance": (
        "- Each topic is a one-line premise for a 30-second Japanese romantic mini drama.\n"
        "- Focus on quiet, emotionally resonant romance — not K-drama grandiosity but Japanese restraint and longing.\n"
        "- Think: 幼馴染との再会、片思いが両思いになる瞬間、別れた恋人との偶然の再会、同僚への秘めた想い.\n"
        "- The best premises are specific and bittersweet — 'ずっと好きだったと言えないまま、彼女は明日転勤する'.\n"
        "- Write the topic AS the drama premise in Japanese.\n"
    ),
    "drama_bl": (
        "- Each topic is a one-line BL (Boys Love) drama premise for a 30-second mini episode.\n"
        "- Both protagonists MUST be young Japanese men in their 20s (university students, young adults, early-career).\n"
        "- Think: 大学の先輩×後輩、幼馴染の再会、同じアパートの住人、バイト仲間、部活のライバル.\n"
        "- The premise must feel tender and charged — the kind that makes BL fans' hearts ache.\n"
        "- Write the topic AS the drama premise in Japanese, e.g. '嫌いなはずの幼馴染が、雨の夜だけ優しくなる理由'.\n"
    ),
    "drama_korean_bl": (
        "- Each topic is a one-line Korean BL drama premise for a 30-second intense mini episode.\n"
        "- Both protagonists MUST be young Korean men in their 20s (young professionals, rookies, university students).\n"
        "- Think: 新人社員×同期のライバル、大学のサークル先輩×後輩、20代の若き起業家×幼馴染.\n"
        "- The premise needs charged energy and emotional tension — forbidden feelings between young men.\n"
        "- Must have a dramatic hook: rivalry, a shared secret, enemies-to-lovers, or an unexpected reunion.\n"
        "- Write the topic AS the drama premise in Japanese, e.g. '同期だと思っていた男が、実は3年前に俺の心を壊した人物だった'.\n"
    ),
    "beauty": (
        "- Topics must span the full beauty spectrum — skincare, cosmetic procedures, hair, fashion, and anti-aging — not just skincare alone. "
        "Think: 'the one ingredient dermatologists say is worth every yen', 'why your moisturiser is making your skin worse', "
        "'the Korean clinic procedure going viral in 2026', 'the hairstyle that takes 10 years off instantly', "
        "'the fashion rule that makes any outfit look expensive', 'the anti-aging habit dermatologists swear by'. "
        "Mix science-backed facts with aspirational J-beauty or K-beauty wisdom. "
        "Make viewers feel they are getting access to a pro's insider knowledge. "
        "Specific over vague: ingredients, procedures, techniques, or styles beat general advice every time.\n"
    ),
    "kdrama_intro": (
        "- Topics must be about REAL trending Korean dramas — introducing, recommending, or spotlighting what makes them unmissable. "
        "Think: '今すぐ観るべき韓ドラ：財閥御曹司と庶民女性の化学反応が止まらない理由', "
        "'Netflixで話題沸騰中の韓ドラがとにかくエモすぎる件', "
        "'このシーンで沼落ちする：2026年最強の韓ドラ胸キュン瞬間TOP3'. "
        "Be specific about the drama, the leads, the chemistry, the must-watch moment. "
        "Make viewers feel they MUST watch it immediately — FOMO is the hook. "
        "Write topics as a recommendation hook in Japanese.\n"
    ),
    "bl_intro": (
        "- Topics must be about BL (Boys Love) content that appeals to women — recommending BL dramas, manga, webtoons, or spotlighting iconic BL moments. "
        "Think: '女子が絶対ハマる：感情破壊系BLドラマTOP3の共通点', "
        "'このBLの沼にハマったら抜け出せない：2026年最強スロー展開BL', "
        "'BLファンが全員泣いたあのシーン：感情的に崩壊したBLベスト3'. "
        "Target: women (20s-40s) who love BL — make topics feel like recommendations from a passionate BL fan friend. "
        "Be specific about what makes the content special — the pairing, the trope, the scene, the emotional gut punch. "
        "Write topics as enthusiastic fan recommendations in Japanese.\n"
    ),
}

_LANG_AUDIENCE = {
    "en": "English-speaking global",
    "ja": "Japanese-speaking",
}


class LLMTopicSelector:
    def __init__(self, model: str = "claude-sonnet-4-6", history_path: Path | None = None):
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = model
        self.history_path = history_path or DEFAULT_HISTORY_PATH

    # ── History helpers ───────────────────────────────────────────────────────

    def _load_history(self) -> list[dict]:
        if self.history_path.exists():
            try:
                return json.loads(self.history_path.read_text())
            except Exception:
                return []
        return []

    def record(self, topic: str, genre: str, lang: str) -> None:
        """Persist a used topic so future suggestions avoid it."""
        history = self._load_history()
        history.append({"topic": topic, "genre": genre, "lang": lang})
        self.history_path.write_text(json.dumps(history, indent=2, ensure_ascii=False))
        logger.debug("Recorded topic to history: %s", topic)

    # ── Core methods ──────────────────────────────────────────────────────────

    def suggest(self, genre: str = "general", lang: str = "en", count: int = 5, use_trends: bool = False) -> list[str]:
        lang_audience = _LANG_AUDIENCE.get(lang, "global")
        genre_hint = _GENRE_HINTS.get(genre, "")

        # Build avoid-hint from history (last 50 entries for this genre+lang)
        history = self._load_history()
        past = [
            e["topic"] for e in history
            if e.get("genre") == genre and e.get("lang") == lang
        ][-50:]
        if past:
            lines = "\n".join(f"  × {t}" for t in past)
            avoid_hint = f"\n- ALREADY USED — do NOT repeat or make variations of these:\n{lines}\n"
            logger.info("Excluding %d previously used topics from suggestions", len(past))
        else:
            avoid_hint = ""

        # Optionally seed with Google Trends rising queries
        trend_hint = ""
        if use_trends:
            from src.adapters.trend_research import GoogleNewsTrendResearcher
            researcher = GoogleNewsTrendResearcher()
            rising = researcher.fetch(genre=genre, lang=lang)
            if rising:
                lines = "\n".join(f"  → {q}" for q in rising)
                trend_hint = (
                    f"\n- TRENDING NOW on Japanese social media (use as creative inspiration"
                    f" — adapt angle, do not copy directly):\n{lines}\n"
                )
                logger.info("Injected %d trend seeds into prompt", len(rising))

        prompt = _PROMPT.format(
            genre=genre,
            count=count,
            lang_audience=lang_audience,
            genre_hint=genre_hint,
            avoid_hint=avoid_hint + trend_hint,
        )
        logger.info("Requesting %d topic suggestions (genre=%s, lang=%s)", count, genre, lang)

        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text.strip()
                start = raw.find("[")
                end = raw.rfind("]")
                if start != -1 and end != -1:
                    raw = raw[start:end + 1]
                topics = json.loads(raw)
                logger.info("Got %d topic suggestions (attempt %d)", len(topics), attempt)
                return topics
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning("JSON parse failed (attempt %d/3): %s — retrying", attempt, e)

        raise ValueError(f"Topic suggestion failed after 3 attempts: {last_error}")

    def select(
        self,
        genre: str = "general",
        lang: str = "en",
        interactive: bool = False,
        count: int = 5,
        use_trends: bool = False,
    ) -> str:
        topics = self.suggest(genre=genre, lang=lang, count=count, use_trends=use_trends)

        if not interactive:
            chosen = topics[0]
            logger.info("Auto-selected topic: %s", chosen)
            self.record(chosen, genre, lang)
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
                chosen = input("Enter your topic: ").strip()
                self.record(chosen, genre, lang)
                return chosen
            if raw.isdigit() and 1 <= int(raw) <= len(topics):
                chosen = topics[int(raw) - 1]
                logger.info("User selected topic: %s", chosen)
                self.record(chosen, genre, lang)
                return chosen
            print(f"Please enter a number between 0 and {len(topics)}.")
