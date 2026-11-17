"""
Cloud upload adapter — uploads final output to Google Drive (or any rclone remote).

Setup:
  1. rclone config  → set up a remote named "gdrive"
  2. config.json に追加:
       "cloud": { "enabled": true, "remote": "gdrive:ai_narrator", "cleanup_intermediates": true }
"""
import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_KEEP = {"final.mp4", "storyboard.json", "report.json", "script.txt"}


def _rclone_bin() -> str | None:
    """Find rclone binary: PATH first, then ~/bin/rclone fallback."""
    if shutil.which("rclone"):
        return "rclone"
    local = os.path.expanduser("~/bin/rclone")
    if os.path.isfile(local) and os.access(local, os.X_OK):
        return local
    return None

_INTERMEDIATE_PATTERNS = [
    "scene_*.png",
    "narration_*.mp3",
    "narration_*.wav",
    "clip_*.mp4",
    "final_no_bgm.mp4",
    "bgm.mp3",
    "raw_*.mp4",
]


def upload_run(out_dir: Path, remote: str) -> bool:
    """Upload final output files to rclone remote. Returns True on success."""
    rclone = _rclone_bin()
    if not rclone:
        logger.error("rclone not found — skipping upload")
        return False

    remote_path = f"{remote}/{out_dir.name}"
    uploaded = 0
    for filename in _KEEP:
        local = out_dir / filename
        if not local.exists():
            continue
        try:
            subprocess.run(
                [rclone, "copy", str(local), remote_path],
                check=True, capture_output=True,
            )
            logger.info("Uploaded %s → %s", filename, remote_path)
            uploaded += 1
        except subprocess.CalledProcessError as e:
            logger.error("Upload failed for %s: %s", filename, e.stderr.decode())
            return False

    logger.info("Cloud upload complete: %d files → %s", uploaded, remote_path)
    return True


def cleanup_intermediates(out_dir: Path) -> None:
    """Delete large intermediate files, keeping only final output + JSONs."""
    deleted = 0
    for pattern in _INTERMEDIATE_PATTERNS:
        for f in out_dir.glob(pattern):
            f.unlink()
            logger.info("Deleted intermediate: %s", f.name)
            deleted += 1
    logger.info("Cleanup done: %d files deleted from %s", deleted, out_dir.name)
