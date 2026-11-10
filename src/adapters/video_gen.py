"""
Kling video generation adapter.

Workflow (async):
  1. POST /v1/videos/text2video  → task_id
  2. GET  /v1/videos/text2video/{task_id}  (poll until succeed)
  3. Download video from URL
"""
import logging
import os
import time
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.klingai.com/v1"
_POLL_INTERVAL = 5   # seconds between status checks
_POLL_TIMEOUT  = 300  # max seconds to wait per clip


class KlingAdapter:
    def __init__(self, config: dict):
        self.config = config
        self._api_key = os.environ["KLING_API_KEY"]
        self.usage: dict = {"videos_generated": 0, "estimated_cost_usd": 0.0}

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=20))
    def generate_video(self, prompt: str, output_path: Path, duration: int = 5) -> Path:
        """Generate a video clip from a text prompt. duration: 5 or 10 seconds."""
        logger.info("Generating video clip: %s", output_path.name)

        # Clamp duration to Kling supported values
        duration = 10 if duration >= 8 else 5

        payload = {
            "model_name":     self.config.get("model", "kling-v1"),
            "prompt":         prompt[:2500],
            "aspect_ratio":   self.config.get("aspect_ratio", "9:16"),
            "duration":       str(duration),
            "mode":           self.config.get("mode", "std"),
        }
        if "negative_prompt" in self.config:
            payload["negative_prompt"] = self.config["negative_prompt"]

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{_BASE_URL}/videos/text2video",
                headers=self._headers(),
                json=payload,
            )

        if resp.status_code != 200:
            logger.error("Kling submit failed (%d): %s", resp.status_code, resp.text)
            resp.raise_for_status()

        task_id = resp.json()["data"]["task_id"]
        logger.info("Kling task submitted: %s", task_id)

        # Poll until complete
        video_url = self._wait_for_completion(task_id)

        # Download video
        logger.info("Downloading video: %s", output_path.name)
        video_bytes = httpx.get(video_url, timeout=120).content
        output_path.write_bytes(video_bytes)

        cost = 0.05 * duration  # rough estimate
        self.usage["videos_generated"] += 1
        self.usage["estimated_cost_usd"] = round(
            self.usage["estimated_cost_usd"] + cost, 4
        )
        self.usage["model"] = self.config.get("model", "kling-v1")
        logger.info("Video saved → %s", output_path)
        return output_path

    def _wait_for_completion(self, task_id: str) -> str:
        """Poll task status until succeed, return video URL."""
        deadline = time.time() + _POLL_TIMEOUT
        while time.time() < deadline:
            time.sleep(_POLL_INTERVAL)
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    f"{_BASE_URL}/videos/text2video/{task_id}",
                    headers=self._headers(),
                )
            if resp.status_code != 200:
                logger.warning("Kling poll error (%d): %s", resp.status_code, resp.text)
                continue

            data = resp.json().get("data", {})
            status = data.get("task_status", "")
            logger.info("Kling task %s status: %s", task_id, status)

            if status == "succeed":
                videos = data.get("task_result", {}).get("videos", [])
                if videos:
                    return videos[0]["url"]
                raise RuntimeError(f"Kling task {task_id} succeeded but no video URL returned")
            elif status == "failed":
                raise RuntimeError(f"Kling task {task_id} failed: {data}")

        raise TimeoutError(f"Kling task {task_id} timed out after {_POLL_TIMEOUT}s")
