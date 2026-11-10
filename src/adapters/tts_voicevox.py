"""Voicevox TTS adapter — calls local Voicevox Engine REST API."""
import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class VoicevoxAdapter:
    file_ext = "wav"

    def __init__(self, config: dict):
        self.speaker = config.get("speaker", 1)
        self.base_url = config.get("base_url", "http://localhost:50021").rstrip("/")
        self.usage: dict = {"characters": 0, "estimated_cost_usd": 0.0}

    def synthesize(self, text: str, output_path: Path) -> Path:
        logger.info("Synthesizing Voicevox TTS: %s (speaker=%d)", output_path.name, self.speaker)

        with httpx.Client(timeout=30) as client:
            # Step 1: generate audio query
            resp = client.post(
                f"{self.base_url}/audio_query",
                params={"text": text, "speaker": self.speaker},
            )
            if resp.status_code != 200:
                logger.error("Voicevox audio_query failed (%d): %s", resp.status_code, resp.text)
                resp.raise_for_status()
            query = resp.json()

            # Step 2: synthesize to WAV
            resp = client.post(
                f"{self.base_url}/synthesis",
                params={"speaker": self.speaker},
                json=query,
                timeout=60,
            )
            if resp.status_code != 200:
                logger.error("Voicevox synthesis failed (%d): %s", resp.status_code, resp.text)
                resp.raise_for_status()

        output_path.write_bytes(resp.content)
        self.usage["characters"] += len(text)
        logger.info("Audio saved → %s (%d chars)", output_path, len(text))
        return output_path
