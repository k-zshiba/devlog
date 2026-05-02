---
layout: default
title: PostgreSQL Rendezvous Variable
date: 2026-05-03
---

# PostgreSQL Rendezvous Variable

*2026-05-03*

## 概要

Rendezvous variable は、PostgreSQL の拡張機能フレームワークにおいて、動的にロードされた複数の拡張モジュール間で実行時に相互通信を行うための仕組み。

通常の方法では、拡張 A が拡張 B の関数を呼ぼうとするとコンパイル時のリンク依存が生じる。Rendezvous variable を使うと、名前付きのグローバルポインタ（`void *`）を介して API を受け渡せるため、**コンパイル時の依存なしに拡張間通信**が実現できる。

## API

```c
/* src/include/fmgr.h */
extern void **find_rendezvous_variable(const char *varName);
```

- 引数: 変数名（最大 `NAMEDATALEN` 文字）
- 戻り値: `void **`（保存先ポインタへのポインタ）
- 同じ名前で呼び出すと常に同じアドレスを返す
- 初回呼び出し時にエントリを自動作成し、`NULL` で初期化

実装は `src/backend/utils/fmgr/dfmgr.c` にあり、プロセスローカルなハッシュテーブルで管理される。

## 基本パターン

### プロバイダー側（API を登録する拡張）

```c
typedef struct {
    void (*on_func_beg)(PLpgSQL_execstate *estate, PLpgSQL_function *func);
    void (*on_func_end)(PLpgSQL_execstate *estate, PLpgSQL_function *func);
} MyExtAPI;

void _PG_init(void)
{
    MyExtAPI *api = palloc(sizeof(MyExtAPI));
    api->on_func_beg = my_on_func_beg;
    api->on_func_end = my_on_func_end;

    void **var = find_rendezvous_variable("my_ext.api");
    *var = (void *) api;
}
```

### コンシューマー側（API を利用する拡張）

```c
void _PG_init(void)
{
    void **var = find_rendezvous_variable("my_ext.api");
    MyExtAPI *api = (MyExtAPI *) *var;

    if (api != NULL)
        api->on_func_beg(...);
}
```

## 実際の使用例：PL/pgSQL プラグインシステム

PL/pgSQL は rendezvous variable を使ってプラグイン機構を実装している（`src/pl/plpgsql/src/pl_handler.c`）。

`plpgsql.plugin` という rendezvous variable に `PLpgSQL_plugin` 構造体を登録することで、外部拡張が PL/pgSQL の実行フローにフックを差し込める。例えば `plpgsql_check` や `pg_query_settings` がこの仕組みを利用している。

## 注意事項

**スコープはプロセスローカル**  
共有メモリには置かれない。各バックエンドプロセスが独立したハッシュテーブルを持つ。バックエンド間の共有には別の仕組み（`ShmemInitStruct` など）が必要。

**型安全性がない**  
`void *` を使うため、プロバイダーとコンシューマーが同じ構造体定義を参照する責任がある。ずれるとメモリ破壊につながる。共有ヘッダで構造体を定義するか、バージョンフィールドを入れるとよい。

**NULL チェック必須**  
プロバイダーが先にロードされていない場合 `*var` は `NULL` になる。コンシューマー側で必ずチェックする。

**初期化タイミング**  
`_PG_init()` 内で登録するのが通例。`shared_preload_libraries` に登録すれば起動時に確実に初期化される。

## まとめ

| 項目 | 内容 |
|------|------|
| 目的 | 動的ロード拡張間のコンパイル依存なし通信 |
| API | `find_rendezvous_variable(name)` → `void **` |
| スコープ | プロセスローカル |
| 型安全 | なし（`void *`） |
| 実装例 | PL/pgSQL プラグインシステム |
| ソース | `src/backend/utils/fmgr/dfmgr.c` |

## 参考

- [PostgreSQL wiki – PostgresServerExtensionPoints](https://wiki.postgresql.org/wiki/PostgresServerExtensionPoints)
- [PostgreSQL Doxygen – dfmgr.c](https://doxygen.postgresql.org/dfmgr_8c.html)
- `src/include/fmgr.h`
- `src/pl/plpgsql/src/pl_handler.c`
