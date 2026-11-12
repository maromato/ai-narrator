# AI Narrator

TikTok向け縦型ショート動画（1080×1920）および30秒ミニドラマをトピック1つから自動生成します。

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

# Google News トレンドを参考にトピックを生成（APIキー不要）
.venv/bin/python run.py --topic-from llm --genre finance --lang ja --trends

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
| `--trends` | off | Google News トレンドをシードにトピック生成 |
| `--ab-variants` | `1` | ストーリーボードをN個生成してスコアの高いものを採用 |
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

### TikTok 情報・教育系

| ジャンル | 内容 | 画像スタイル |
|---|---|---|
| `general` | 汎用 | 映画トレーラー風 |
| `history` | 歴史 | ハリウッド歴史映画風 |
| `science` | 科学 | NASA/BBC Planet Earth風 |
| `animals` | 動物（犬中心） | 感動的なドキュメンタリー |
| `religion` | 宗教・精神 | 神聖な光と壮大なスケール |
| `lifestyle` | 健康・生活習慣 | インスタ映えする日常 |
| `selfhelp` | 自己啓発 | 大自然の中の孤独な人物 |
| `workplace` | 副業・仕事術 | リアルなビジネスシーン |
| `japan_travel` | 日本旅行・秘境 | 日本の絶景・神社・温泉 |
| `japan_zen` | 日本の禅・文化 | 枯山水・竹林・静寂 |
| `romance` | 恋愛（科学×駆け引き） | 日本人カップルの日常 |
| `mens_life` | 男性向けライフ | 東京・都市の日本人男性 |
| `beauty` | 美容・スキンケア | J/Kビューティー・白背景 |
| `academia` | ハーバード大学の秘密・小ネタ | Harvard Yard・研究室 |
| `elite_edu` | 一流大学の勉強法・思考法 | Harvard/MIT/Stanfordキャンパス |
| `finance` | 富裕層の習慣・投資家思考 | 都市の金融シーン |
| `psychology` | 心理学・認知バイアス | 感情的な人物ポートレート |

### ミニドラマ系（30秒ショートドラマ）

| ジャンル | 内容 | 画像スタイル |
|---|---|---|
| `drama_kdrama` | 韓ドラ風男女恋愛（財閥・記憶喪失・身分差） | 雨・夜景・ティール＆オレンジ |
| `drama_romance` | 日本ロマンス（静かな恋愛・余白重視） | 桜・夕焼け・アンバー |
| `drama_bl` | 日本BL（20代・スローバーン・胸キュン） | ソフトパステル・ブルーグレー |
| `drama_korean_bl` | 韓国BL（20代・ライバル・禁断の感情） | ネオン・ティール＆ローズ |

---

## トレンド機能

Google News RSS をシードにしてトピックを生成します。APIキー不要。

```bash
# 単発
.venv/bin/python run.py --topic-from llm --genre academia --lang ja --trends

# バッチ
.venv/bin/python run.py --batch-genre academia finance psychology --lang ja --trends
```

使用済みトピックは `used_topics.json` に自動保存され、次回の生成から除外されます。

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
# 複数ジャンルで一括生成
.venv/bin/python run.py --batch-genre academia finance psychology \
  --lang ja --batch-count 3 --trends

# A/Bテスト付き（2バリアント生成してスコアの高い方を採用）
.venv/bin/python run.py --batch-genre drama_kdrama drama_bl \
  --lang ja --batch-count 2 --ab-variants 2
```

---

## ジャンル評価ツール

全ジャンルのストーリーボードをClaudeで自動評価し、TikTok効果スコアでランキングします。

```bash
# 全ジャンル評価（3本ずつ）
.venv/bin/python tools/eval_genres.py --lang ja --top 4 --out results.json

# トレンド機能つき
.venv/bin/python tools/eval_genres.py --lang ja --trends --top 4

# 特定ジャンルだけ
.venv/bin/python tools/eval_genres.py --lang ja --genres academia finance --count 3 --trends
```

**評価基準（各1〜10点）:** hook_power / shareability / specificity / emotional_impact / tiktok_fit / replay_value
**final_score = 平均点 × RPM係数**（academia: ×1.35、finance: ×1.30、psychology: ×1.25 など）

---

## BGM（バックグラウンドミュージック）

### ローカルファイルを使用
```bash
.venv/bin/python run.py --genre romance --lang ja --bgm bgm.mp3
.venv/bin/python run.py --genre romance --lang ja --bgm bgm.mp3 --bgm-volume 0.15
```

### Mubert AIで自動生成
1. [mubert.com](https://mubert.com) でアカウント作成・APIキー取得
2. `.env` に追加: `MUBERT_API_KEY=...`

```bash
.venv/bin/python run.py --genre romance --lang ja --bgm-ai
```

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
.venv/bin/python run.py --tts voicevox --tts-speaker 13 --lang ja
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
.venv/bin/python run.py --mode video --genre drama_kdrama --topic "財閥御曹司との契約結婚"
```

- `KLING_API_KEY` が必要です
- 1クリップあたり約30〜60秒かかります
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
| Kling（×6クリップ） | 動画生成 | ~$1.50〜 |
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
        ├── src/adapters/llm.py              # Claude → ストーリーボードJSON
        ├── src/adapters/image_gen.py        # gpt-image-2 → PNG画像
        ├── src/adapters/tts.py              # OpenAI TTS → MP3
        ├── src/adapters/tts_voicevox.py     # Voicevox → WAV
        ├── src/adapters/video_gen.py        # Kling → MP4クリップ
        ├── src/adapters/trend_research.py   # Google News RSS → トレンドシード
        └── src/video.py                     # FFmpeg → 最終MP4

src/storyboard.py     # JSONスキーマ・ジャンルスタイル・プロンプト生成
src/topic_selector.py # LLMによるトピック自動提案・使用済み履歴管理
src/evaluator.py      # Claude によるストーリーボード自動評価
src/batch.py          # バッチ処理オーケストレーション
src/report.py         # 実行レポート（コスト・タイミング）
tools/eval_genres.py  # ジャンル評価ツール
mock/adapters.py      # --mock用ダミーアダプター
```
