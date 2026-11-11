# AI Narrator

TikTok向け縦型ショート動画（1080×1920）をトピック1つから自動生成します。

**パイプライン:** トピック → Claude（ストーリーボード） → 画像/動画生成 → TTS音声 → FFmpeg合成 → MP4

---

## 必要なもの

- Python 3.11+
- FFmpeg（`ffprobe` 含む）
- APIキー: Anthropic + OpenAI（静止画モード）、Kling（動画モード、任意）

```bash
# macOS
brew install ffmpeg
```

---

## セットアップ

```bash
cd ai_narrator
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env にAPIキーを入力:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
#   KLING_API_KEY=...  # --mode video を使う場合のみ
```

---

## 基本的な使い方

```bash
# モックモード（APIコールなし・無料）— 動作確認用
.venv/bin/python run.py --mock

# デフォルトトピックで実行
.venv/bin/python run.py

# トピックを指定
.venv/bin/python run.py --topic "江戸時代の朝"

# ジャンルを指定
.venv/bin/python run.py --topic "古代ローマの崩壊" --genre history

# 日本語ナレーション
.venv/bin/python run.py --topic "桜の秘密" --genre japan_zen --lang ja

# Claude にトピックを自動選択させる
.venv/bin/python run.py --topic-from llm --genre romance --lang ja

# トピック候補を表示して選ぶ（インタラクティブ）
.venv/bin/python run.py --topic-from llm --genre romance --lang ja --interactive
```

---

## 全オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--topic` | `"A morning in Ancient Rome"` | 動画のトピック |
| `--genre` | `general` | 画像スタイルのジャンル（下記参照） |
| `--lang` | `en` | ナレーション言語: `en` / `ja` |
| `--mode` | `static` | `static`（静止画+Ken Burns）/ `video`（Kling動画生成） |
| `--topic-from` | `manual` | `manual`（--topicを使用）/ `llm`（Claudeが自動提案） |
| `--interactive` | off | `--topic-from llm` 時に候補を表示して選択 |
| `--tts` | config準拠 | `openai` / `voicevox` |
| `--tts-speaker` | `1` | Voicevox スピーカーID |
| `--bgm` | なし | ローカル音楽ファイルのパス（例: bgm.mp3） |
| `--bgm-ai` | off | Mubert APIでBGM自動生成 |
| `--bgm-volume` | `0.2` | BGM音量（0.0〜1.0） |
| `--no-subtitle` | off | 字幕オーバーレイを無効化 |
| `--mock` | off | APIコールなし・無料のテストモード |
| `--config` | `config.json` | 設定ファイルのパス |

---

## ジャンル一覧

| ジャンル | 内容 | 画像スタイル |
|---|---|---|
| `general` | 汎用 | 映画トレーラー風 |
| `history` | 歴史 | ハリウッド歴史映画風 |
| `science` | 科学 | NASA/BBC Planet Earth風 |
| `animals` | 動物 | Pixar/DreamWorks 3Dアニメ風 |
| `religion` | 宗教・精神 | 神聖な光と壮大なスケール |
| `lifestyle` | ライフスタイル | インスタ映えする日常 |
| `selfhelp` | 自己啓発 | 大自然の中の孤独な人物 |
| `workplace` | 職場・仕事 | リアルなビジネスシーン |
| `japan_travel` | 日本旅行 | 日本の絶景・神社・温泉 |
| `japan_zen` | 日本の禅・仏教 | 枯山水・竹林・静寂 |
| `romance` | 恋愛・カップル | 日本人カップルの日常 |
| `mens_life` | 男性向けライフ | 東京・都市の日本人男性 |
| `academia` | ハーバード式・一流大学の知識 | アイビーリーグの図書館・講堂 |

---

## バッチ処理

### YAMLファイルで一括生成

```bash
.venv/bin/python run.py --batch topics.yaml
.venv/bin/python run.py --batch topics.yaml --mock  # 動作確認
```

`topics.yaml` の書き方：
```yaml
- topic: "なぜ犬は飼い主の帰宅がわかるのか"
  genre: animals
  lang: ja

- topic_from: llm        # Claude がトピックを自動選択
  genre: romance
  lang: ja

- topic: "The Fall of Rome"
  genre: history
  lang: en
  subtitle: false        # 字幕なし
```

### ジャンル指定で自動一括生成

```bash
# romance ジャンルで5本自動生成（デフォルト）
.venv/bin/python run.py --batch-genre romance --lang ja

# 本数を指定
.venv/bin/python run.py --batch-genre animals --lang ja --batch-count 3
```

---

## BGM（バックグラウンドミュージック）

### ローカルファイルを使用
```bash
.venv/bin/python run.py --genre romance --lang ja --bgm bgm.mp3
.venv/bin/python run.py --genre romance --lang ja --bgm bgm.mp3 --bgm-volume 0.15
```

### Mubert AIで自動生成
ジャンルに合わせて自動的にBGMが生成されます。

1. [mubert.com](https://mubert.com) でアカウント作成・APIキー取得
2. `.env` に追加: `MUBERT_API_KEY=...`
3. `config.json` の `bgm.email` を自分のメールアドレスに変更

```bash
.venv/bin/python run.py --genre romance --lang ja --bgm-ai
```

**ジャンル別BGMスタイル**

| ジャンル | BGMスタイル |
|---|---|
| `history` | epic orchestral |
| `science` | ambient electronic |
| `animals` | nature acoustic |
| `religion` | meditation spiritual |
| `lifestyle` | chill lofi |
| `selfhelp` | motivational uplifting |
| `workplace` | focus productivity |
| `japan_travel` | japanese ambient |
| `japan_zen` | zen meditation |
| `romance` | romantic soft pop |
| `mens_life` | urban hip hop |
| `academia` | classical piano |
| `general` | cinematic background |

BGMなし（デフォルト）の場合はオプション不要です。

---

## TTS（音声合成）

### OpenAI（デフォルト）
```bash
.venv/bin/python run.py --lang ja   # config.json の設定を使用
```

### Voicevox（無料・ローカル・自然な日本語）
1. [voicevox.hiroshiba.jp](https://voicevox.hiroshiba.jp/) からインストール・起動
2. オプションで指定:
```bash
.venv/bin/python run.py --tts voicevox --lang ja
.venv/bin/python run.py --tts voicevox --tts-speaker 13 --lang ja  # スピーカー指定
```

**主なVoicevoxスピーカーID**

| ID | キャラクター |
|---|---|
| 1 | ずんだもん（ノーマル） |
| 3 | ずんだもん（喜び） |
| 2 | 四国めたん |
| 8 | 春日部つむぎ |
| 13 | 青山龍星（落ち着いた男性） |

---

## 動画生成モード（Kling）

静止画+Ken Burnsではなく、AIが動画クリップを生成します。

```bash
.venv/bin/python run.py --mode video --genre history --topic "古代ローマ"
```

- `KLING_API_KEY` が必要です
- 1クリップあたり約30〜60秒かかります（Klingの生成時間）
- コスト: 5秒クリップ $0.25、10秒クリップ $0.50 程度

---

## 出力ファイル

```
output/20261109_120000/
├── storyboard.json     # 6シーンのストーリーボード（トーン・ハッシュタグ含む）
├── script.txt          # 全体ナレーション
├── scene_1.png         # 生成画像（staticモード）
│   ...
├── narration_1.mp3     # シーンごとの音声
│   ...
├── clip_1.mp4          # シーンごとの動画クリップ
│   ...
├── final.mp4           # ← 最終出力
└── report.json         # API使用量・コスト・ハッシュタグ
```

---

## 費用の目安（1本あたり）

### 静止画モード（static）
| サービス | 内容 | 費用 |
|---|---|---|
| Claude | ストーリーボード生成 | ~$0.02 |
| gpt-image-2 low（×6） | 画像生成 | ~$0.07 |
| OpenAI TTS（×6シーン） | 音声合成 | ~$0.01 |
| **合計** | | **~$0.10** |

### 動画モード（video / Kling）
| サービス | 内容 | 費用 |
|---|---|---|
| Claude | ストーリーボード生成 | ~$0.02 |
| Kling kling-v3（×6クリップ） | 動画生成 | ~$1.50〜 |
| OpenAI TTS（×6シーン） | 音声合成 | ~$0.01 |
| **合計** | | **~$1.55〜** |

---

## 設定ファイル（config.json）

| セクション | キー | デフォルト | 説明 |
|---|---|---|---|
| `llm` | `model` | `claude-sonnet-4-6` | Claudeモデル |
| `llm` | `max_tokens` | `3500` | 最大トークン数 |
| `image_gen` | `model` | `gpt-image-2` | 画像生成モデル |
| `image_gen` | `quality` | `low` | `low` / `medium` / `high` |
| `tts` | `provider` | `openai` | `openai` / `voicevox` |
| `tts` | `model` | `tts-1` | `tts-1` / `tts-1-hd` |
| `tts` | `voice` | `nova` | `alloy` / `echo` / `nova` / `onyx` / `shimmer` |
| `video_gen` | `model` | `kling-v3` | Klingモデル |
| `video` | `width`/`height` | `1080`/`1920` | 縦型フォーマット |
| `video` | `fps` | `30` | フレームレート |

---

## アーキテクチャ

```
run.py
  └── src/pipeline.py
        ├── src/adapters/llm.py           # Claude → ストーリーボードJSON
        ├── src/adapters/image_gen.py     # gpt-image-2 → PNG画像
        ├── src/adapters/tts.py           # OpenAI TTS → MP3
        ├── src/adapters/tts_voicevox.py  # Voicevox → WAV
        ├── src/adapters/video_gen.py     # Kling → MP4クリップ
        └── src/video.py                  # FFmpeg → 最終MP4

src/storyboard.py     # JSONスキーマ・ジャンルスタイル・プロンプト生成
src/topic_selector.py # LLMによるトピック自動提案
src/report.py         # 実行レポート（コスト・タイミング）
mock/adapters.py      # --mock用ダミーアダプター
```
