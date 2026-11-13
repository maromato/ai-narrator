#!/usr/bin/env python3
"""
TikTok Marketing Strategist — AI-powered advisor for AI Narrator content strategy.

Usage:
  .venv/bin/python tools/marketer.py                              # interactive Q&A
  .venv/bin/python tools/marketer.py --data results.json         # analyze eval data
  .venv/bin/python tools/marketer.py --ask "新アカウントを作るべきか"
  .venv/bin/python tools/marketer.py --plan                       # content calendar
  .venv/bin/python tools/marketer.py --plan --genres finance2 academia --weekly 14
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import anthropic

_SYSTEM = """\
You are an elite TikTok growth strategist and monetization expert specializing in \
AI-generated short-form content.

Your expertise:
- TikTok algorithm: completion rate, shares, saves, ForYou page mechanics, \
  new-account honeymoon boost
- Account growth: niche accounts vs general, shadow limiting, audience-genre matching
- Monetization: TikTok Creativity Program (requires 10K followers + 100K views/90 days), \
  Series (paid content, 10K followers), brand deals, cross-platform funnels
- Japanese and international TikTok market dynamics
- AI content: disclosure requirements, what makes AI video feel authentic vs robotic \
  (biggest drop-off cause: uncanny images + flat TTS voice)
- Content calendar optimization and posting cadence (consistency > quantity)
- RPM maximization by genre selection

About the AI Narrator system (the tool this user is running):
- Auto-generates 30-second portrait TikTok videos from a topic + genre using Claude + image AI + TTS
- 24 genres: education/info (history, science, finance, psychology, academia, elite_edu, \
  finance2, beauty, romance, mens_life, lifestyle, selfhelp, workplace, japan_travel, \
  japan_zen, animals, religion, general), \
  intro/review (kdrama_intro, bl_intro), \
  mini drama/creative (drama_kdrama, drama_romance, drama_bl, drama_korean_bl)
- RPM factors (content_score × factor = final_score):
    finance2=1.40, academia/elite_edu=1.35, finance=1.30, psychology=1.25,
    history/science=1.15, workplace/drama_kdrama/drama_korean_bl/kdrama_intro=1.10,
    beauty/selfhelp/drama_romance/drama_bl/bl_intro=1.05,
    japan_travel/japan_zen/general=1.00, mens_life=0.95,
    lifestyle/romance/animals=0.90, religion=0.85
- Supports Japanese (ja) and English (en)
- Batch mode: auto-generates multiple videos in one run with LLM topic selection
- --trends flag: seeds topics from Google News RSS (no API key required)
- --ab-variants N: generates N storyboard variants and picks the best-scoring one

When giving advice:
- Be specific and actionable — no vague platitudes
- Prioritize by impact × effort
- Be honest about what won't work (generic AI content without a hook gets 0 views)
- If eval data is provided, base recommendations on actual scores
- Answer in the same language the user writes in (Japanese or English)
"""


def format_eval_summary(data: dict) -> str:
    summary = data.get("summary", [])
    if not summary:
        return ""
    lines = ["## Eval Results (ranked by final_score)\n"]
    for i, g in enumerate(summary, 1):
        lines.append(
            f"{i}. [{g['genre']}] avg_final={g['avg_final']:.2f} "
            f"(content={g['avg_content']:.2f} × rpm{g['rpm_factor']:.2f}, n={g['n']})\n"
            f"   Best topic: \"{g['best_topic'][:70]}\"\n"
            f"   Verdict: {g['best_verdict']}\n"
        )
    return "\n".join(lines)


def chat(client: anthropic.Anthropic, messages: list[dict], question: str, context: str = "") -> str:
    content = f"{context}\n\n---\n\n{question}" if (context and not messages) else question
    messages.append({"role": "user", "content": content})
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=_SYSTEM,
        messages=messages,
    )
    answer = response.content[0].text
    messages.append({"role": "assistant", "content": answer})
    return answer


def main() -> int:
    parser = argparse.ArgumentParser(description="TikTok Marketing Strategist for AI Narrator")
    parser.add_argument("--data", metavar="FILE",
                        help="Eval results JSON from eval_genres.py --out for data-driven analysis")
    parser.add_argument("--ask", metavar="QUESTION",
                        help="One-shot question (non-interactive)")
    parser.add_argument("--plan", action="store_true",
                        help="Generate a content strategy and weekly calendar")
    parser.add_argument("--genres", nargs="+", metavar="GENRE",
                        help="Focus genres for --plan")
    parser.add_argument("--weekly", type=int, default=14, metavar="N",
                        help="Target videos per week for --plan (default: 14)")
    args = parser.parse_args()

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    messages: list[dict] = []

    # Load eval data if provided
    context = ""
    if args.data:
        try:
            data = json.loads(Path(args.data).read_text())
            context = format_eval_summary(data)
            print(f"Loaded eval data: {len(data.get('summary', []))} genres\n")
        except Exception as e:
            print(f"Warning: could not load {args.data}: {e}\n")

    # -- Plan mode --
    if args.plan:
        genres_note = (
            f"Focus on these genres: {', '.join(args.genres)}."
            if args.genres
            else "Recommend the best genres based on eval data or RPM factors."
        )
        question = (
            f"Generate a detailed TikTok content strategy and weekly content calendar.\n"
            f"Weekly video target: {args.weekly} videos/week.\n"
            f"{genres_note}\n\n"
            f"Include:\n"
            f"1. Which genres to prioritize and why (with RPM reasoning)\n"
            f"2. Posting schedule (days/times, cadence)\n"
            f"3. Account growth milestones and timeline to Creativity Program\n"
            f"4. Specific tips to make AI-generated content feel authentic on TikTok\n"
            f"5. Quick wins for the first 30 days\n"
        )
        print("Generating content strategy...\n")
        answer = chat(client, messages, question, context)
        print(answer)
        return 0

    # -- One-shot mode --
    if args.ask:
        answer = chat(client, messages, args.ask, context)
        print(answer)
        return 0

    # -- Interactive mode --
    print("=" * 60)
    print("  AI Narrator — TikTok Marketing Strategist")
    print("  質問を入力してください。終了: exit")
    if context:
        print("  Eval data: loaded")
    print("=" * 60 + "\n")

    first = True
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if q.lower() in ("exit", "quit", "q"):
            break
        if not q:
            continue
        answer = chat(client, messages, q, context if first else "")
        first = False
        print(f"\nStrategist:\n{answer}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
