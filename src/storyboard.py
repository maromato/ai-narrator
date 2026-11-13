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
        "capturing one specific intimate human moment — a face, a hand, an object, a single scene — "
        "not a grand battle but a close personal detail that makes history feel real and touchable, "
        "dramatic natural torchlight or golden-hour sunlight, shallow depth of field, "
        "looks like an actual photograph taken in that exact moment in history"
    ),
    "science": (
        "ultra-photorealistic 8K real scientific photograph, "
        "one extreme close-up or one vast scale — either stunning macro (cells, crystals, insects) "
        "or breathtaking astronomical scale (nebula, planet surface, deep ocean), "
        "the kind of single image that makes viewers stop and whisper 'wait, this is real?' — "
        "genuine NASA, BBC Planet Earth, or scientific journal photography quality"
    ),
    "animals": (
        "ultra-photorealistic 8K real photograph of a dog, "
        "irresistibly cute and emotionally expressive face — big eyes, floppy ears, tilted head, "
        "warm soft natural light, shallow bokeh background, "
        "the kind of dog photo that makes viewers say 'oh my god' and immediately want to share it — "
        "pure joy, love, and adorableness captured in a real candid moment"
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
        "a hidden or lesser-known location — secret mountain onsen, quiet rural village, "
        "misty bamboo forest path, lantern-lit old merchant street, "
        "warm bright cheerful atmosphere — soft golden morning light or glowing sunset, "
        "inviting and joyful, not dramatic or mysterious, "
        "the kind of real photo that makes viewers immediately open Google Maps to find this place"
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
        "strikingly handsome Japanese man and breathtakingly beautiful Japanese woman — "
        "perfect features, luminous skin, expressive eyes — in intimate relatable everyday moments, "
        "soft natural golden bokeh lighting, heartfelt genuine emotions, "
        "candid documentary style — the kind of real photo that makes viewers think 'this is exactly me'"
    ),
    "mens_life": (
        "ultra-photorealistic 8K real photograph, "
        "confident stylish young Japanese man in authentic real-life situation in Tokyo or modern Japanese city, "
        "dramatic natural or street lighting, genuine emotional expression — "
        "candid documentary style, not posed, deeply relatable to men aged 20-35"
    ),
    "beauty": (
        "ultra-photorealistic 8K beauty photograph, "
        "radiant Japanese woman with flawless skin in a minimal clean aesthetic setting — "
        "soft diffused natural window light or softbox, pastel or pure white background, "
        "close-up textures of dewy skin, luxury skincare products or cosmetics artfully arranged, "
        "K-beauty or J-beauty inspired palette — serene, aspirational, deeply satisfying to look at"
    ),
    "academia": (
        "ultra-photorealistic 8K real photograph, "
        "iconic Harvard University setting — Widener Library interior, Harvard Yard red-brick paths, "
        "Memorial Hall stained glass, or a dimly lit Harvard study room at night, "
        "leather-bound books, handwritten notes, single desk lamp casting warm light on equations, "
        "lone scholar in deep intellectual focus — "
        "looks like a real documentary photograph from inside Harvard's secret world"
    ),
    "elite_edu": (
        "ultra-photorealistic 8K real photograph, "
        "prestigious university campus — Harvard, MIT, or Stanford — "
        "students in focused study sessions, whiteboards filled with frameworks, "
        "collaborative group discussions in modern innovation labs or historic reading rooms, "
        "warm academic lighting, aspirational yet approachable atmosphere — "
        "the kind of image that makes viewers think 'I want to learn like this'"
    ),
    "finance": (
        "ultra-photorealistic 8K real photograph, "
        "visually striking money metaphor — hands holding cash, stock ticker screens reflecting on a face, "
        "contrast between wealthy and ordinary life captured candidly, "
        "dramatic urban financial district lighting or intimate home budget scene, "
        "the kind of real image that makes viewers immediately think about their own money"
    ),
    "psychology": (
        "ultra-photorealistic 8K real photograph, "
        "a single human face or gesture expressing a complex emotion — surprise, realization, vulnerability, "
        "intimate shallow depth of field, dramatic side-lighting revealing texture and feeling, "
        "the kind of real portrait that makes viewers feel seen and understood — "
        "not clinical, deeply human and emotionally resonant"
    ),
    "general": (
        "ultra-photorealistic 8K real photograph, "
        "dramatic natural lighting, vivid colors, emotionally compelling real-world scene"
    ),
    "drama_kdrama": (
        "ultra-cinematic 8K Korean drama still frame, "
        "exceptionally handsome Korean male lead and strikingly beautiful Korean female lead — "
        "visually stunning faces with flawless skin, strong jawline, expressive eyes — "
        "in emotionally charged scenes: rain-soaked streets at night, luxury penthouse with Han River view, "
        "rooftop under neon signs, tearful close-ups in golden hour backlight, "
        "occasionally an achingly beautiful first kiss — lips barely touching, eyes fluttering closed, "
        "anamorphic lens flare, shallow depth of field, desaturated teal-and-orange color grade, "
        "every frame looks like a drama poster shot — vertical portrait 9:16 cinematic composition"
    ),
    "drama_romance": (
        "ultra-cinematic 8K Japanese romantic drama still frame, "
        "strikingly handsome Japanese man and breathtakingly beautiful Japanese woman — "
        "perfect features, luminous skin, deeply expressive eyes — "
        "in sensually charged intimate scenes: dim city-glow bedroom with disheveled sheets, "
        "a tender kiss deepening in soft backlight, flushed cheeks and parted lips after a kiss, "
        "his hand sliding to her waist pulling her close, her fingers curling into his shirt, "
        "foreheads pressed together catching breath — tastefully suggestive, never explicit — "
        "warm amber and soft rose color grade, shallow depth of field, "
        "every frame smolders with restrained desire — vertical portrait 9:16 cinematic composition"
    ),
    "drama_bl": (
        "ultra-cinematic 8K Boys Love drama still frame, "
        "two beautiful Japanese men in their early-to-mid twenties (20-26 years old) — "
        "one tall and quietly handsome with sharp features and a cool gaze, "
        "the other boyishly cute with soft round eyes, gentle smile, and an innocent warmth — "
        "in sensually charged intimate scenes: the taller pressing the smaller against a wall, "
        "a breathless kiss with collar undone and hair disheveled, "
        "lying side by side in dim lamplight their faces inches apart, "
        "one's hand trembling as it reaches for the other's — tastefully suggestive, never explicit — "
        "soft pastel and cool blue-grey color grade, achingly tender close-ups, "
        "every frame smolders with unspoken longing — vertical portrait 9:16 cinematic composition"
    ),
    "drama_korean_bl": (
        "ultra-cinematic 8K Korean BL drama still frame, "
        "two beautiful Korean men in their twenties (20-29 years old) — "
        "one powerfully handsome with sharp jawline, smoldering eyes and commanding presence, "
        "the other adorably cute with doe eyes, soft features, and an endearing flustered expression — "
        "in intensely sensual scenes: pinned against a rain-streaked window after a heated kiss, "
        "shirt collar pulled open and chest flushed, the smaller one looking up with parted lips, "
        "tangled together in the backseat of a car under neon light — tastefully suggestive, never explicit — "
        "desaturated teal-and-rose color grade, anamorphic lens flare, "
        "every frame crackles with barely restrained desire — vertical portrait 9:16 cinematic composition"
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
    "history": (
        "- Scene 1 (HOOK): Open with one hyper-specific, surprising detail — not 'Rome fell' but 'the last Roman Emperor was 16 years old and nobody remembers his name'.\n"
        "- Scene 2 (ZOOM IN): Focus on one real person, one object, or one single moment — make history feel human and close.\n"
        "- Scene 3 (THE DETAIL): Reveal the specific fact or detail that changes how viewers see this moment.\n"
        "- Scene 4 (REFRAME): 'What most people believe' vs 'what actually happened' — the surprising truth.\n"
        "- Scene 5 (RESONANCE): Why this still matters today — connect the past to the viewer's present.\n"
        "- Scene 6 (CLOSE): A single powerful line that makes viewers feel they just learned something nobody else knows."
    ),
    "science": (
        "- Scene 1 (HOOK): Open with one image or fact so extreme it breaks the viewer's sense of scale — 'this photo is real'.\n"
        "- Scene 2 (SCALE): Establish just how extreme this phenomenon is — make the viewer feel small or amazed.\n"
        "- Scene 3 (THE MECHANISM): Explain the 'why' in one simple, vivid analogy — no jargon.\n"
        "- Scene 4 (TWIST): The counterintuitive implication — something that challenges what viewers assumed was true.\n"
        "- Scene 5 (WONDER): The bigger picture — what this means for life, the universe, or humanity.\n"
        "- Scene 6 (CLOSE): A closing line that leaves viewers staring at the sky or their own hand differently."
    ),
    "animals": (
        "- Scene 1 (HOOK): Open with the most irresistibly cute or surprising dog moment — the 'oh my god' image.\n"
        "- Scene 2 (CHARM): Show the dog's personality — the tilt, the look, the expression that melts hearts.\n"
        "- Scene 3 (SURPRISING FACT): One amazing thing dogs do that most people don't know — make it feel like a gift.\n"
        "- Scene 4 (EMOTION): The moment that shows the depth of a dog's love or intelligence — genuinely moving.\n"
        "- Scene 5 (BOND): The connection between dog and human — make viewers feel it in their chest.\n"
        "- Scene 6 (CTA): A warm closer like 'hug your dog tonight' or 'share this with someone who needs a smile'."
    ),
    "academia": (
        "- Scene 1 (HOOK): Open with a Harvard-specific hook — 'Harvard's most secret course', 'what Harvard teaches on day 1 that changes everything', or a surprising Harvard fact.\n"
        "- Scene 2 (HARVARD CONTEXT): Ground it in Harvard specifically — the library, the professor, the research lab.\n"
        "- Scene 3 (THE KNOWLEDGE): The core insight — smart but accessible, like a brilliant friend explaining it.\n"
        "- Scene 4 (SURPRISING TWIST): The counterintuitive part — 'even most Harvard graduates get this wrong'.\n"
        "- Scene 5 (APPLICATION): How to use this in real life — immediately actionable.\n"
        "- Scene 6 (CTA): 'Save this — most people never get access to what Harvard teaches' or 'share with someone you want to impress'."
    ),
    "elite_edu": (
        "- Scene 1 (HOOK): Open with an elite-university-sourced insight — 'MIT teaches this on day 1', 'Stanford's #1 study rule', or 'Harvard MBAs all do this differently'.\n"
        "- Scene 2 (THE METHOD): Introduce the specific technique, framework, or mindset — name it, make it feel like a system.\n"
        "- Scene 3 (THE SCIENCE): Why it works — the research or logic behind it, explained simply.\n"
        "- Scene 4 (REAL EXAMPLE): A concrete example of someone applying it — results, transformation, before/after.\n"
        "- Scene 5 (YOUR TURN): How to apply it starting today — specific, step-by-step, no excuses.\n"
        "- Scene 6 (CTA): 'Save this and try it this week' or 'share with someone who wants to level up'."
    ),
    "finance": (
        "- Scene 1 (HOOK): Open with a money fact that makes viewers feel urgent — 'most people lose $X doing this without knowing'.\n"
        "- Scene 2 (SETUP): The relatable financial situation — specific, not generic.\n"
        "- Scene 3 (THE TRICK): One concrete, actionable money move — simple enough to do today.\n"
        "- Scene 4 (THE MATH): Show the numbers — make the impact real and tangible.\n"
        "- Scene 5 (RESULT): What changes when you apply this — be specific about the outcome.\n"
        "- Scene 6 (CTA): 'Save this before you forget' or 'send to someone who needs this'."
    ),
    "psychology": (
        "- Scene 1 (HOOK): Open with a behavior or feeling viewers recognize in themselves — 'you've done this without realizing why'.\n"
        "- Scene 2 (THE PHENOMENON): Name the psychological effect — make it feel like finally having a word for something.\n"
        "- Scene 3 (THE SCIENCE): The research behind it — one study, one finding, explained simply.\n"
        "- Scene 4 (DEEPER TRUTH): The uncomfortable or surprising implication — 'your brain is doing this right now'.\n"
        "- Scene 5 (REFRAME): How knowing this changes how you see yourself or others.\n"
        "- Scene 6 (CTA): 'Share with someone who needs to understand themselves better' or 'save this for when you need it'."
    ),
    "japan_travel": (
        "- Scene 1 (HOOK): Open with a stunning image of a place most viewers have never heard of — 'you've never seen Japan like this'.\n"
        "- Scene 2 (WHERE IS THIS): Reveal the location with delight — the name, the region, why it's special and still under the radar.\n"
        "- Scene 3 (THE EXPERIENCE): What it feels, smells, sounds like to actually be there — make it sensory and vivid.\n"
        "- Scene 4 (THE STORY): A piece of local history, legend, or culture that gives this place soul — why locals love it.\n"
        "- Scene 5 (THE MOMENT): The one experience you can only have here — the onsen at dawn, the festival, the hidden dish.\n"
        "- Scene 6 (CTA): A warm, excited closer like 'add this to your Japan list' or 'save this for your next trip'."
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
    "beauty": (
        "- Scene 1 (HOOK): Open with a surprising beauty secret or 'you've been doing this wrong' revelation — make viewers stop scrolling.\n"
        "- Scene 2 (PROBLEM): Show the relatable struggle — dull skin, uneven tone, a product everyone buys but few use correctly.\n"
        "- Scene 3 (THE SECRET): Reveal the insider tip, ingredient, or technique that changes everything.\n"
        "- Scene 4 (SCIENCE): One satisfying fact about why it works — dermatologist-backed or traditional wisdom.\n"
        "- Scene 5 (TRANSFORMATION): The before/after moment or the 'this is the result' payoff — make it aspirational.\n"
        "- Scene 6 (CTA): A save-worthy closer like 'bookmark this routine' or 'try this tonight'."
    ),
    "drama_kdrama": (
        "- Scene 1 (運命の出会い): 二人が初めて交差する瞬間。偶然か必然か——読者が息を呑む出会いの瞬間を描く。\n"
        "- Scene 2 (惹かれる心): 距離が縮まる場面。言葉ではなく、視線・仕草・沈黙で気持ちを伝える。\n"
        "- Scene 3 (すれ違い): 誤解・秘密・身分差など、二人を引き裂く葛藤が表面化する。\n"
        "- Scene 4 (転換点): 感情が爆発する瞬間——雨の中の言葉、病院の廊下、屋上での叫び。\n"
        "- Scene 5 (クライマックス): 告白・抱擁・キス・別れ——どれでもよい。二人の関係が決定的に変わる感情の頂点を描く。キスシーンは必須ではない。\n"
        "- Scene 6 (余韻): 次の展開を予感させる余韻。セリフや表情で視聴者の心を引き留める。"
    ),
    "drama_romance": (
        "- Scene 1 (出会い直し): すでに知っている二人が、ある瞬間に「特別な人」として見え始める場面。\n"
        "- Scene 2 (距離が縮まる): 偶然の接触、共有する時間——言葉より先に体が反応する。指が触れた瞬間、心臓が跳ねる。\n"
        "- Scene 3 (迷い): 好きだと気づいた瞬間に生まれる躊躇。傷つくのが怖い、でも体が引き寄せられる。\n"
        "- Scene 4 (限界): 抑えていた感情と欲望がついにあふれ出す——気づけば彼の腕の中にいた。\n"
        "- Scene 5 (キス・クライマックス): 唇が重なり、腰に回る腕の力が増す。甘く、熱く、息ができない——世界が二人だけになる瞬間。直接的な描写は避けつつ、官能的な緊張感を最大限に高める。\n"
        "- Scene 6 (余韻): 乱れた髪、上気した頬、明け方の光。言葉より雄弁な沈黙と、その先への予感。"
    ),
    "drama_bl": (
        "- Scene 1 (気づき): 何度も会っているのに、今日だけ違って見えた——その視線が、肌に触れるみたいだった。\n"
        "- Scene 2 (近づく): 触れそうで触れない距離。吐息が届く近さで目が合う——心臓が、うるさい。\n"
        "- Scene 3 (葛藤): これは友情か、それとも——気づいてしまったら、もう戻れない。\n"
        "- Scene 4 (亀裂と転換): 第三者の影、すれ違い——そして限界が来る。もう隠せなかった。\n"
        "- Scene 5 (キス・クライマックス): 壁に押し当てられて、唇が重なる——思ったより、ずっと熱かった。シャツの裾を握る手が震えている。直接的な描写は避けつつ、甘く官能的な緊張感を描く。\n"
        "- Scene 6 (余韻): 乱れた息、離れない視線——夜明けの光の中で、二人の間に新しい距離感が生まれた。"
    ),
    "drama_korean_bl": (
        "- Scene 1 (対立する二人): 反目し合う二人。だが視線が絡むたびに、妙な熱が残る。\n"
        "- Scene 2 (隙を見せる瞬間): 強い男が、一瞬だけ崩れる——その瞬間に何かが火花を散らす。\n"
        "- Scene 3 (距離が消える): 状況が二人を密着させる。触れた体温の濃さに、息が詰まる。\n"
        "- Scene 4 (引き裂かれる): 感情を認めた瞬間に障壁が現れる。でも体はもう、正直だった。\n"
        "- Scene 5 (キス・クライマックス): 壁に追い詰め、雨の中で引き寄せ——唇が激しく重なる。シャツの胸元が乱れ、吐息が混ざり合う——直接的な描写は避けつつ、ギリギリまで官能的な緊張感を描く。\n"
        "- Scene 6 (余韻): 嵐の後の静寂。上気した肌、乱れた呼吸——そして、次の嵐への予感。"
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
    is_drama = genre.startswith("drama_")
    style = GENRE_STYLES.get(genre, GENRE_STYLES["general"])
    genre_label = genre.upper()
    narrative_structure = _NARRATIVE_STRUCTURES.get(genre, _DEFAULT_NARRATIVE)

    if lang == "ja":
        lang_instruction = (
            "- narration と subtitle は必ず日本語で書くこと。\n"
            "- image_prompt は英語のまま（画像生成AIのため）。\n"
            "- script（全体ナレーション）も日本語で書くこと。"
        )
        if is_drama:
            subtitle_rule = "字幕（subtitle）は最大20文字の日本語。ドラマのキャッチコピーや印象的なセリフ・情景描写。"
            narration_rule = "narration は日本語で2〜4文、小説の地の文または三人称ナレーター視点で書く。読み上げ時4〜6秒。"
        else:
            subtitle_rule = "字幕（subtitle）は最大12文字の日本語、感情的でインパクトのあるフレーズ。"
            narration_rule = "narration は日本語で1〜3文、読み上げ時4〜6秒程度。"
    else:
        lang_instruction = ""
        if is_drama:
            subtitle_rule = "Subtitles are drama title-card style — max 8 words, emotionally charged, like a novel chapter title."
            narration_rule = "Narration is literary prose, third-person omniscient, ~4-6 seconds per scene."
        else:
            subtitle_rule = "Subtitles must be ALL CAPS, max 6 words, punchy and emotional."
            narration_rule = "Each narration ~4-6 seconds when spoken aloud (do NOT make them too long)."

    if is_drama:
        creator_role = f"You are a Korean drama scriptwriter and narrator creating a 30-second mini drama episode in {genre_label} style."
        format_note = "30-second mini drama episode (portrait 1080×1920)"
        extra_rules = (
            "- narration must read like literary novel prose or drama voiceover — NOT educational facts.\n"
            "- Each scene should deepen emotion and move the story forward.\n"
            "- hashtags: 5 drama-relevant tags (e.g. #韓ドラ #ドラマ #恋愛 #短編ドラマ #縦型ドラマ).\n"
        )
    else:
        creator_role = f"You are a viral short-form video creator specializing in {genre_label} content for TikTok."
        format_note = "30-second TikTok-style portrait video (1080×1920)"
        extra_rules = (
            "- hashtags: 5 relevant tags including platform-appropriate ones (e.g. #LearnOnTikTok).\n"
            "- The story must feel genuinely compelling — not like a Wikipedia summary.\n"
        )

    return f"""\
{creator_role}

Create a 6-scene storyboard for a {format_note}.

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
{extra_rules}- No field may be null or empty.
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
