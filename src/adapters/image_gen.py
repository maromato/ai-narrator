"""Image generation adapter — calls OpenAI REST API directly via httpx."""
import base64
import logging
import os
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/images/generations"
_COST = {
    "gpt-image-1": {"low": 0.011, "medium": 0.042, "high": 0.167},
    "dall-e-3":    {"standard": 0.040, "hd": 0.080},
}


class DalleAdapter:
    def __init__(self, config: dict):
        self.config = config
        self._api_key = os.environ["OPENAI_API_KEY"]
        self.usage: dict = {"images_generated": 0, "estimated_cost_usd": 0.0}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=20))
    def generate_image(self, prompt: str, output_path: Path) -> Path:
        logger.info("Generating image: %s", output_path.name)

        safe_prompt = prompt[:3800] if len(prompt) > 3800 else prompt
        if len(prompt) > 3800:
            logger.warning("Prompt truncated from %d to 3800 chars", len(prompt))

        model = self.config["model"]
        payload = {
            "model": model,
            "prompt": safe_prompt,
            "size": self.config["size"],
            "quality": self.config["quality"],
            "n": 1,
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                _API_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )

        if resp.status_code != 200:
            logger.error("Image generation failed (%d): %s", resp.status_code, resp.text)
            resp.raise_for_status()

        item = resp.json()["data"][0]
        if item.get("url"):
            image_bytes = httpx.get(item["url"], timeout=60).content
        else:
            image_bytes = base64.b64decode(item["b64_json"])

        output_path.write_bytes(image_bytes)

        quality = self.config["quality"]
        cost = _COST.get(model, {}).get(quality, 0.04)
        self.usage["images_generated"] += 1
        self.usage["estimated_cost_usd"] = round(self.usage["estimated_cost_usd"] + cost, 4)
        self.usage["model"] = model
        logger.info("Image saved → %s", output_path)
        return output_path
