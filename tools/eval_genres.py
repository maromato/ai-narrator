#!/usr/bin/env python3
"""
Genre evaluation tool.

Generates N storyboards per genre using Claude, evaluates each with the
StoryboardEvaluator, and outputs a ranked report to help choose top genres.

Usage:
  .venv/bin/python tools/eval_genres.py                        # all genres, 3 each
  .venv/bin/python tools/eval_genres.py --count 5              # 5 storyboards per genre
  .venv/bin/python tools/eval_genres.py --genres history science academia
  .venv/bin/python tools/eval_genres.py --lang ja
  .venv/bin/python tools/eval_genres.py --out results.json     # save full results
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

ALL_GENRES = [
    "history", "science", "animals", "religion",
    "lifestyle", "selfhelp", "workplace",
    "japan_travel", "japan_zen",
    "romance", "mens_life",
    "academia", "elite_edu",
    "finance", "finance2", "psychology",
    "beauty",
    "drama_kdrama",
    "drama_romance",
    "drama_bl",
    "drama_korean_bl",
    "kdrama_intro",
    "bl_intro",
    "general",
]


def generate_storyboard(topic: str, genre: str, lang: str, config: dict) -> dict:
    from src.adapters.llm import ClaudeAdapter
    adapter = ClaudeAdapter(config["llm"])
    sb = adapter.generate_storyboard(topic, genre=genre, lang=lang)
    return sb.to_dict()


def suggest_topics(genre: str, lang: str, count: int, model: str, use_trends: bool = False) -> list[str]:
    from src.topic_selector import LLMTopicSelector
    selector = LLMTopicSelector(model=model)
    return selector.suggest(genre=genre, lang=lang, count=count, use_trends=use_trends)


def run_evaluation(genres: list[str], count: int, lang: str, config: dict, use_trends: bool = False) -> list[dict]:
    from src.evaluator import StoryboardEvaluator
    evaluator = StoryboardEvaluator(model=config["llm"]["model"])

    all_results = []
    total = len(genres) * count
    done = 0

    for genre in genres:
        logger.info("━" * 50)
        logger.info("Genre: %s — generating %d topics...", genre, count)

        try:
            topics = suggest_topics(genre, lang, count, config["llm"]["model"], use_trends=use_trends)
        except Exception as e:
            logger.error("Topic suggestion failed for %s: %s", genre, e)
            continue

        for topic in topics:
            done += 1
            logger.info("[%d/%d] %s | %s", done, total, genre, topic[:60])
            try:
                sb = generate_storyboard(topic, genre, lang, config)
                scores = evaluator.evaluate(sb, genre)
                scores["lang"] = lang
                all_results.append(scores)
                logger.info("  → final_score=%.2f | %s", scores["final_score"], scores["verdict"])
            except Exception as e:
                logger.error("  ✗ Failed: %s", e)

    return all_results


def aggregate_by_genre(results: list[dict]) -> list[dict]:
    from collections import defaultdict
    genre_data: dict[str, list] = defaultdict(list)
    for r in results:
        genre_data[r["genre"]].append(r)

    summary = []
    for genre, scores in genre_data.items():
        finals = [s["final_score"] for s in scores]
        contents = [s["content_score"] for s in scores]
        best = max(scores, key=lambda x: x["final_score"])
        summary.append({
            "genre":          genre,
            "avg_final":      round(sum(finals) / len(finals), 2),
            "avg_content":    round(sum(contents) / len(contents), 2),
            "rpm_factor":     scores[0]["rpm_factor"],
            "n":              len(scores),
            "best_topic":     best["topic"],
            "best_score":     best["final_score"],
            "best_verdict":   best["verdict"],
            "scores":         scores,
        })

    return sorted(summary, key=lambda x: x["avg_final"], reverse=True)


def print_report(summary: list[dict], top_n: int = 4) -> None:
    print(f"\n{'='*70}")
    print(f"  GENRE EVALUATION REPORT")
    print(f"{'='*70}\n")

    print(f"  {'#':<3} {'Genre':<14} {'Avg Score':<11} {'Content':<10} {'RPM×':<7} {'Best Topic'}")
    print(f"  {'─'*3} {'─'*14} {'─'*11} {'─'*10} {'─'*7} {'─'*30}")

    for i, g in enumerate(summary, 1):
        marker = "◎" if i <= top_n else " "
        topic_short = g["best_topic"][:40] + ("…" if len(g["best_topic"]) > 40 else "")
        print(f"  {marker}{i:<3} {g['genre']:<14} {g['avg_final']:<11.2f} {g['avg_content']:<10.2f} {g['rpm_factor']:<7.2f} {topic_short}")

    print(f"\n{'─'*70}")
    print(f"  TOP {top_n} RECOMMENDED GENRES:\n")
    for i, g in enumerate(summary[:top_n], 1):
        print(f"  {i}. [{g['genre']}]  avg={g['avg_final']:.2f}")
        print(f"     Best: \"{g['best_topic'][:65]}\"")
        print(f"     → {g['best_verdict']}\n")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Evaluate all genres and rank by TikTok potential.")
    parser.add_argument("--genres", nargs="+", default=ALL_GENRES, metavar="GENRE",
                        help="Genres to evaluate (default: all)")
    parser.add_argument("--count", default=3, type=int,
                        help="Storyboards per genre (default: 3)")
    parser.add_argument("--lang", default="en", choices=["en", "ja"],
                        help="Language (default: en)")
    parser.add_argument("--top", default=4, type=int,
                        help="Number of top genres to highlight (default: 4)")
    parser.add_argument("--out", default=None, metavar="FILE",
                        help="Save full results to JSON file")
    parser.add_argument("--config", default="config.json",
                        help="Path to config.json")
    parser.add_argument("--trends", action="store_true",
                        help="Seed topic suggestions with Google News trends")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text())

    print(f"\n{'='*70}")
    print(f"  AI Narrator — Genre Evaluation")
    print(f"  Genres : {len(args.genres)}  ×  {args.count} storyboards  =  {len(args.genres) * args.count} total")
    print(f"  Lang   : {args.lang}")
    print(f"  Trends : {'ON (Google News)' if args.trends else 'OFF'}")
    print(f"{'='*70}\n")

    results = run_evaluation(args.genres, args.count, args.lang, config, use_trends=args.trends)

    if not results:
        print("No results collected.")
        return 1

    summary = aggregate_by_genre(results)
    print_report(summary, top_n=args.top)

    if args.out:
        Path(args.out).write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False))
        print(f"Full results saved → {args.out}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
