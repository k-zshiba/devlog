# devlog

ソフトウェア開発に関する調査メモを GitHub Pages で公開するブログ。Hacker Newsをもとに自動生成されるニュースダイジェストはローカル閲覧用として git で管理。

## ディレクトリ構成

| パス | 内容 |
|------|------|
| `docs/` | GitHub Pages 公開コンテンツ（調査メモ） |
| `digests/` | ニュースダイジェスト（git 管理、Pages 非公開） |
| `scripts/` | ダイジェスト生成スクリプト |

## 使い方

### セットアップ

```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY=your_api_key_here
```

### ダイジェスト生成（Claude Code スキル）

```
/daily-news
```

前日分のニュースダイジェストが `digests/YYYY-MM-DD.md` に生成されます。

### スクリプト直接実行

```bash
python3 scripts/generate_digest.py
```

### 利用するCLIの指定（Claude / Codex / Gemini）

```bash
python3 scripts/generate_digest.py --llm-cli gemini
```

`--llm-cli` には `claude` / `codex` / `gemini` を指定できます。未指定時は、`codex` → `claude` → `gemini` の順で利用可能なCLIを自動選択します。

## ブランチ運用

| ブランチ | 用途 |
|---------|------|
| `main`  | 本番。push すると GitHub Pages へ自動デプロイ |
| `dev`   | 開発用。PR 経由で main へマージ |

## GitHub Pages の有効化

1. GitHubリポジトリの **Settings → Pages** を開く
2. **Source** を `GitHub Actions` に設定
