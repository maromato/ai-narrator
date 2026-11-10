"""Run report — saves a JSON summary of the pipeline execution."""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunReport:
    run_id: str
    topic: str
    mock_mode: bool
    start_time: float = field(default_factory=time.time)

    # Filled in during execution
    end_time: float = 0.0
    output_video: str = ""
    output_storyboard: str = ""
    video_duration_seconds: float = 0.0
    llm_usage: dict = field(default_factory=dict)
    image_gen_usage: dict = field(default_factory=dict)
    tts_usage: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    # Storyboard metadata
    tone: str = ""
    target_audience: str = ""
    hashtags: list = field(default_factory=list)
    genre: str = ""
    lang: str = "en"

    def finish(self) -> None:
        self.end_time = time.time()

    @property
    def elapsed_seconds(self) -> float:
        return round((self.end_time or time.time()) - self.start_time, 1)

    @property
    def total_cost_usd(self) -> float:
        return round(
            self.llm_usage.get("estimated_cost_usd", 0)
            + self.image_gen_usage.get("estimated_cost_usd", 0)
            + self.tts_usage.get("estimated_cost_usd", 0),
            4,
        )

    def to_dict(self) -> dict:
        import datetime
        return {
            "run_id": self.run_id,
            "topic": self.topic,
            "mock_mode": self.mock_mode,
            "start_time": datetime.datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "elapsed_seconds": self.elapsed_seconds,
            "output": {
                "video": self.output_video,
                "storyboard": self.output_storyboard,
            },
            "video_duration_seconds": round(self.video_duration_seconds, 2),
            "api_usage": {
                "llm":       self.llm_usage,
                "image_gen": self.image_gen_usage,
                "tts":       self.tts_usage,
            },
            "total_estimated_cost_usd": self.total_cost_usd,
            "errors": self.errors,
            "content": {
                "genre":           self.genre,
                "lang":            self.lang,
                "tone":            self.tone,
                "target_audience": self.target_audience,
                "hashtags":        self.hashtags,
            },
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))
        print(f"Report saved → {path}")
