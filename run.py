#!/usr/bin/env python3
"""
AI Narrator — CLI entry point

Usage:
  python run.py                                     # default topic, real APIs
  python run.py --topic "Life in Edo Japan"         # custom topic
  python run.py --genre history                     # genre-specific style
  python run.py --topic "Black Holes" --genre science
  python run.py --mock                              # mock mode (no API calls)
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

DEFAULT_TOPIC = "A morning in Ancient Rome"
DEFAULT_GENRE = "general"
DEFAULT_LANG = "en"
CONFIG_PATH = Path(__file__).parent / "config.json"

GENRES = ["general", "history", "science", "animals", "religion", "lifestyle", "selfhelp", "workplace", "japan_travel", "japan_zen", "romance", "mens_life", "academia", "elite_edu", "finance", "psychology"]
LANGS = ["en", "ja"]


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def build_adapters(config: dict, mock: bool):
    if mock:
        from mock.adapters import MockImageGenAdapter, MockLLMAdapter, MockTTSAdapter
        return MockLLMAdapter(), MockImageGenAdapter(), MockTTSAdapter()

    from src.adapters.image_gen import DalleAdapter
    from src.adapters.llm import ClaudeAdapter

    tts_provider = config.get("tts", {}).get("provider", "openai")
    if tts_provider == "voicevox":
        from src.adapters.tts_voicevox import VoicevoxAdapter
        tts = VoicevoxAdapter(config["tts"])
    else:
        from src.adapters.tts import OpenAITTSAdapter
        tts = OpenAITTSAdapter(config["tts"])

    return (
        ClaudeAdapter(config["llm"]),
        DalleAdapter(config["image_gen"]),
        tts,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a short narrated video from a topic.")
    parser.add_argument(
        "--topic", default=DEFAULT_TOPIC,
        help=f'Topic for the video (default: "{DEFAULT_TOPIC}")',
    )
    parser.add_argument(
        "--genre", default=DEFAULT_GENRE, choices=GENRES,
        help=f"Visual style genre (default: {DEFAULT_GENRE}). Choices: {', '.join(GENRES)}",
    )
    parser.add_argument(
        "--mode", default="static", choices=["static", "video"],
        help="static: image+KenBurns (default), video: AI video generation",
    )
    parser.add_argument(
        "--video-provider", default="kling", choices=["kling"],
        dest="video_provider",
        help="Video generation provider when --mode video (default: kling)",
    )
    parser.add_argument(
        "--topic-from", default="manual", choices=["manual", "llm"],
        dest="topic_from",
        help="Topic source: 'manual' (use --topic) or 'llm' (Claude suggests topics)",
    )
    parser.add_argument(
        "--interactive", action="store_true",
        help="When --topic-from llm: show suggestions and let you pick (default: auto-select)",
    )
    parser.add_argument(
        "--lang", default=DEFAULT_LANG, choices=LANGS,
        help=f"Narration language: en (English) or ja (Japanese). Default: {DEFAULT_LANG}",
    )
    parser.add_argument(
        "--tts", default=None, choices=["openai", "voicevox"],
        help="TTS provider override: openai or voicevox (default: use config.json)",
    )
    parser.add_argument(
        "--tts-speaker", default=None, type=int,
        dest="tts_speaker",
        help="Voicevox speaker ID (default: 1)",
    )
    parser.add_argument(
        "--ab-variants", default=1, type=int, dest="ab_variants", metavar="N",
        help="Generate N storyboard variants and pick the best scoring one (default: 1 = off)",
    )
    parser.add_argument(
        "--bgm", default=None, metavar="FILE",
        help="Path to a local audio file to use as background music",
    )
    parser.add_argument(
        "--bgm-ai", action="store_true", dest="bgm_ai",
        help="Generate background music via Mubert AI (requires MUBERT_API_KEY)",
    )
    parser.add_argument(
        "--bgm-volume", default=0.2, type=float, dest="bgm_volume",
        help="BGM volume relative to narration (default: 0.2 = 20%%)",
    )
    parser.add_argument(
        "--no-subtitle", action="store_true", dest="no_subtitle",
        help="Disable subtitle overlay on video",
    )
    parser.add_argument(
        "--batch", default=None, metavar="YAML",
        help="Run batch mode from a YAML file (e.g. topics.yaml)",
    )
    parser.add_argument(
        "--batch-genre", default=None, nargs="+", dest="batch_genre",
        metavar="GENRE",
        help="Auto-batch: one or more genres (e.g. --batch-genre romance mens_life academia)",
    )
    parser.add_argument(
        "--batch-count", default=5, type=int, dest="batch_count",
        help="Number of videos per genre in auto-batch mode (default: 5)",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Run in mock mode — no API calls, no cost",
    )
    parser.add_argument(
        "--config", default=str(CONFIG_PATH),
        help="Path to config.json",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    if args.tts:
        config["tts"]["provider"] = args.tts
    if args.tts_speaker is not None:
        config["tts"]["speaker"] = args.tts_speaker

    # ── Batch mode ────────────────────────────────────────────────────────────
    if args.batch or args.batch_genre:
        from src.batch import jobs_from_genre, load_jobs_from_yaml, print_summary, run_batch

        if args.batch:
            jobs = load_jobs_from_yaml(Path(args.batch))
            print(f"\n{'='*60}")
            print(f"  AI Narrator — Batch Mode (YAML)")
            print(f"  File  : {args.batch}")
            print(f"  Jobs  : {len(jobs)}")
            print(f"  Mode  : {'MOCK' if args.mock else 'LIVE'}")
            print(f"{'='*60}\n")
        else:
            invalid = [g for g in args.batch_genre if g not in GENRES]
            if invalid:
                print(f"Error: unknown genre(s): {', '.join(invalid)}")
                print(f"Valid genres: {', '.join(GENRES)}")
                return 1

            jobs = []
            for genre in args.batch_genre:
                jobs += jobs_from_genre(
                    genre=genre,
                    lang=args.lang,
                    count=args.batch_count,
                    model=config["llm"]["model"],
                )

            genres_str = ", ".join(args.batch_genre)
            total = len(args.batch_genre) * args.batch_count
            print(f"\n{'='*60}")
            print(f"  AI Narrator — Batch Mode (Auto)")
            print(f"  Genres: {genres_str}")
            print(f"  Lang  : {args.lang}  {args.batch_count} videos/genre  Total: {total}")
            print(f"  Mode  : {'MOCK' if args.mock else 'LIVE'}")
            print(f"{'='*60}\n")
            for i, j in enumerate(jobs, 1):
                print(f"  {i:2}. [{j.genre}] {j.topic}")
            print()

        results = run_batch(jobs, config, mock=args.mock)
        print_summary(results)
        return 0 if all(r.success for r in results) else 1

    llm, img, tts = build_adapters(config, args.mock)

    # Resolve topic
    topic = args.topic
    if args.topic_from == "llm":
        if args.mock:
            logging.warning("--topic-from llm ignored in mock mode; using default topic")
        else:
            from src.topic_selector import LLMTopicSelector
            selector = LLMTopicSelector(model=config["llm"]["model"])
            topic = selector.select(
                genre=args.genre,
                lang=args.lang,
                interactive=args.interactive,
            )

    print(f"\n{'='*60}")
    print(f"  AI Narrator")
    print(f"  Topic : {topic}")
    print(f"  Genre : {args.genre}")
    print(f"  Lang  : {args.lang}")
    print(f"  Mode  : {'MOCK (no API calls)' if args.mock else 'LIVE'}")
    print(f"  Video : {args.mode}{' (' + args.video_provider + ')' if args.mode == 'video' else ' (static image)'}")
    print(f"{'='*60}\n")

    from src.pipeline import run

    video_gen = None
    if args.mode == "video" and not args.mock:
        if not os.environ.get("KLING_API_KEY"):
            logging.error("KLING_API_KEY is not set. Add it to .env or use --mode static.")
            return 1
        from src.adapters.video_gen import KlingAdapter
        video_gen = KlingAdapter(config.get("video_gen", {}))

    bgm = None
    if not args.mock:
        if args.bgm:
            from src.adapters.bgm import LocalBGMAdapter
            bgm = LocalBGMAdapter(args.bgm)
        elif args.bgm_ai:
            from src.adapters.bgm import MubertBGMAdapter
            bgm = MubertBGMAdapter(config.get("bgm", {}))

    try:
        video_path, report = run(
            topic=topic,
            llm_adapter=llm,
            image_adapter=img,
            tts_adapter=tts,
            config=config,
            mock=args.mock,
            genre=args.genre,
            lang=args.lang,
            mode=args.mode,
            video_gen_adapter=video_gen,
            subtitle=not args.no_subtitle,
            bgm_adapter=bgm,
            bgm_volume=args.bgm_volume,
            ab_variants=args.ab_variants,
        )
    except Exception as e:
        logging.error("Pipeline failed: %s", e, exc_info=True)
        return 1

    print(f"\n{'='*60}")
    print(f"  Video  : {video_path}")
    print(f"  Report : {Path(report.output_storyboard).parent / 'report.json'}")
    print(f"  Duration: {report.video_duration_seconds:.1f}s")
    if not args.mock:
        print(f"  Est. cost: ${report.total_cost_usd:.4f}")
    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
