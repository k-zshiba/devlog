# devlog

ソフトウェア開発に関する調査メモを GitHub Pages で公開するブログ。

## ディレクトリ構成

| パス | 内容 |
|------|------|
| `docs/` | GitHub Pages 公開コンテンツ（調査メモ） |

## ブランチ運用

| ブランチ | 用途 |
|---------|------|
| `main`  | 本番。push すると GitHub Pages へ自動デプロイ |
| `dev`   | 開発用。PR 経由で main へマージ |

## GitHub Pages の有効化

1. GitHubリポジトリの **Settings → Pages** を開く
2. **Source** を `GitHub Actions` に設定
