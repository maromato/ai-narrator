# AI Narrator

Generate a short narrated video (1080×1920 MP4) from a single topic string.

**Pipeline:** Topic → LLM storyboard → AI images → TTS narration → FFmpeg video

---

## Requirements

- Python 3.11+
- FFmpeg (with `ffprobe`)
- API keys: Anthropic + OpenAI

```bash
# macOS
brew install ffmpeg

# Check
ffmpeg -version && ffprobe -version
```

---

## Setup

```bash
cd ai_narrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your API keys:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
```

---

## Usage

```bash
# Mock mode — no API calls, free, tests the full pipeline
python run.py --mock

# Default topic (live)
python run.py

# Custom topic (live)
python run.py --topic "Life in Feudal Japan"

# Custom config
python run.py --mock --config config.json
```

Output is saved to `output/<timestamp>/`:

```
output/20261108_120000/
├── storyboard.json   # 4-scene storyboard
├── script.txt        # full narration script
├── scene_1.png       # generated images
├── scene_2.png
├── scene_3.png
├── scene_4.png
├── narration_1.mp3   # per-scene TTS audio
├── narration_2.mp3
├── narration_3.mp3
├── narration_4.mp3
├── clip_1.mp4        # per-scene video clips
├── clip_2.mp4
├── clip_3.mp4
├── clip_4.mp4
├── final.mp4         # ← playable output
└── report.json       # API usage + cost estimate
```

---

## Tests

```bash
pytest tests/ -v
```

The `test_mock_pipeline_produces_mp4` test runs the full end-to-end pipeline in mock mode and verifies the MP4 is created.

---

## Configuration (`config.json`)

| Section | Key | Default | Notes |
|---|---|---|---|
| `llm` | `model` | `claude-sonnet-4-6` | Claude model |
| `image_gen` | `model` | `dall-e-3` | Image model |
| `image_gen` | `quality` | `standard` | `standard` or `hd` |
| `tts` | `voice` | `nova` | `alloy` / `echo` / `fable` / `onyx` / `nova` / `shimmer` |
| `video` | `width`/`height` | `1080`/`1920` | Portrait format |
| `video` | `fps` | `30` | Frame rate |
| `video` | `crf` | `18` | Quality (lower = better) |

---

## Architecture

```
run.py
  └── src/pipeline.py           # orchestrates all steps
        ├── src/adapters/llm.py       # Claude → storyboard JSON
        ├── src/adapters/image_gen.py # DALL-E 3 → PNG images
        ├── src/adapters/tts.py       # OpenAI TTS → MP3 audio
        └── src/video.py              # FFmpeg → MP4 (Ken Burns + subtitles)

mock/adapters.py               # Drop-in replacements for --mock mode
src/storyboard.py              # JSON schema + dataclass
src/report.py                  # Run report (cost, timing, paths)
```

---

## Estimated cost per video

| Service | Usage | Est. cost |
|---|---|---|
| Claude (storyboard) | ~1,500 tokens | ~$0.02 |
| DALL-E 3 standard (×4) | 4 images | ~$0.16 |
| OpenAI TTS (×4 scenes) | ~300 chars | ~$0.005 |
| **Total** | | **~$0.19** |
