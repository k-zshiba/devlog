# devlog

ソフトウェア開発に関する調査メモを GitHub Pages で公開するブログ。

## ディレクトリ構成

| パス | 内容 |
|------|------|
| `docs/` | GitHub Pages 公開コンテンツ（調査メモ） |
| `scripts/` | 通常記事と Marp スライドのビルド処理 |

## 記事・スライドの追加

通常記事もスライドも、同じ `docs/` に `.md` ファイルを追加します。
サブディレクトリも使用できます。先頭のフロントマターで表示形式を選びます。

通常記事（`marp: false` または `marp` を省略）：

```markdown
---
title: 調査メモ
marp: false
---

# 調査メモ

本文……
```

スライド（`marp: true`）：

```markdown
---
title: 発表資料
marp: true
theme: default
paginate: true
---

# 発表タイトル

1枚目の内容

---

# 次のページ

2枚目の内容
```

`true` / `false` は引用符を付けない YAML の真偽値で指定します。
通常記事には既定の Jekyll レイアウトが適用され、スライドは Marp が単独の HTML として生成します。
スライドでは Jekyll の `layout`、`permalink`、Liquid テンプレートは使用しません。

どちらも `docs/example.md` は `example.html`、`docs/topic/example.md` は
`topic/example.html` で公開します（通常記事で `permalink` を指定した場合を除く）。
同じ公開パスのファイルは作らないでください。
記事一覧は手動管理です。追加後は `docs/index.md` に公開先へのリンクを追記します。

```liquid
- [発表資料]({{ '/topic/example.html' | relative_url }})
```

スライド内の画像は Markdown からの相対パスで参照できます。
画像などのアセットは記事と共通で公開されます。
スライド内の HTML タグも有効です。
スライドの実例は `docs/marp-example.md` を参照してください。

## ローカルのビルド・プレビュー

Node.js 22 以上、Docker、プレビュー用の Python 3 を使用します。
リポジトリのルートで実行してください。

```bash
npm ci
npm test
npm run prepare:content
docker run --rm --user "$(id -u):$(id -g)" --entrypoint /usr/local/bundle/bin/jekyll \
  -v "$PWD:/repo" -w /repo \
  ghcr.io/actions/jekyll-build-pages:v1.0.13 \
  build --source /repo/.build/docs --destination /repo/_site
npm run build:slides
python3 -m http.server 4000 --directory _site --bind 127.0.0.1
```

ブラウザでポート 4000 のトップページや各 `.html` を確認できます。
Markdown を編集したら `prepare:content` → Jekyll ビルド → `build:slides` の順に再実行し、
ブラウザを再読み込みします。Jekyll はビルド時に出力先を掃除するため、スライド生成は必ず最後に行います。
既存の出力と衝突した場合、スライド生成は上書きせずエラーにします。

`.build/docs/` はスライドを除いた Jekyll 入力用の一時コピーです。
原本の `docs/` は変更せず、通常記事とスライドの二重生成を防ぎます。
本番公開と PR プレビューでも同じ手順で `_site/` を作成します。
CI では `SITE_BASEURL` を使い、一時コピーに本番・PR ごとの公開パスを設定します。

## ブランチ運用

| ブランチ | 用途 |
|---------|------|
| `main`  | 本番。push すると GitHub Pages へ自動デプロイ |
| `dev`   | 開発用。PR 経由で main へマージ |

## GitHub Pages の有効化

1. GitHub リポジトリの **Settings → Pages** を開く
2. **Source** を `Deploy from a branch` に設定
3. ブランチを `gh-pages`、フォルダを `/ (root)` に設定

GitHub Actions が生成済み HTML を `gh-pages` ブランチへ配置します。
`GITHUB_TOKEN` による push では Pages のビルドが自動起動しないため、
本番・PR プレビューとも配置後に Pages API でビルドをリクエストします。
プレビューのリンクは、その後の Pages デプロイ完了後にアクセスできます。
