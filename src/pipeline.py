"""
Pipeline orchestration.

Steps:
  1. Generate storyboard (LLM)
  2. Generate images (image_gen adapter)
  3. Generate per-scene narration audio (TTS adapter)
  4. Render scene clips (FFmpeg)
  5. Concatenate clips → final.mp4
  6. Save run report
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from src import video as vid
from src.report import RunReport
from src.storyboard import Storyboard

logger = logging.getLogger(__name__)


def run(
    topic: str,
    llm_adapter,
    image_adapter,
    tts_adapter,
    config: dict,
    mock: bool = False,
    genre: str = "general",
    lang: str = "en",
    mode: str = "static",
    video_gen_adapter=None,
    subtitle: bool = True,
    bgm_adapter=None,
    bgm_volume: float = 0.2,
    ab_variants: int = 1,
) -> tuple[Path, RunReport]:
    vid.check_ffmpeg()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(config["pipeline"]["output_dir"]) / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    report = RunReport(run_id=run_id, topic=topic, mock_mode=mock)
    logger.info("Run ID: %s | Topic: %s | Genre: %s | Lang: %s | Mock: %s", run_id, topic, genre, lang, mock)

    # ── Step 1: Storyboard (with optional A/B test) ───────────────────────────
    if ab_variants > 1 and not mock:
        logger.info("[1/5] Generating %d storyboard variants (A/B test)...", ab_variants)
        from src.evaluator import StoryboardEvaluator
        evaluator = StoryboardEvaluator()
        candidates: list[Storyboard] = []
        ab_scores: list[dict] = []
        for i in range(ab_variants):
            logger.info("  Variant %d/%d...", i + 1, ab_variants)
            sb = llm_adapter.generate_storyboard(topic, genre, lang)
            score = evaluator.evaluate(sb.to_dict(), genre)
            candidates.append(sb)
            ab_scores.append(score)
            logger.info("  → score=%.2f | %s", score["final_score"], score["verdict"])

        best_idx = max(range(len(ab_scores)), key=lambda i: ab_scores[i]["final_score"])
        storyboard = candidates[best_idx]
        logger.info("Selected variant %d (score=%.2f): %s",
                    best_idx + 1, ab_scores[best_idx]["final_score"], storyboard.topic)

        # Save A/B comparison report
        ab_report = [
            {
                "variant": i + 1,
                "topic": s["topic"],
                "final_score": s["final_score"],
                "content_score": s["content_score"],
                "verdict": s["verdict"],
                "selected": i == best_idx,
            }
            for i, s in enumerate(ab_scores)
        ]
        (out_dir / "ab_results.json").write_text(
            json.dumps(ab_report, indent=2, ensure_ascii=False)
        )
    else:
        logger.info("[1/5] Generating storyboard...")
        storyboard: Storyboard = llm_adapter.generate_storyboard(topic, genre, lang)

    storyboard.save(out_dir / "storyboard.json")
    (out_dir / "script.txt").write_text(storyboard.script)
    report.output_storyboard = str(out_dir / "storyboard.json")
    report.llm_usage = llm_adapter.usage
    report.tone = storyboard.tone
    report.target_audience = storyboard.target_audience
    report.hashtags = storyboard.hashtags
    report.genre = genre
    report.lang = lang
    logger.info("Storyboard saved with %d scenes", len(storyboard.scenes))

    if mode == "video":
        # ── Video mode: Kling generates clips directly ─────────────────────
        logger.info("[2/5] Generating TTS audio (needed first for duration)...")
        audio_paths: list[Path] = []
        for scene in storyboard.scenes:
            ext = "wav" if mock else getattr(tts_adapter, "file_ext", "mp3")
            audio_path = out_dir / f"narration_{scene.scene_id}.{ext}"
            tts_adapter.synthesize(scene.narration, audio_path)
            audio_paths.append(audio_path)
        report.tts_usage = tts_adapter.usage

        logger.info("[3/5] Generating video clips (Kling)...")
        raw_video_paths: list[Path] = []
        for scene, audio_path in zip(storyboard.scenes, audio_paths):
            duration = vid.get_audio_duration(audio_path)
            raw_path = out_dir / f"raw_{scene.scene_id}.mp4"
            video_gen_adapter.generate_video(
                prompt=scene.image_prompt,
                output_path=raw_path,
                duration=int(duration) + 1,
            )
            raw_video_paths.append(raw_path)
        report.image_gen_usage = video_gen_adapter.usage

        logger.info("[4/5] Muxing video + audio + subtitles...")
        clip_paths: list[Path] = []
        for scene, raw_path, audio_path in zip(storyboard.scenes, raw_video_paths, audio_paths):
            clip_path = out_dir / f"clip_{scene.scene_id}.mp4"
            vid.mux_video_audio(raw_path, audio_path, clip_path, config["video"], subtitle=scene.subtitle if subtitle else "")
            clip_paths.append(clip_path)

    else:
        # ── Static mode: image + Ken Burns (default) ───────────────────────
        logger.info("[2/5] Generating images...")
        image_paths: list[Path] = []
        for scene in storyboard.scenes:
            img_path = out_dir / f"scene_{scene.scene_id}.png"
            image_adapter.generate_image(scene.image_prompt, img_path)
            image_paths.append(img_path)
        report.image_gen_usage = image_adapter.usage

        logger.info("[3/5] Generating narration audio...")
        audio_paths: list[Path] = []
        for scene in storyboard.scenes:
            ext = "wav" if mock else getattr(tts_adapter, "file_ext", "mp3")
            audio_path = out_dir / f"narration_{scene.scene_id}.{ext}"
            tts_adapter.synthesize(scene.narration, audio_path)
            audio_paths.append(audio_path)
        report.tts_usage = tts_adapter.usage

        logger.info("[4/5] Rendering scene clips...")
        clip_paths: list[Path] = []
        for scene, img_path, audio_path in zip(storyboard.scenes, image_paths, audio_paths):
            clip_path = out_dir / f"clip_{scene.scene_id}.mp4"
            vid.build_scene_clip(
                image_path=img_path,
                audio_path=audio_path,
                output_path=clip_path,
                subtitle=scene.subtitle if subtitle else "",
                camera_effect=scene.camera_effect,
                config=config["video"],
            )
            clip_paths.append(clip_path)

    # ── Step 5: Concatenate ───────────────────────────────────────────────────
    logger.info("[5/5] Concatenating clips...")
    concat_path = out_dir / ("final_no_bgm.mp4" if bgm_adapter else "final.mp4")
    vid.concatenate_clips(clip_paths, concat_path)

    total_duration = sum(vid.get_audio_duration(a) for a in audio_paths)

    # ── Step 6: BGM (optional) ────────────────────────────────────────────────
    final_path = out_dir / "final.mp4"
    if bgm_adapter:
        logger.info("[6/6] Adding BGM...")
        bgm_path = out_dir / "bgm.mp3"
        bgm_adapter.get_bgm(total_duration, genre, bgm_path)
        vid.add_bgm(concat_path, bgm_path, final_path, volume=bgm_volume)
    else:
        final_path = concat_path

    report.output_video = str(final_path)
    report.video_duration_seconds = total_duration
    report.finish()

    report.save(out_dir / "report.json")
    logger.info("Done. Video: %s (%.1fs)", final_path, total_duration)
    return final_path, report
