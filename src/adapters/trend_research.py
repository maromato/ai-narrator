"""
Trend research adapter — fetches current headlines from Google News RSS
and returns them as topic seeds for the LLM topic selector.

No API key required. Uses Google News RSS (free, reliable).
"""
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# Strip leading emoji / punctuation symbols from RSS titles
_JUNK_PREFIX = re.compile(r"^[\U00010000-\U0010ffff\u2000-\u27ff！。、「」【】◆◇■□★☆…\s]+")


logger = logging.getLogger(__name__)

# Genre → search queries to send to Google News
_GENRE_QUERIES: dict[str, dict[str, list[str]]] = {
    "academia": {
        "ja": ["ハーバード大学", "ハーバード生の生活", "ハーバード留学", "ハーバード合格"],
        "en": ["Harvard university secrets", "Harvard student life"],
    },
    "elite_edu": {
        "ja": ["東大 京大 合格", "一流大学 勉強法", "受験 偏差値 秘訣", "エリート 思考法"],
        "en": ["Harvard MIT study method", "elite university learning"],
    },
    "finance": {
        "ja": ["爆益 投資 2026", "金持ち 成功者の習慣"],
        "en": ["billionaire habits wealth", "investor success secrets"],
    },
    "psychology": {
        "ja": ["心理学", "脳科学", "人間関係 心理", "メンタル 感情", "認知バイアス"],
        "en": ["psychology behavior surprising", "cognitive bias everyday"],
    },
    "science": {
        "ja": ["宇宙 最新発見", "量子力学 不思議", "生物 衝撃の事実", "AI 研究 最新"],
        "en": ["science discovery shocking", "space surprising facts"],
    },
    "history": {
        "ja": ["戦国時代 真実", "幕末 衝撃", "昭和 知られていない事件", "偉人 意外な素顔"],
        "en": ["history surprising facts", "historical secrets unknown"],
    },
    "animals": {
        "ja": ["犬 かわいい", "猫 不思議な行動", "ペット 癒し", "動物 感動エピソード"],
        "en": ["dog behavior science", "pet psychology study"],
    },
    "religion": {
        "ja": ["神社 パワースポット", "仏教 教え 現代", "お守り 御利益", "スピリチュアル 話題"],
        "en": ["religion surprising history", "spiritual facts unknown"],
    },
    "lifestyle": {
        "ja": ["健康 ダイエット 最新", "睡眠 質 改善", "食事 体に良い", "ウェルネス 習慣"],
        "en": ["lifestyle health science 2026", "morning routine benefits"],
    },
    "selfhelp": {
        "ja": ["自己啓発", "モチベーション 上げる", "朝活 成功者", "メンタル強化 習慣"],
        "en": ["habit formation science", "self improvement research"],
    },
    "workplace": {
        "ja": ["副業 稼ぐ", "年収アップ 転職", "仕事術 デキる人", "フリーランス キャリア"],
        "en": ["productivity science research", "workplace psychology tips"],
    },
    "japan_travel": {
        "ja": ["日本 秘境 絶景", "温泉 穴場", "旅行 知られていない", "観光地 ローカル"],
        "en": ["hidden Japan spots 2026", "secret Japan travel"],
    },
    "japan_zen": {
        "ja": ["瞑想 マインドフルネス", "断捨離 シンプルな暮らし", "禅 侘び寂び", "日本文化 深い意味"],
        "en": ["zen philosophy modern life", "Japanese mindfulness culture"],
    },
    "romance": {
        "ja": ["恋愛", "恋バナ", "ドキドキ 恋愛心理", "オトコごごろ", "オンナごごろ", "デート 距離感", "彼氏 彼女 秘密"],
        "en": ["relationship psychology study", "attraction science research"],
    },
    "mens_life": {
        "ja": ["モテる 男 習慣", "筋トレ 男磨き", "メンズファッション", "30代 男 仕事 人生"],
        "en": ["men lifestyle habits science", "men self improvement"],
    },
    "general": {
        "ja": ["バズ 豆知識", "知らなかった 衝撃", "雑学 面白い", "話題 トレンド 2026"],
        "en": ["TikTok viral facts 2026", "shocking facts trending"],
    },
    "beauty": {
        "ja": ["スキンケア 美肌 秘訣", "コスメ 話題 2026", "美容 皮膚科 おすすめ", "メイク テク 時短"],
        "en": ["skincare secrets dermatologist", "beauty tips viral 2026"],
    },
    "finance2": {
        "ja": ["機関投資家 戦略 2026", "ヘッジファンド 手法 空売り", "オプション取引 上級", "億り人 投資術 爆益"],
        "en": ["hedge fund strategy 2026", "institutional investor tactics", "options trading advanced"],
    },
    "drama_kdrama": {
        "ja": ["韓国ドラマ 話題 2026", "韓ドラ 胸キュン", "財閥 恋愛 ドラマ", "韓国 縦型ドラマ バズ"],
        "en": ["Korean drama trending 2026", "kdrama romance viral"],
    },
    "drama_romance": {
        "ja": ["恋愛ドラマ 胸キュン 2026", "日本 ロマンス 縦型ドラマ", "片思い 再会 切ない"],
        "en": ["Japanese romance drama 2026", "short romance drama viral"],
    },
    "drama_bl": {
        "ja": ["BL ドラマ 話題 2026", "ボーイズラブ 縦型動画", "BL 胸キュン シーン"],
        "en": ["BL drama trending 2026", "boys love short drama viral"],
    },
    "drama_korean_bl": {
        "ja": ["韓国BL ドラマ 2026", "Korean BL 話題", "韓ドラ 男同士 恋愛"],
        "en": ["Korean BL drama trending 2026", "K-BL romance viral"],
    },
}

_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"


def _rss_url(query: str, lang: str) -> str:
    if lang == "ja":
        hl, gl, ceid = "ja", "JP", "JP:ja"
    else:
        hl, gl, ceid = "en-US", "US", "US:en"
    return _NEWS_RSS.format(
        query=urllib.parse.quote(query),
        hl=hl, gl=gl, ceid=ceid,
    )


def _fetch_titles(url: str, timeout: int = 8) -> list[str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            tree = ET.parse(r)
        root = tree.getroot()
        titles = []
        for item in root.findall(".//item"):
            t = item.find("title")
            if t is not None and t.text:
                # Strip " - Source Name" suffix that Google News appends
                title = t.text.split(" - ")[0].strip()
                title = _JUNK_PREFIX.sub("", title).strip()
                if len(title) > 10:  # skip fragments
                    titles.append(title)
        return titles
    except Exception as e:
        logger.debug("RSS fetch failed (%s): %s", url, e)
        return []


class GoogleNewsTrendResearcher:
    """Fetches current Google News headlines to seed topic generation."""

    def __init__(self, max_results: int = 8):
        self.max_results = max_results

    def fetch(self, genre: str, lang: str = "ja") -> list[str]:
        """Return a list of recent headline strings for the genre."""
        queries = _GENRE_QUERIES.get(genre, _GENRE_QUERIES["general"]).get(lang, [])
        if not queries:
            return []

        all_titles: list[str] = []
        for query in queries:
            url = _rss_url(query, lang)
            titles = _fetch_titles(url)
            all_titles.extend(titles)

        # Deduplicate, preserve order
        seen: set[str] = set()
        unique: list[str] = []
        for t in all_titles:
            if t and t not in seen:
                seen.add(t)
                unique.append(t)

        result = unique[: self.max_results]
        logger.info(
            "Google News returned %d headlines for genre=%s lang=%s", len(result), genre, lang
        )
        return result
