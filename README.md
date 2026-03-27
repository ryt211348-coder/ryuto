# TikTok Viral Analysis Tool

TikTokアカウントの100万再生以上の動画を抽出し、台本を文字起こしして、バイラルの共通項を分析するツールです。

## セットアップ

```bash
pip install -r requirements.txt
```

## 使い方

```bash
# アカウントの動画を分析
python main.py analyze https://www.tiktok.com/@username

# 最低再生数を変更（デフォルト: 1,000,000）
python main.py analyze https://www.tiktok.com/@username --min-views 500000

# Whisperモデルサイズを指定（tiny/base/small/medium/large）
python main.py analyze https://www.tiktok.com/@username --whisper-model medium

# 出力ディレクトリを指定
python main.py analyze https://www.tiktok.com/@username --output-dir ./results
```

## 出力

- `results/videos.json` - 抽出された動画メタデータ
- `results/transcripts/` - 各動画の文字起こしテキスト
- `results/analysis_report.md` - バイラル共通項の分析レポート
