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
    "religion2": (
        "ultra-photorealistic 8K real photograph, "
        "overflowing with warm luminous positive energy — "
        "clear quartz crystals exploding with rainbow light on a white linen surface, "
        "a sunlit altar of fresh flowers, gold coins and citrine in full bloom, "
        "god-rays streaming through a Japanese shrine torii gate onto golden moss, "
        "a hand cradling a glowing rose quartz sphere with soft bokeh behind it, "
        "cherry blossom petals raining down on a stone path at first light, "
        "or a full moon rising over a calm ocean scattering golden light — "
        "palette: radiant gold, warm ivory, soft rose, luminous lavender — NEVER dark or ominous, "
        "the entire frame should feel like sunshine on skin, abundant and overflowing with good fortune, "
        "no faces, no text in image, "
        "the kind of image that makes viewers feel: '見ただけで運気が上がった気がする'"
    ),
    "lifestyle": (
        "ultra-photorealistic 8K lifestyle photography, "
        "real person in a beautiful everyday moment, "
        "warm soft natural window light, shallow bokeh background, "
        "authentic candid feel — not posed stock photo, "
        "the kind of real photo that stops you while scrolling"
    ),
    "selfhelp": (
        "ultra-photorealistic 8K real photograph, "
        "capturing the exact TURNING POINT moment of personal transformation — "
        "a lone silhouette cresting a mountain summit at first light (the breakthrough), "
        "a hand releasing a bird into open sky (letting go), "
        "a single door swinging open to flood a dark room with golden light (the decision to change), "
        "broken chain links on stone ground (freedom from a habit), "
        "a seed cracking through dry earth toward sunlight (growth against resistance) — "
        "figure always in pure backlit silhouette — no facial features visible, "
        "warm dawn orange and gold palette, strong backlight, dramatic sense of forward momentum, "
        "no faces, no text in image, looks like a real photograph — "
        "the kind of image that makes viewers feel: 'this is the moment everything changes'"
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
        "ultra-photorealistic 8K beauty and fashion photograph, "
        "radiant Japanese or Korean woman — flawless skin, perfectly styled hair, elegant fashion — "
        "or close-up of luxury beauty tools, cosmetic products, a stunning hair transformation, "
        "or an aesthetic clinic's minimalist treatment room, "
        "soft diffused natural window light or softbox, clean minimal aesthetic, pastel or white background, "
        "K-beauty or J-beauty inspired palette — serene, aspirational, deeply satisfying to look at"
    ),
    "kdrama_intro": (
        "ultra-cinematic 8K Korean drama promotional still, "
        "iconic K-drama visual aesthetic — Han River night view, luxury penthouse rooftop, "
        "Seoul streets with neon reflections, cherry blossom campus paths, "
        "or a chaebol's modern minimalist office — "
        "rich teal-and-orange cinematic color grade, anamorphic lens flare, "
        "the kind of frame that stops you mid-scroll and makes you search for the show immediately — "
        "vertical portrait 9:16 cinematic composition"
    ),
    "bl_intro": (
        "ultra-cinematic 8K Boys Love drama promotional still, "
        "two beautiful young Asian men in intimate emotionally charged moments — "
        "one quietly handsome with cool composure, the other soft and endearingly vulnerable — "
        "dreamy pastel and soft lavender color palette, backlighting creating a romantic glow, "
        "the kind of promotional frame that makes BL fans clutch their hearts and "
        "immediately add it to their watchlist — vertical portrait 9:16 cinematic composition"
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
        "the visual language of sudden, unexpected wealth — "
        "a smartphone screen exploding with green crypto candles in a dark room, "
        "stacks of ¥10,000 bills fanned out on a desk next to a racing form, "
        "a lone trader's silhouette against multiple glowing screens at night, "
        "gold coins and a cracked phone showing a brokerage account balance that just changed everything, "
        "or a hand holding a racetrack ticket surrounded by confetti — "
        "dramatic high-contrast lighting, electric green or gold against deep black, "
        "no faces, no text in image, "
        "the kind of image that makes viewers think: '俺も、私も——もしかしたらいけるんじゃないか'"
    ),
    "psychology": (
        "ultra-photorealistic 8K real photograph, "
        "a single object or scene that makes the INVISIBLE workings of the mind suddenly VISIBLE — "
        "a glass brain model lit by cold blue light casting complex shadows, "
        "two diverging paths in a fog-covered forest (the moment of a decision), "
        "a hand holding a cracked mirror reflecting distorted light (cognitive bias), "
        "neural-like patterns in frost on glass, a chess piece standing alone on an empty board, "
        "or a closed door with warm light leaking underneath (repressed thought) — "
        "dramatic high-contrast lighting, deep blue-violet or slate-grey palette with one warm accent, "
        "shallow depth of field, no faces, no text in image, "
        "the kind of image that makes viewers think: 'my brain is doing this right now and I never noticed'"
    ),
    "general": (
        "ultra-photorealistic 8K real photograph, "
        "dramatic natural lighting, vivid colors, emotionally compelling real-world scene"
    ),
    "investor": (
        "ultra-photorealistic 8K real photograph, "
        "the cold, clinical world of professional finance — "
        "multiple Bloomberg terminal screens casting teal light on empty chairs at 2am, "
        "a Financial Times front page on a mahogany desk, "
        "macro data printouts annotated in red pen, a chess board with only two pieces remaining, "
        "a hand drawing a contrarian arrow on a whiteboard full of charts — "
        "dramatic high-contrast lighting, deep navy and teal palette, cold authoritative atmosphere, "
        "no faces, no text in image, "
        "the kind of image that makes viewers feel they just stepped inside a world most people are never allowed to see"
    ),
    "drama_kdrama": (
        "ultra-cinematic 8K Korean drama still frame, "
        "exceptionally handsome Korean male lead and strikingly beautiful Korean female lead — "
        "visually stunning faces with flawless skin, strong jawline, expressive eyes — "
        "in emotionally charged scenes: luxury penthouse with Han River view, "
        "rooftop under neon signs, tearful close-ups in golden hour backlight, dim library at closing time, "
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
        "in intensely sensual scenes: pinned against a window after a heated kiss, "
        "shirt collar pulled open and chest flushed, the smaller one looking up with parted lips, "
        "tangled together in the backseat of a car, or forehead pressed against forehead under streetlight — tastefully suggestive, never explicit — "
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
        "- Scene 1 (一攫千金フック): 普通の人が普通じゃない方法で稼いだ実話を一行で掴む。「競馬AIで年収超えた会社員」「仮想通貨で元手30万が3000万になった日」——視聴者が「え、マジ？」と止まる瞬間。\n"
        "- Scene 2 (その人のリアル): 主人公はどんな普通の人だったか。職業・状況・きっかけ。具体的な数字（年齢・元手・期間）を必ず入れる。リアルなほど刺さる。\n"
        "- Scene 3 (一つの転換点): 何をどう変えたのか——ツール名・考え方の転換・具体的なタイミング。「誰でも再現できそう」と感じる具体性が命。\n"
        "- Scene 4 (普通の人との唯一の違い): 成功した人が持つ、普通の人と根本的に異なる金に対する考え方を一言で表す。名前をつける（例：「損切り哲学」「確率思考」）。抽象論ではなく行動レベルの違いを語る。\n"
        "- Scene 5 (今日の一手): 視聴者が今日・今週から実際にできる具体的な一つのアクション。アプリ名・金額・時間など数字を入れて再現可能にする。「やるかやらないかの差はここだけ」と締める。\n"
        "- Scene 6 (教訓＋CTA): 「結局この話が教えてくれること——[一行の教訓]」で締め、「保存して忘れるな」「これを知らずにいた自分に送って」と背中を押す。教訓なしのCTAだけは禁止。"
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
        "- Scene 1 (HOOK): Open with a surprising beauty secret, transformation result, or 'you've been doing this wrong' revelation — make viewers stop scrolling.\n"
        "- Scene 2 (PROBLEM): Show the relatable struggle — a skin issue, a hair dilemma, a fashion mistake, or an aging concern most people face.\n"
        "- Scene 3 (THE SECRET): Reveal the insider tip, ingredient, technique, procedure, or style hack that changes everything.\n"
        "- Scene 4 (SCIENCE OR EXPERT): One satisfying fact about why it works — dermatologist-backed, stylist-approved, or clinical research.\n"
        "- Scene 5 (TRANSFORMATION): The before/after moment or the 'this is the result' payoff — make it aspirational.\n"
        "- Scene 6 (CTA): A save-worthy closer like 'bookmark this' or 'try this tonight'."
    ),
    "kdrama_intro": (
        "- Scene 1 (HOOK): Open with the drama's most viral, talked-about, or visually stunning moment — make viewers feel they're missing out.\n"
        "- Scene 2 (STORY SETUP): The premise in one irresistible line — the leads, the central conflict, the reason viewers can't stop watching.\n"
        "- Scene 3 (THE CHEMISTRY): The lead pair's dynamic — their tension, their charm, the moment that made fans lose their minds.\n"
        "- Scene 4 (THE SCENE): The scene or plot twist everyone is talking about — tease without fully spoiling.\n"
        "- Scene 5 (WHY WATCH NOW): The emotional payoff — why this drama specifically hits different right now.\n"
        "- Scene 6 (CTA): 'Add this to your watchlist tonight' or 'send to your K-drama partner'."
    ),
    "bl_intro": (
        "- Scene 1 (HOOK): Open with the BL content's most squeal-worthy or emotionally devastating moment — 'this BL wrecked me'.\n"
        "- Scene 2 (STORY SETUP): Who are the two leads, what is their relationship, why is their dynamic irresistible.\n"
        "- Scene 3 (THE CHEMISTRY): The moment BL fans live for — the pining, the almost-touch, the first confession, or the charged look.\n"
        "- Scene 4 (THE SCENE): The scene everyone screenshots and saves — describe it vividly enough that viewers must find it.\n"
        "- Scene 5 (WHY IT HITS): What makes this BL special — the writing, the performances, the emotional depth, what makes it different.\n"
        "- Scene 6 (CTA): 'Read/watch this immediately' or 'tag your BL partner in crime'."
    ),
    "investor": (
        "- Scene 1 (CONTRARIAN HOOK): マーケットの通説を真っ向否定する一行で掴む。FT・WSJ・The Economistのヘッドライン感覚——『市場が間違っている理由』『誰も言わない中央銀行の矛盾』『バフェットが今売っているもの』。\n"
        "- Scene 2 (MACRO CONTEXT): なぜ今この話が重要か。マクロ経済・地政学・金融サイクルのどこにいるかを冷静に俯瞰する。\n"
        "- Scene 3 (THE EDGE): プロだけが使う指標・シグナル・フレームワーク。具体的な数字・データ・チャートパターンで論証する。抽象論NG。\n"
        "- Scene 4 (CONTRARIAN CASE): 一般投資家が信じている通説の何が間違いか。コントラリアンな視点と、それを支持する歴史的証拠。\n"
        "- Scene 5 (RISK/POSITION): このテーゼのリスクと、それでもポジションを取る理由。プロが実際に使う条件・撤退ライン・サイズ感。\n"
        "- Scene 6 (CTA): 今すぐ確認すべき具体的な指標・銘柄・ニュースソース。知的好奇心を刺激して保存させる締め。"
    ),
    "religion2": (
        "- Scene 1 (光のフック): 見ただけで運気が上がりそうな、ポジティブなエネルギーで掴む。禁忌や恐怖ではなく『これを知ったら今日から運が変わる』という希望の角度から入る。\n"
        "- Scene 2 (宇宙の仕組み): なぜそれが運気・引き寄せに繋がるのか。難しくなく、温かく、『なるほど、そういうことか』と腑に落ちる説明。\n"
        "- Scene 3 (今すぐできる開運アクション): 一つの具体的で簡単な行動——置く・持つ・唱える・整える。やった瞬間から気持ちが上がるもの。\n"
        "- Scene 4 (宇宙からのサイン): 運気が上がっているときに起こる出来事・変化・シンクロニシティ。『これ、最近あった！』と視聴者が思わず頷く内容。\n"
        "- Scene 5 (豊かさのビジョン): それを続けた先にある明るい未来。金運・人間関係・健康——どれでも良い。希望と豊かさで満たす。\n"
        "- Scene 6 (CTA): 「運気を上げたい人に送って」「保存して今日から試して」と温かく明るく締める。ネガティブな言葉は一切使わない。"
    ),
    # Drama genres store only the tone/character note here.
    # The actual arc-selection structure is injected by build_prompt() via _DRAMA_ARCS.
    "drama_kdrama": (
        "スタイル：韓国ドラマ。財閥・身分差・雨のシーン・漢江の夜景が似合う。感情表現は大きく、"
        "色彩豊か。キスシーンは映画的に、ドラマポスターのような構図で。"
    ),
    "drama_romance": (
        "スタイル：日本のロマンティックドラマ。繊細な日本的感性、抑制された感情、"
        "言葉より「間」が大切。官能的な緊張感は直接的な描写を避けつつ最大限に高める。"
    ),
    "drama_bl": (
        "スタイル：日本BLドラマ。20代の日本人男性二人。甘く柔らかい感情表現、"
        "パステル・淡い光の映像美。胸が痛くなるほどの繊細さと、抑えきれない引力。"
    ),
    "drama_korean_bl": (
        "スタイル：韓国BLドラマ。20代の韓国人男性二人。強くクールな一方と、可愛らしく"
        "ドギマギする一方。ネオン・雨・煙草・ジャケット——激しくギリギリまで官能的に。"
    ),
}

_DRAMA_ARCS = """\
トピックのプレミスを読み、最も合うアークを一つ選んで、そのシーン構成に従うこと。

━━ ARC A: 急速接近型 ━━ (運命の出会い・一目惚れ・身分差の禁断愛・契約から始まる関係)
- Scene 1 (出会いの衝撃): 二人が初めて交差する瞬間——偶然か必然か、息を呑む出会い。
- Scene 2 (惹かれる瞬間): 距離が縮まる場面。言葉より先に、視線と仕草が語る。
- Scene 3 (すれ違い): 誤解・秘密・身分差——二人を引き裂く葛藤が表面化する。
- Scene 4 (転換点): 感情が爆発する瞬間——場所・天気・状況はトピックに合わせて自由に選ぶ。どこかで何かが決壊する。
- Scene 5 (クライマックス): 告白・抱擁・キス——関係が決定的に変わる感情の頂点。
- Scene 6 (余韻): 次を予感させる余韻。セリフか沈黙で視聴者の心を引き留める。

━━ ARC B: スローバーン型 ━━ (幼馴染・同僚・ずっと側にいた人・気づかなかった感情)
- Scene 1 (いつもの日常): 二人の当たり前の距離感——でも今日だけ、何かが違って見える。
- Scene 2 (小さな違和感): 触れた指・交わった視線・無意識の行動——心臓が、少しだけうるさい。
- Scene 3 (認めたくない): 「これは友情だ」と言い聞かせる内面。でも体は正直だった。
- Scene 4 (限界の手前): 誰かの一言・別れの予感・第三者の存在——気持ちが溢れそうになる。
- Scene 5 (ようやく届く): 言葉にならなかった感情が、ついに相手に届く瞬間。
- Scene 6 (余韻): 変わった距離感、変わらない声——でも全てが変わった。静かな幸福。

━━ ARC C: 再会型 ━━ (別れた恋人・忘れられない初恋・記憶喪失・数年後の再会)
- Scene 1 (再会の瞬間): もう会わないと思っていた人が、目の前にいる。
- Scene 2 (過去の影): 二人の間にある歴史——喜びか痛みか、あの頃の記憶がよみがえる。
- Scene 3 (変わったもの、変わらないもの): 時間が二人に何を与え、何を奪ったか。
- Scene 4 (感情の再燃): 消えたはずの気持ちが、まだそこにあった。
- Scene 5 (選択): もう一度向き合うか、離れるか——どちらを選んでも、痛い。
- Scene 6 (余韻): 答えより感情を残す。視聴者の胸に問いかけて終わる。

━━ ARC D: 悲恋型 ━━ (叶わない愛・別れで終わる話・片想いの完結・身分差で結ばれない)
- Scene 1 (美しい始まり): 二人が最も近かった瞬間——幸福で、だからこそ切ない。
- Scene 2 (忍び寄る影): 別れの理由・障壁・タイムリミットが見え始める。
- Scene 3 (それでも): わかっていても離れられない——愛することをやめられない。
- Scene 4 (最後の時間): 終わりが近いと知りながら過ごす、密度の高い瞬間。
- Scene 5 (別れ): 言葉か沈黙か——どちらにせよ、胸が痛い別れ。
- Scene 6 (余韻): 残されたもの——物・言葉・記憶。悲しくて、でも美しい。

━━ ARC E: 敵から恋へ型 ━━ (ライバル・反目・嫌いなはずの相手・強制同居・契約)
- Scene 1 (火花): 二人の対立——言葉が刃のように交わされる。でも視線が離せない。
- Scene 2 (崩れる瞬間): 強がりの向こうに見えた本当の顔——その一瞬で何かが変わる。
- Scene 3 (認めたくない引力): 「嫌いだ」と言い聞かせるほど、頭から離れない。
- Scene 4 (共に立つ瞬間): 二人が同じ方向を向く——敵ではなく、味方だと気づく。
- Scene 5 (クライマックス): もう嘘はつけない——感情が、全てを上書きする。
- Scene 6 (余韻): 変わった関係の新しい始まり——または、まだ言えない感情の続き。
"""

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
    if is_drama:
        genre_tone = _NARRATIVE_STRUCTURES.get(genre, "")
        narrative_structure = genre_tone + "\n\n" + _DRAMA_ARCS
    else:
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
