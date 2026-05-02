# devlog

ソフトウェア開発に関するニュースまとめと調査メモを日々記録するログ。Hacker Newsをもとに自動生成されるダイジェストと、自分で調べたことをマークダウンでまとめたメモを GitHub Pages で公開。

## 使い方

### セットアップ

```bash
pip3 install -r requirements.txt
export ANTHROPIC_API_KEY=your_api_key_here
```

### ダイジェスト生成（Claude Code スキル）

Claude Code 上で以下のコマンドを実行:

```
/daily-news
```

前日分のニュースダイジェストが `docs/YYYY-MM-DD.md` に生成されます。

### スクリプト直接実行

```bash
python3 scripts/generate_digest.py
```

## ブランチ運用

| ブランチ | 用途 |
|---------|------|
| `main`  | 本番。push すると GitHub Pages へ自動デプロイ |
| `dev`   | 開発用。PR 経由で main へマージ |

## GitHub Pages の有効化

1. GitHubリポジトリの **Settings → Pages** を開く
2. **Source** を `GitHub Actions` に設定

## 生成物

- `docs/YYYY-MM-DD.md` — 各日のニュースダイジェスト
- `docs/index.md` — ダイジェスト一覧ページ
