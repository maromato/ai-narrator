"""
FFmpeg video assembly.

Per scene:
  - Burn subtitle text onto image copy using PIL (no libfreetype dependency)
  - Scale input image to 1296×2304 (1.2× headroom for Ken Burns)
  - Apply zoompan effect (Ken Burns) → 1080×1920
  - Mux with scene audio

Final: concatenate all scene clips → output.mp4
"""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe must be installed and in PATH")


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(audio_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace(":", "\\:")
            .replace("%", "\\%")
    )


def _zoompan_expr(effect: str, frames: int, zoom_max: float = 1.2) -> str:
    delta = round((zoom_max - 1.0) / frames, 6)
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    pan_range = f"(iw-iw/zoom)"

    if effect == "zoom_in":
        z = f"min(zoom+{delta},{zoom_max})"
        return f"z='{z}':x='{cx}':y='{cy}'"
    elif effect == "zoom_out":
        z = f"if(eq(on,1),{zoom_max},max(zoom-{delta},1.0))"
        return f"z='{z}':x='{cx}':y='{cy}'"
    elif effect == "pan_right":
        return f"z='{zoom_max}':x='{pan_range}*on/{frames}':y='{cy}'"
    else:  # pan_left
        return f"z='{zoom_max}':x='{pan_range}*(1-on/{frames})':y='{cy}'"


def _burn_subtitle(image_path: Path, subtitle: str, output_path: Path) -> Path:
    """Burn subtitle text onto image using PIL (no libfreetype/drawtext needed)."""
    with Image.open(image_path).convert("RGB") as img:
        w, h = img.size
        draw = ImageDraw.Draw(img)

        font_paths = [
            "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
            "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        font_path_found = None
        for fp in font_paths:
            try:
                ImageFont.truetype(fp, 10)
                font_path_found = fp
                break
            except Exception:
                pass

        # Only uppercase for ASCII text (skip for Japanese)
        if all(ord(c) < 128 for c in subtitle):
            subtitle = subtitle.upper()

        # Auto-shrink font to fit within 90% of image width
        max_text_width = int(w * 0.90)
        font_size = max(36, h // 26)
        font = ImageFont.load_default()
        while font_size >= 28:
            if font_path_found:
                try:
                    font = ImageFont.truetype(font_path_found, font_size)
                except Exception:
                    pass
            bbox = draw.textbbox((0, 0), subtitle, font=font)
            tw = bbox[2] - bbox[0]
            if tw <= max_text_width:
                break
            font_size -= 4

        bbox = draw.textbbox((0, 0), subtitle, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (w - tw) // 2
        y = int(h * 0.80)
        padding = 18

        # Semi-transparent background box
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        box_draw = ImageDraw.Draw(overlay)
        box_draw.rectangle(
            [x - padding, y - padding, x + tw + padding, y + th + padding],
            fill=(0, 0, 0, 160),
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Outline + text for TikTok-style pop
        for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
            draw.text((x + ox, y + oy), subtitle, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), subtitle, font=font, fill=(255, 255, 255, 255))

        img.save(str(output_path))
    return output_path


def build_scene_clip(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    subtitle: str,
    camera_effect: str,
    config: dict,
) -> Path:
    """Render a single scene: image + subtitle (PIL) + Ken Burns + audio → MP4."""
    w, h, fps = config["width"], config["height"], config["fps"]
    zoom_max = config.get("zoom_max", 1.2)

    duration = get_audio_duration(audio_path)
    frames = max(int(duration * fps), 1)

    zp = _zoompan_expr(camera_effect, frames, zoom_max)
    scale_w = int(w * zoom_max)
    scale_h = int(h * zoom_max)

    # Burn subtitle into a temp image copy
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_image = Path(tmp.name)
    _burn_subtitle(image_path, subtitle, tmp_image)

    video_filter = (
        f"[0:v]scale={scale_w}:{scale_h}:force_original_aspect_ratio=increase,"
        f"crop={scale_w}:{scale_h},"
        f"zoompan={zp}:d={frames}:s={w}x{h}:fps={fps}[vout]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(tmp_image),
        "-i", str(audio_path),
        "-filter_complex", video_filter,
        "-map", "[vout]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast",
        "-crf", str(config.get("crf", 18)),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        str(output_path),
    ]

    logger.info("Rendering scene clip: %s (%.1fs)", output_path.name, duration)
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        tmp_image.unlink(missing_ok=True)
    return output_path


def _create_subtitle_overlay(subtitle: str, w: int, h: int, output_path: Path) -> Path:
    """Create a transparent PNG with subtitle text for overlay onto video."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_paths = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    font_path_found = None
    for fp in font_paths:
        try:
            ImageFont.truetype(fp, 10)
            font_path_found = fp
            break
        except Exception:
            pass

    if all(ord(c) < 128 for c in subtitle):
        subtitle = subtitle.upper()

    max_text_width = int(w * 0.90)
    font_size = max(36, h // 26)
    font = ImageFont.load_default()
    while font_size >= 28:
        if font_path_found:
            try:
                font = ImageFont.truetype(font_path_found, font_size)
            except Exception:
                pass
        bbox = draw.textbbox((0, 0), subtitle, font=font)
        if bbox[2] - bbox[0] <= max_text_width:
            break
        font_size -= 4

    bbox = draw.textbbox((0, 0), subtitle, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (w - tw) // 2
    y = int(h * 0.80)
    padding = 18

    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    box_draw = ImageDraw.Draw(box)
    box_draw.rectangle(
        [x - padding, y - padding, x + tw + padding, y + th + padding],
        fill=(0, 0, 0, 160),
    )
    img = Image.alpha_composite(img, box)
    draw = ImageDraw.Draw(img)

    for ox, oy in [(-3, -3), (3, -3), (-3, 3), (3, 3)]:
        draw.text((x + ox, y + oy), subtitle, font=font, fill=(0, 0, 0, 255))
    draw.text((x, y), subtitle, font=font, fill=(255, 255, 255, 255))

    img.save(str(output_path))
    return output_path


def mux_video_audio(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    config: dict,
    subtitle: str = "",
) -> Path:
    """Mux a Kling-generated video with TTS audio → scene clip MP4."""
    duration = get_audio_duration(audio_path)
    w, h = config["width"], config["height"]

    if subtitle:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            overlay_path = Path(tmp.name)
        _create_subtitle_overlay(subtitle, w, h, overlay_path)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-i", str(overlay_path),
            "-filter_complex",
            f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[base];"
            f"[base][2:v]overlay=0:0[vout]",
            "-map", "[vout]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast",
            "-crf", str(config.get("crf", 18)),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            str(output_path),
        ]
        logger.info("Muxing video+audio+subtitle: %s (%.1fs)", output_path.name, duration)
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        finally:
            overlay_path.unlink(missing_ok=True)
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", "fast",
            "-crf", str(config.get("crf", 18)),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-t", str(duration),
            str(output_path),
        ]
        logger.info("Muxing video+audio: %s (%.1fs)", output_path.name, duration)
        subprocess.run(cmd, check=True, capture_output=True)

    return output_path


def concatenate_clips(clip_paths: list[Path], output_path: Path) -> Path:
    """Concatenate scene clips into the final video."""
    concat_list = output_path.parent / "concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths)
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path),
    ]

    logger.info("Concatenating %d clips → %s", len(clip_paths), output_path.name)
    subprocess.run(cmd, check=True, capture_output=True)
    concat_list.unlink(missing_ok=True)
    return output_path


def check_ffmpeg() -> None:
    _require_ffmpeg()
