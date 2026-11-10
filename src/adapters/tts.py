"""TTS adapter — calls OpenAI REST API directly via httpx."""
import logging
import os
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/audio/speech"


class OpenAITTSAdapter:
    def __init__(self, config: dict):
        self.config = config
        self._api_key = os.environ["OPENAI_API_KEY"]
        self.usage: dict = {"characters": 0, "estimated_cost_usd": 0.0}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def synthesize(self, text: str, output_path: Path) -> Path:
        logger.info("Synthesizing TTS: %s", output_path.name)

        payload = {
            "model": self.config["model"],
            "voice": self.config["voice"],
            "input": text,
            "speed": self.config.get("speed", 1.0),
            "response_format": "mp3",
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                _API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )

        if resp.status_code != 200:
            logger.error("TTS failed (%d): %s", resp.status_code, resp.text)
            resp.raise_for_status()

        output_path.write_bytes(resp.content)

        self.usage["model"] = self.config["model"]
        self.usage["characters"] += len(text)
        self.usage["estimated_cost_usd"] = round(self.usage["characters"] * 15e-6, 6)
        logger.info("Audio saved → %s (%d chars)", output_path, len(text))
        return output_path
