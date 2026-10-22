---
title: PostgreSQLの型変換：資料の補足
---

# PostgreSQLの型変換：資料の補足

[スライドを開く](casts.html)

## 元資料でのSQL検証条件

- PostgreSQL 20devel、`master / 7787aec8ab000932a8704a988b175b39ff816f2f`
- UTF8、locale C、JIT無効
- 専用Unixソケットを使った一時データベースで実行
- ビルド設定：`buildtype=debug`、`cassert=true`

ここに記載した条件は元資料のREADMEに基づきます。devlogへの追加時にSQLの再検証は行っていません。

## フォント

[Google FontsのNoto Sans JP](https://github.com/google/fonts/tree/main/ofl/notosansjp)を同梱しています。利用条件は [assets/OFL.txt](assets/OFL.txt) を参照してください。
