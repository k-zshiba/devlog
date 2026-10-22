---
title: Marp スライドの書き方
marp: true
theme: default
paginate: true
lang: ja
---

# Marp スライドの書き方

記事と同じ `docs/` に Markdown を置きます。

---

## 表示形式の選択

先頭の設定欄に `marp: true` を指定するとスライドになります。

```yaml
---
title: 発表資料
marp: true
theme: default
paginate: true
---
```

---

## ページの区切り

本文中の `---` で次のスライドに進みます。

- 左右キーで移動
- 公開先は Markdown と同じパスの `.html`
- `marp: false` または省略なら通常記事
