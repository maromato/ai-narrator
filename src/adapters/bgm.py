"""
BGM adapters.

LocalBGMAdapter  — use a user-provided audio file
MubertBGMAdapter — generate music via Mubert API (requires MUBERT_API_KEY)
"""
import hashlib
import logging
import os
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class LocalBGMAdapter:
    """Pass-through adapter for a local audio file."""

    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"BGM file not found: {self.path}")

    def get_bgm(self, duration: float, genre: str, output_path: Path) -> Path:
        """Return the local file as-is (FFmpeg will loop it to fit duration)."""
        import shutil
        shutil.copy2(self.path, output_path)
        logger.info("Local BGM: %s", self.path.name)
        return output_path


class MubertBGMAdapter:
    """Generate royalty-free music via Mubert API."""

    _BASE = "https://api.mubert.com/v2"

    # Genre → Mubert tag mapping
    _TAGS: dict[str, str] = {
        "history":     "epic orchestral",
        "science":     "ambient electronic",
        "animals":     "nature acoustic",
        "religion":    "meditation spiritual",
        "lifestyle":   "chill lofi",
        "selfhelp":    "motivational uplifting",
        "workplace":   "focus productivity",
        "japan_travel":"japanese ambient",
        "japan_zen":   "zen meditation",
        "romance":     "romantic soft pop",
        "mens_life":   "urban hip hop",
        "academia":    "classical piano",
        "general":     "cinematic background",
    }

    def __init__(self, config: dict):
        self._email = config.get("email", "user@example.com")
        self._api_key = os.environ["MUBERT_API_KEY"]
        self._token: str = ""

    def _ensure_token(self) -> None:
        if self._token:
            return
        pat = hashlib.md5(self._api_key.encode()).hexdigest()
        resp = httpx.post(
            f"{self._BASE}/GetServiceAccess",
            json={"method": "GetServiceAccess", "params": {"email": self._email, "license": "ttm", "token": pat}},
            timeout=15,
        )
        resp.raise_for_status()
        self._token = resp.json()["data"]["pat"]
        logger.info("Mubert token obtained")

    def get_bgm(self, duration: float, genre: str, output_path: Path) -> Path:
        self._ensure_token()
        tags = self._TAGS.get(genre, self._TAGS["general"])
        duration_s = max(15, int(duration) + 5)  # at least 15s

        logger.info("Generating Mubert BGM: tags='%s' duration=%ds", tags, duration_s)
        resp = httpx.post(
            f"{self._BASE}/TTM",
            json={
                "method": "TTM",
                "params": {
                    "pat": self._token,
                    "text": tags,
                    "mode": "track",
                    "duration": duration_s,
                    "format": "mp3",
                    "intensity": "medium",
                },
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]

        # Poll for completion
        task_id = data.get("tasks_id") or data.get("task_id", "")
        if task_id:
            audio_url = self._poll(task_id)
        else:
            audio_url = data.get("url", "")

        if not audio_url:
            raise RuntimeError(f"Mubert returned no audio URL: {resp.json()}")

        audio_bytes = httpx.get(audio_url, timeout=60).content
        output_path.write_bytes(audio_bytes)
        logger.info("Mubert BGM saved → %s", output_path)
        return output_path

    def _poll(self, task_id: str, timeout: int = 120) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(5)
            resp = httpx.post(
                f"{self._BASE}/GetTaskStatus",
                json={"method": "GetTaskStatus", "params": {"pat": self._token, "tasks_id": task_id}},
                timeout=15,
            )
            resp.raise_for_status()
            task = resp.json().get("data", {})
            status = task.get("status", "")
            logger.info("Mubert task %s: %s", task_id, status)
            if status == "done":
                return task.get("url", "")
            if status == "error":
                raise RuntimeError(f"Mubert task failed: {task}")
        raise TimeoutError(f"Mubert task {task_id} timed out after {timeout}s")
