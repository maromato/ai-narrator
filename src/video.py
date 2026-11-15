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


_FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W9.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

_OUTLINE_OFFSETS = [
    (-5, 0), (5, 0), (0, -5), (0, 5),
    (-4, -4), (4, -4), (-4, 4), (4, 4),
]


def _find_font() -> str | None:
    for fp in _FONT_PATHS:
        try:
            ImageFont.truetype(fp, 10)
            return fp
        except Exception:
            pass
    return None


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int,
              start_size: int, min_size: int, font_path: str | None) -> ImageFont.FreeTypeFont:
    font = ImageFont.load_default()
    size = start_size
    while size >= min_size:
        if font_path:
            try:
                font = ImageFont.truetype(font_path, size)
            except Exception:
                pass
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            break
        size -= 4
    return font


def _draw_outlined_text(draw: ImageDraw.ImageDraw, pos: tuple[int, int], text: str,
                        font, fill: tuple, outline: tuple = (0, 0, 0, 255)) -> None:
    x, y = pos
    for ox, oy in _OUTLINE_OFFSETS:
        draw.text((x + ox, y + oy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """Wrap text to fit within max_width. Japanese: char boundary. English: word boundary."""
    is_ascii = all(ord(c) < 128 for c in text)
    lines: list[str] = []
    current = ""

    if is_ascii:
        for word in text.split():
            test = (current + " " + word).strip()
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
    else:
        for char in text:
            test = current + char
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = char

    if current:
        lines.append(current)
    return lines or [text]


def _burn_subtitle(image_path: Path, subtitle: str, output_path: Path,
                   hook_title: str = "") -> Path:
    """Burn subtitle (and optional hook title) onto image — TikTok viral style."""
    with Image.open(image_path).convert("RGBA") as img:
        w, h = img.size
        draw = ImageDraw.Draw(img)
        font_path = _find_font()

        # ── Subtitle (bottom area, white + thick black outline, no box) ──────
        if subtitle:
            if all(ord(c) < 128 for c in subtitle):
                subtitle = subtitle.upper()

            font = _fit_font(draw, subtitle, int(w * 0.88),
                             start_size=max(80, h // 18), min_size=40, font_path=font_path)
            bbox = draw.textbbox((0, 0), subtitle, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            x = (w - tw) // 2
            y = int(h * 0.84) - th // 2
            _draw_outlined_text(draw, (x, y), subtitle, font, fill=(255, 255, 255, 255))

        # ── Hook title card (top area, yellow + thick black outline, wrapped) ──
        if hook_title:
            if all(ord(c) < 128 for c in hook_title):
                hook_title = hook_title.upper()

            max_w = int(w * 0.88)
            hfont_size = max(72, h // 17)
            hfont = ImageFont.load_default()
            if font_path:
                try:
                    hfont = ImageFont.truetype(font_path, hfont_size)
                except Exception:
                    pass

            lines = _wrap_text(draw, hook_title, hfont, max_w)
            # Measure total block height
            line_h = draw.textbbox((0, 0), "あ", font=hfont)[3] + 8
            total_h = line_h * len(lines)
            padding = 20
            hy_start = int(h * 0.09)

            # Dark band covering all lines
            band = Image.new("RGBA", img.size, (0, 0, 0, 0))
            band_draw = ImageDraw.Draw(band)
            band_draw.rectangle(
                [0, hy_start - padding, w, hy_start + total_h + padding],
                fill=(0, 0, 0, 180),
            )
            img = Image.alpha_composite(img, band)
            draw = ImageDraw.Draw(img)

            for i, line in enumerate(lines):
                lbbox = draw.textbbox((0, 0), line, font=hfont)
                lw = lbbox[2] - lbbox[0]
                lx = (w - lw) // 2
                ly = hy_start + i * line_h
                _draw_outlined_text(draw, (lx, ly), line, hfont,
                                    fill=(255, 224, 0, 255))  # #FFE000 yellow

        img.convert("RGB").save(str(output_path))
    return output_path


def build_scene_clip(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    subtitle: str,
    camera_effect: str,
    config: dict,
    hook_title: str = "",
) -> Path:
    """Render a single scene: image + subtitle (PIL) + Ken Burns + audio → MP4."""
    w, h, fps = config["width"], config["height"], config["fps"]
    zoom_max = config.get("zoom_max", 1.2)

    duration = get_audio_duration(audio_path)
    frames = max(int(duration * fps), 1)

    zp = _zoompan_expr(camera_effect, frames, zoom_max)
    scale_w = int(w * zoom_max)
    scale_h = int(h * zoom_max)

    # Burn subtitle (+ optional hook title) into a temp image copy
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_image = Path(tmp.name)
    _burn_subtitle(image_path, subtitle, tmp_image, hook_title=hook_title)

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


def _create_subtitle_overlay(subtitle: str, w: int, h: int, output_path: Path,
                              hook_title: str = "") -> Path:
    """Create a transparent PNG with subtitle (+ optional hook title) for overlay onto video."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font_path = _find_font()

    if subtitle:
        if all(ord(c) < 128 for c in subtitle):
            subtitle = subtitle.upper()
        font = _fit_font(draw, subtitle, int(w * 0.88),
                         start_size=max(80, h // 18), min_size=40, font_path=font_path)
        bbox = draw.textbbox((0, 0), subtitle, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (w - tw) // 2
        y = int(h * 0.84) - th // 2
        _draw_outlined_text(draw, (x, y), subtitle, font, fill=(255, 255, 255, 255))

    if hook_title:
        if all(ord(c) < 128 for c in hook_title):
            hook_title = hook_title.upper()
        max_w = int(w * 0.88)
        hfont_size = max(72, h // 17)
        hfont = ImageFont.load_default()
        if font_path:
            try:
                hfont = ImageFont.truetype(font_path, hfont_size)
            except Exception:
                pass
        lines = _wrap_text(draw, hook_title, hfont, max_w)
        line_h = draw.textbbox((0, 0), "あ", font=hfont)[3] + 8
        total_h = line_h * len(lines)
        padding = 20
        hy_start = int(h * 0.09)
        band = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        band_draw = ImageDraw.Draw(band)
        band_draw.rectangle(
            [0, hy_start - padding, w, hy_start + total_h + padding],
            fill=(0, 0, 0, 180),
        )
        img = Image.alpha_composite(img, band)
        draw = ImageDraw.Draw(img)
        for i, line in enumerate(lines):
            lbbox = draw.textbbox((0, 0), line, font=hfont)
            lw = lbbox[2] - lbbox[0]
            lx = (w - lw) // 2
            ly = hy_start + i * line_h
            _draw_outlined_text(draw, (lx, ly), line, hfont, fill=(255, 224, 0, 255))

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


def add_bgm(video_path: Path, bgm_path: Path, output_path: Path, volume: float = 0.2) -> Path:
    """Mix background music into a video. BGM is looped to match video duration."""
    logger.info("Adding BGM: %s (volume=%.2f)", bgm_path.name, volume)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-stream_loop", "-1", "-i", str(bgm_path),
        "-filter_complex",
        f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info("BGM added → %s", output_path)
    return output_path


def check_ffmpeg() -> None:
    _require_ffmpeg()
