"""
Batch runner — generate multiple videos from a YAML file or auto-generated topics.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from src.pipeline import run as run_pipeline
from src.report import RunReport
from src.topic_selector import LLMTopicSelector

logger = logging.getLogger(__name__)


@dataclass
class BatchJob:
    genre: str = "general"
    lang: str = "en"
    topic: str = ""
    topic_from: str = "manual"
    mode: str = "static"
    subtitle: bool = True
    tts: str = ""
    ab_variants: int = 1
    tts_speaker: int = 1


@dataclass
class BatchResult:
    job: BatchJob
    success: bool
    video_path: str = ""
    cost_usd: float = 0.0
    error: str = ""


def load_jobs_from_yaml(path: Path) -> list[BatchJob]:
    data = yaml.safe_load(path.read_text())
    jobs = []
    for item in data:
        jobs.append(BatchJob(
            topic=item.get("topic", ""),
            topic_from=item.get("topic_from", "llm" if not item.get("topic") else "manual"),
            genre=item.get("genre", "general"),
            lang=item.get("lang", "en"),
            mode=item.get("mode", "static"),
            subtitle=item.get("subtitle", True),
            tts=item.get("tts", ""),
            tts_speaker=item.get("tts_speaker", 1),
            ab_variants=item.get("ab_variants", 1),
        ))
    return jobs


def jobs_from_genre(genre: str, lang: str, count: int, model: str) -> list[BatchJob]:
    """Auto-generate jobs using LLM topic suggestions."""
    selector = LLMTopicSelector(model=model)
    topics = selector.suggest(genre=genre, lang=lang, count=count)
    return [BatchJob(topic=t, genre=genre, lang=lang) for t in topics]


def run_batch(
    jobs: list[BatchJob],
    config: dict,
    mock: bool = False,
) -> list[BatchResult]:
    from run import build_adapters

    results: list[BatchResult] = []

    for i, job in enumerate(jobs, 1):
        logger.info("─" * 50)
        logger.info("Batch job %d/%d | topic=%s | genre=%s | lang=%s", i, len(jobs), job.topic, job.genre, job.lang)

        # Apply job-level TTS override
        job_config = dict(config)
        if job.tts:
            job_config["tts"] = dict(config["tts"])
            job_config["tts"]["provider"] = job.tts
            if job.tts == "voicevox":
                job_config["tts"]["speaker"] = job.tts_speaker

        try:
            # Resolve topic (LLM or manual)
            if not job.topic:
                if mock:
                    job.topic = "Mock topic"
                else:
                    selector = LLMTopicSelector(model=config["llm"]["model"])
                    job.topic = selector.select(genre=job.genre, lang=job.lang)
                logger.info("Topic resolved: %s", job.topic)

            llm, img, tts = build_adapters(job_config, mock)

            video_gen = None
            if job.mode == "video" and not mock:
                from src.adapters.video_gen import KlingAdapter
                video_gen = KlingAdapter(job_config.get("video_gen", {}))

            video_path, report = run_pipeline(
                topic=job.topic,
                llm_adapter=llm,
                image_adapter=img,
                tts_adapter=tts,
                config=job_config,
                mock=mock,
                genre=job.genre,
                lang=job.lang,
                mode=job.mode,
                video_gen_adapter=video_gen,
                subtitle=job.subtitle,
                ab_variants=job.ab_variants,
            )
            results.append(BatchResult(
                job=job,
                success=True,
                video_path=str(video_path),
                cost_usd=report.total_cost_usd,
            ))
            logger.info("✓ Done: %s (cost: $%.4f)", video_path.name, report.total_cost_usd)

        except Exception as e:
            logger.error("✗ Failed: %s", e, exc_info=True)
            results.append(BatchResult(job=job, success=False, error=str(e)))

    return results


def print_summary(results: list[BatchResult]) -> None:
    success = [r for r in results if r.success]
    failed  = [r for r in results if not r.success]
    total_cost = sum(r.cost_usd for r in success)

    print(f"\n{'='*60}")
    print(f"  Batch Summary")
    print(f"  Success : {len(success)}/{len(results)}")
    print(f"  Failed  : {len(failed)}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"{'='*60}")

    for r in success:
        print(f"  ✓ {r.job.topic[:40]:<40} → {Path(r.video_path).parent.name}")
    for r in failed:
        print(f"  ✗ {r.job.topic[:40]:<40}   ERROR: {r.error[:50]}")
    print()
