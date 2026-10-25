---
marp: true
theme: default
size: 16:9
paginate: true
lang: ja
title: PostgreSQLの型変換：SQLからC関数まで
description: キャストの許可条件、pg_cast、変換方式、C関数の実装とunknownの扱いを解説する15分の発表資料
footer: PostgreSQL / 型変換
style: |
  @font-face {
    font-family: 'Noto Sans JP';
    src: url('./assets/NotoSansJP.ttf') format('truetype');
    font-weight: 100 900;
  }
  section {
    background: #f5f4ef;
    color: #182b3a;
    font-family: 'Noto Sans JP', sans-serif;
    font-size: 27px;
    line-height: 1.6;
    padding: 48px 64px;
    justify-content: flex-start;
    border-top: 9px solid #137c83;
  }
  h1 { font-size: 41px; line-height: 1.35; letter-spacing: -0.025em; margin: 8px 0 27px; color: #182b3a; }
  h2 { font-size: 29px; color: #137c83; margin: 15px 0; }
  p { margin: 10px 0 18px; }
  strong { color: #08777f; font-weight: 800; }
  code { font-family: 'DejaVu Sans Mono', 'Noto Sans JP', monospace; font-size: 0.85em; background: #e8eded; color: #155e6a; }
  pre { background: #e9eeed; border: 1px solid #d0dcda; padding: 17px 22px; border-radius: 10px; line-height: 1.45; }
  pre code { font-size: 22px; background: transparent; }
  table { width: 100%; font-size: 25px; border-collapse: collapse; display: table; margin: 16px 0; }
  th { background: #dce9e7; color: #182b3a; }
  th, td { padding: 10px 15px; border-color: #cbd8d5; }
  tr { background: transparent; }
  tr:nth-child(2n) { background: #edf0eb; }
  blockquote { border-left: 5px solid #d48a3b; background: #f2eadd; padding: 9px 20px; color: #56412c; margin: 18px 0; }
  footer { font-size: 15px; color: #687b84; bottom: 20px; }
  section::after { font-size: 16px; color: #687b84; bottom: 20px; }
  a { color: #08777f; }
  .eyebrow { font-size: 17px; letter-spacing: 0.09em; font-weight: 700; color: #137c83; margin: 0 0 10px; }
  .small { font-size: 21px; }
  .source { font-size: 15px; color: #687b84; line-height: 1.45; margin-top: auto; }
  .source code { font-size: 14px; }
  .lead { font-size: 35px; line-height: 1.6; }
  .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; align-items: start; }
  .card { border: 1px solid #cbd8d5; border-radius: 12px; background: #fffdf8; padding: 19px 23px; }
  .flow { display: flex; align-items: center; gap: 13px; margin: 22px 0; }
  .flow .card { flex: 1; text-align: center; padding: 17px 10px; font-size: 24px; }
  .arrow { font-size: 32px; color: #137c83; }
  .nest { border-radius: 14px; border: 2px solid #b7cfca; background: #e3ece7; padding: 16px 24px; }
  .nest .nest { background: #d0e5de; margin-top: 12px; }
  .nest .nest .nest { background: #137c83; color: #fff; }
  section.cover, section.finish { background: #142d3c; color: #f5f4ef; border-top-color: #4ec3b1; }
  section.cover h1, section.finish h1 { color: #f5f4ef; font-size: 56px; margin-top: 38px; }
  section.cover strong, section.finish strong, section.cover .eyebrow, section.finish .eyebrow { color: #6bd4c4; }
  section.cover footer, section.cover::after, section.finish footer, section.finish::after { color: #9eb6be; }
  section.dense pre code { font-size: 20px; }
  section.dense pre { padding: 13px 22px; }
  section.dense h1 { margin-bottom: 20px; }
  section.dense table { font-size: 22px; }
  section.code-detail pre { line-height: 1.3; margin: 10px 0; }
  section.code-detail pre code { font-size: 19px; }
  section.appendix h1 { font-size: 36px; }
  section.appendix { font-size: 23px; }
---

<!-- _class: cover -->

<p class="eyebrow">POSTGRESQL INTERNALS / 15 MINUTES</p>

# PostgreSQLの型変換<br>SQLからC関数まで

<ul class="small">

<li>導入</li>
<li>使える場面</li>
<li>ルールの所在</li>
<li>変換方式</li>
<li>Cの実装</li>
</ul>

<p class="small">PostgreSQL 20develで確認</p>

<!--
① 導入 / 10秒 / 累計 0:10
SQLの結果に疑問があるとき、変換前後の型、キャストの許可条件、実装の順に調べる方法を紹介します。
ソースは master / 7787aec8ab000932a8704a988b175b39ff816f2f（20devel）で確認しています。
-->

---

<p class="eyebrow">01 / 導入</p>

# `1.5` と `'1.5'` を整数にすると？

```sql
SELECT 1.5::integer;
```

```sql
SELECT '1.5'::integer;
```

<p class="lead">どちらも <strong>2</strong> になるでしょうか？</p>

<!--
① 導入 / 30秒 / 累計 0:40
5秒ほど待ち、結果を予想してもらいます。二つのSQLの違いは、1.5にシングルクォートが付いているかどうかです。
-->

---

<p class="eyebrow">01 / 導入</p>

# `1.5` は `2` に、`'1.5'` はエラーに

```sql
SELECT 1.5::integer;
-- 2

SELECT '1.5'::integer;
-- ERROR: invalid input syntax for type integer: "1.5"
```

変換前の型によって、**変換処理が異なる**。

詳しい理由は、文字列リテラルの扱いまで見てから振り返る。

> まず、型変換を要求する場面を整理しよう。

<!--
① 導入 / 20秒 / 累計 1:00
同じ::integerでも、変換前の型と使われる処理によって結果が異なります。その仕組みを調べ、最後にこの例へ戻ります。
まず、型変換を要求する場面を整理します。明示的に指定する場合以外にも、代入や式の中で変換が起きます。
-->

---

<p class="eyebrow">02 / キャストが使える3つの場面</p>

# キャストが使えるのは、どのような場面か

<div class="nest">
明示の場面：<code>CAST(x AS type)</code> / <code>x::type</code>
<div class="nest">
代入の場面：<code>INSERT</code> / <code>UPDATE</code> で列の型に合わせる
<div class="nest">
暗黙の場面：演算子・関数などが必要とする型に合わせる
</div>
</div>
</div>

**暗黙・代入・明示の順に許可範囲が広がる**

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/nodes/primnodes.h">primnodes.h</a> / CoercionContext。ここでは通常のSQLの3場面を扱う。</p>

<!--
② 3つの場面 / 50秒 / 累計 1:50
ここでは、キャストを使う場面を整理します。各キャストには、どの場面まで利用を許可するかが定められています。
暗黙の場面で使えるキャストは、代入でも明示でも使えます。代入用のキャストは明示でも使えますが、関数の引数の型を合わせる際には使えません。
内部にはPL/pgSQL専用の区分もありますが、ここでは通常のSQLの3場面を説明します。
-->

---

<p class="eyebrow">02 / キャストが使える3つの場面</p>

# 例）`bigint → integer` は代入で使える

```sql
CREATE TEMP TABLE dst (n integer);
INSERT INTO dst VALUES (42::bigint);   -- OK：代入
SELECT 42::bigint::integer;            -- OK：明示
```

```sql
SELECT chr(65::bigint);
-- ERROR: function chr(bigint) does not exist

SELECT chr(65::bigint::integer);       -- A
```

bigint → integer は暗黙には変換できないため、**chr の引数は自動で integer に変換されない**。

> どの型からどの型へ、どの場面で変換できるかは、どこに定義されている？

<!--
② 3つの場面 / 50秒 / 累計 2:40
chrは整数の文字コードに対応する文字を返す関数で、引数型はintegerです。bigintからintegerへのキャストは代入用なので、INSERTと明示キャストでは使えます。一方、chrの引数を自動でintegerに変換する際には使えません。
chr(65::bigint::integer)のように明示すると、Aが返ります。
では、どの型からどの型へ、どの場面で変換できるかは、どこに定義されているのでしょうか？
-->

---

<p class="eyebrow">03 / 型変換のルールはどこにあるか</p>

# 変換の登録は `pg_cast` にある

`pg_cast` は、型同士のキャストを登録するシステムカタログ。

| 列 | 登録されている情報 |
| --- | --- |
| `castsource` / `casttarget` | 変換前 / 変換後の型のOID |
| `castcontext` | どの場面まで使えるか |
| `castmethod` | どう変換するか |
| `castfunc` | 呼び出す変換関数のOID（関数を使う場合） |

まず **`castcontext`** を読み、前章の振る舞いを確かめる。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_cast.h">pg_cast.h</a> / FormData_pg_cast。登録を調べるSQLは付録D。</p>

<!--
③ pg_cast / 45秒 / 累計 3:25
前章ではSQLの振る舞いを見ました。ここでは、その許可条件をどこで確認できるかを調べます。pg_castには、変換前後の型、使える場面、変換方式、変換関数が登録されています。
すべての変換が個別に登録されているわけではなく、自動I/O変換などは後で扱います。
bigintとintegerは、ソースではint8とint4という名前で出てきます。
-->

---

<p class="eyebrow">03 / 型変換のルールはどこにあるか</p>

# `castcontext` で使える場面を指定する

| `castcontext` の登録 | 暗黙の場面 | 代入の場面 | 明示の場面 |
| --- | :---: | :---: | :---: |
| `i`：implicit | ✓ | ✓ | ✓ |
| `a`：assignment | — | ✓ | ✓ |
| `e`：explicit | — | — | ✓ |

`i` は **「暗黙でも利用できる」**という意味。

> どんな型同士であっても明示キャストで変換できるわけではない。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_cast.h">pg_cast.h</a> / CoercionCodes、<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / find_coercion_pathway()</p>

<!--
③ pg_cast / 50秒 / 累計 4:15
前章で整理した3つの場面は、castcontextの値で対応づけられます。行はキャストの登録内容、列は使う場面です。iは3場面すべてで、aは代入と明示で、eは明示だけで使えます。
明示キャストにも変換経路が必要です。経路があっても、値の範囲や入力形式の検査で失敗する場合があります。
-->

---

<p class="eyebrow">03 / 型変換のルールはどこにあるか</p>

# 前章の振る舞いを、登録から確認する

| source | target | castcontext | castmethod | function |
| --- | --- | :---: | :---: | --- |
| bigint | integer | `a` | `f` | `int4(bigint)` |
| integer | bigint | `i` | `f` | `int8(integer)` |

`bigint → integer` は **`a`**：代入と明示で使える。

逆方向は **`i`**：暗黙の場面でも使える。方向ごとに登録を確認する。

> `pg_cast` には変換方式もある。`castmethod = f` は何をする？

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_cast.dat">pg_cast.dat</a> / int8 → int4、int4 → int8</p>

<!--
③ pg_cast / 55秒 / 累計 5:10
bigintからintegerはaなので代入と明示で使え、逆方向はiなので暗黙の場面でも使えます。どちらも方式はfで、関数を呼びます。
integerは32ビット、bigintは64ビットです。integerのすべての値はbigintで表現できますが、逆方向では範囲に収まらない場合があります。
int4(bigint)はSQLの関数名と引数型です。Cの関数名は後で確認します。
pg_castには、使える場面に加えて、変換方式も登録されています。次はその方式を見ます。
-->

---

<p class="eyebrow">04 / 内部ではどう変換するか</p>

# `castmethod` が表す3つの変換方式

| `castmethod` | 方式 | 例 |
| --- | --- | --- |
| `f` | 変換関数を呼ぶ | bigint → integer |
| `b` | 同じ内部表現を使う | varchar → text |
| `i` | 出力関数 → 入力関数 | I/O関数で文字列として読み直す |

`castcontext` は **使える場面**、`castmethod` は **変換方式**。

<p class="small">castmethod の i は input/output。castcontext の i（implicit）とは別の意味。</p>

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_cast.h">pg_cast.h</a> / CoercionMethod、<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / coerce_type()・build_coercion_expression()</p>

<!--
④ 3方式 / 35秒 / 累計 5:45
castcontextのiはimplicit、castmethodのiはinput/outputです。同じ文字でも、列によって意味が異なります。
fは変換関数、bは内部表現の再利用、iは出力関数と入力関数による変換です。代表的な式ノードはそれぞれFuncExpr、RelabelType、CoerceViaIOです。配列の要素変換やドメインの制約検査には、これらと別の式ノードも使われます。
-->

---

<p class="eyebrow">04 / 内部ではどう変換するか</p>

# `f`：専用の関数で値を変える

<div class="flow">
<div class="card">bigint の値<br><strong>42</strong></div>
<div class="arrow">→</div>
<div class="card">変換関数<br><code>int4(bigint)</code></div>
<div class="arrow">→</div>
<div class="card">integer の値<br><strong>42</strong></div>
</div>

```sql
SELECT 42::bigint::integer;          -- 42
SELECT 2147483648::bigint::integer;  -- integer out of range
```

この変換関数では、**値の変換と範囲チェック** を行う。

<!--
④ 3方式 / 40秒 / 累計 6:25
bigintからintegerへの変換ではint4(bigint)を呼びます。この関数は、値がintegerの範囲内かを検査してから変換します。Cの実装は次章で追います。
冒頭のnumericからintegerもfですが、使う関数は異なります。
-->

---

<p class="eyebrow">04 / 内部ではどう変換するか</p>

# `b`：内部表現を変えず、別の型として扱う

<div class="flow">
<div class="card">varchar<br><strong>内部表現</strong></div>
<div class="arrow">→</div>
<div class="card">text<br><strong>同じ内部表現</strong></div>
</div>

```sql
SELECT 'hello'::varchar::text;
-- hello
```

varcharとtextは、値をメモリ上で保持する形式（内部表現）が同じ。
そのため、**データを作り直さず、そのままtextとして扱う**。変換関数を呼ぶ必要もない。

<p class="small">varchar(n) への変換では、長さ制限を適用する処理が加わる場合がある。</p>

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_cast.dat">pg_cast.dat</a> / varchar → text、<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / coerce_type()</p>

<!--
④ 3方式 / 35秒 / 累計 7:00
varcharとtextは値をメモリ上で保持する形式が同じなので、データを作り直さず、そのままtextとして扱えます。RelabelTypeは、式を変換先の型として扱うためのノードです。
varchar(n)への変換には、長さ制限を適用する処理が加わる場合があります。また、内部表現を再利用できるかどうかも、変換の方向ごとに確認が必要です。
-->

---

<p class="eyebrow">04 / 内部ではどう変換するか</p>

# `i`：文字列を出力し、変換先の型で読み直す

<div class="flow">
<div class="card">元の値</div>
<div class="arrow">→</div>
<div class="card">元の型の<br><strong>出力関数</strong></div>
<div class="arrow">→</div>
<div class="card">文字列</div>
<div class="arrow">→</div>
<div class="card">変換先の型の<br><strong>入力関数</strong></div>
</div>

```sql
SELECT '42'::text::integer;   -- 42
SELECT '1.5'::text::integer;  -- invalid input syntax
```

`textout` → 文字列 → `int4in`。**整数の入力形式として読めるか検査する**。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / build_coercion_expression()、<a href="https://github.com/postgres/postgres/blob/master/src/backend/executor/execExpr.c">execExpr.c</a> / T_CoerceViaIO、<a href="https://github.com/postgres/postgres/blob/master/src/backend/utils/adt/int.c">int.c</a> / int4in()</p>

<!--
④ 3方式 / 40秒 / 累計 7:40
元の型の出力関数がCの文字列を作り、変換先の型の入力関数が読み込みます。この途中の文字列は、SQLのtext型の値とは別です。
この例では、自動I/O変換によってtextoutとint4inが使われます。int4inは'42'を整数として読めますが、小数点を含む'1.5'は受け入れません。
ここではtext型に確定した値を変換しています。型を指定しない文字列リテラルの扱いは第6章で説明します。次に、この自動I/O変換の経路をどこで確認するかを補足します。
-->

---

<p class="eyebrow">04 / 内部ではどう変換するか</p>

# 自動I/O変換は、個別の登録がなくても使える

```sql
SELECT count(*)
FROM pg_cast
WHERE castsource = 'text'::regtype
  AND casttarget = 'integer'::regtype;
-- 0

SELECT '42'::text::integer;  -- 42：変換できる
```

`text → integer` の明示キャストには、**自動I/O変換** が使われる。

> 次は関数を使う方式を選び、SQLからCの実装まで追う。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/doc/src/sgml/catalogs.sgml">catalogs.sgml</a> / pg_cast、<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / find_coercion_pathway()</p>

<!--
④ 3方式 / 50秒 / 累計 8:30
textからintegerの行はpg_castにありませんが、明示キャストは成功します。これは、文字列型からの明示キャストに自動I/O変換が使われるためです。
変換経路はpg_castの登録に加えて、型解析のコードにある規則からも選ばれます。ほかにもドメインや配列に固有の規則があります。
3つの方式のうち、関数を使う変換を一つ選び、SQLからCの実装まで追います。
-->

---

<p class="eyebrow">05 / SQLからC関数まで追ってみる</p>

# 関数を使う方式の `bigint → integer` を追う

```sql
CREATE TEMP TABLE src (n bigint);
INSERT INTO src VALUES (42);
SELECT n::integer FROM src;
```

<div class="flow">
<div class="card">SQLの<br><strong>型解析</strong></div>
<div class="arrow">→</div>
<div class="card"><code>pg_cast</code><br>許可・方式</div>
<div class="arrow">→</div>
<div class="card"><code>pg_proc</code><br>関数の実装</div>
<div class="arrow">→</div>
<div class="card">C関数<br><code>int84()</code></div>
</div>

前章の **`f`：関数を使う方式** を、型解析から実行まで追う。

<!--
⑤ SQLからC / 35秒 / 累計 9:05
ここからは、bigintの列nをintegerへ変換する処理を調べます。定数だけの式は計画時に評価される場合があるため、列の値を使います。
型解析時にカタログを調べて変換用の式を作り、実行器に渡します。
-->

---

<!-- _class: dense -->
<p class="eyebrow">05 / SQLからC関数まで追ってみる</p>

# ① 型解析で、変換経路を選ぶ

```text
transformTypeCast()                ::integer を解析
  → coerce_to_target_type()        変換可能か確認
    → coerce_type()               変換する式を組み立てる
      → find_coercion_pathway()   pg_cast で経路を調べる
      → build_coercion_expression()
                                 FuncExpr を作る
```

`bigint → integer` は **代入・明示キャストで利用可（`a`）**。
今回は `n::integer` と明示しているため、この変換を使える。
方式は **関数 `f`** なので、呼び出しを表す `FuncExpr` を作る。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_expr.c">parse_expr.c</a> / transformTypeCast()、<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / coerce_to_target_type()・coerce_type()</p>

<!--
⑤ SQLからC / 55秒 / 累計 10:00
SQLの型を調べる型解析の段階で、キャストを適用できるか確認し、変換用の式を作ります。図では主要な呼び出しだけを示しています。
find_coercion_pathwayは、変換前後の型の組でpg_castを検索します。bigintからintegerへの変換はcastcontextがaで、代入と明示キャストで使えることを意味します。今回はn::integerと明示しているため、この登録を利用できます。方式がfなので関数のOIDを取得し、build_coercion_expressionがFuncExprを作ります。
なお、coerce_to_target_type内の変換可能性の確認でも、can_coerce_typeから経路を調べます。
-->

---

<!-- _class: dense -->
<p class="eyebrow">05 / SQLからC関数まで追ってみる</p>

# ② `pg_proc` でC関数名を確認する

```sql
SELECT c.castfunc::regprocedure AS sql_function,
       l.lanname, p.prosrc
FROM pg_cast AS c
JOIN pg_proc AS p ON p.oid = c.castfunc
JOIN pg_language AS l ON l.oid = p.prolang
WHERE c.castsource = 'bigint'::regtype
  AND c.casttarget = 'integer'::regtype;
```

| sql_function | lanname | prosrc |
| --- | --- | --- |
| `int4(bigint)` | `internal` | `int84` |

SQLの関数名は `int4`、Cの関数名は **`int84`**。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_proc.dat">pg_proc.dat</a> / int4(bigint)。prosrcの意味は関数の言語によって異なる。</p>

<!--
⑤ SQLからC / 45秒 / 累計 10:45
pg_castのcastfuncとpg_procのoidを結合すると、prosrcにint84が見つかります。この関数の言語はinternalで、prosrcは組み込みの実装を示します。
int8.cでint84を検索すると、C関数が見つかります。int8からint4への変換なのでint84、という名前です。prosrcの意味は言語によって異なります。
-->

---

<!-- _class: dense code-detail -->
<p class="eyebrow">05 / SQLからC関数まで追ってみる</p>

# ③ `int84()` が範囲を検査し、integerに変換する

```c
Datum
int84(PG_FUNCTION_ARGS)
{
    int64 arg = PG_GETARG_INT64(0);

    if (unlikely(arg < PG_INT32_MIN) || unlikely(arg > PG_INT32_MAX))
        ereturn(fcinfo->context, (Datum) 0,
                (errcode(ERRCODE_NUMERIC_VALUE_OUT_OF_RANGE),
                 errmsg("integer out of range")));

    PG_RETURN_INT32((int32) arg);
}
```

integerの範囲は **−2,147,483,648 ～ 2,147,483,647**。

<p class="source"><a href="https://github.com/postgres/postgres/blob/master/src/backend/utils/adt/int8.c">int8.c</a> / int84()。空白を調整して掲載。</p>

<!--
⑤ SQLからC / 65秒 / 累計 11:50
PG_GETARG_INT64で引数を取り出し、32ビット整数の最小値・最大値と比較します。範囲内なら、int32に変換して返します。
範囲外では、通常のSELECTはinteger out of rangeで失敗します。ereturnの引数にある0がSQLの結果になるわけではありません。
-->

---

<p class="eyebrow">05 / SQLからC関数まで追ってみる</p>

# ④ 実行時に `int84()` を呼ぶ

<div class="flow">
<div class="card">列 <code>n</code> の値<br><strong>bigint</strong></div>
<div class="arrow">→</div>
<div class="card"><code>FuncExpr</code><br>関数OIDを保持</div>
<div class="arrow">→</div>
<div class="card"><code>int84()</code><br>値を検査・変換</div>
</div>

型解析で **変換用の式を作り**、実行時に **列の値を変換する**。

<p class="small">定数だけの式は、計画時の定数畳み込みで先に評価されることもある。</p>

> では、型を指定していない文字列リテラルはどう扱われる？

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/backend/executor/execExpr.c">execExpr.c</a> / ExecInitFunc、<a href="https://github.com/postgres/postgres/blob/master/src/backend/executor/execExprInterp.c">execExprInterp.c</a> / EEOP_FUNCEXPR_STRICT_1</p>

<!--
⑤ SQLからC / 40秒 / 累計 12:30
実行器はFuncExprを基に呼び出しを準備し、列nの値をint84に渡します。int84はstrict関数なので、実行器はNULL入力のときに呼び出しを省き、NULLを返します。
定数だけの式は計画時に評価される場合があります。図では、列の値を通常の式評価器で処理する場合を示しています。
ここまでは変換前の型が決まっている値の変換を追いました。では、型を指定していない文字列リテラルはどう扱われるでしょうか？
-->

---

<p class="eyebrow">06 / 文字列リテラルの落とし穴</p>

# `'42'` は、最初から `text` ではない

```sql
SELECT pg_typeof('42');        -- unknown
SELECT pg_typeof('42'::text);  -- text

SELECT chr('65');              -- A
SELECT chr('65'::text);        -- function chr(text) does not exist
```

型を指定しない文字列リテラルは、最初は **`unknown`**。
`chr('65')` では、引数型の **integer の入力関数** で読み込まれる。

<p class="small">text → integer のI/O変換とは、出発点が異なる。</p>

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/doc/src/sgml/typeconv.sgml">typeconv.sgml</a> / 文字列リテラル、<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / coerce_type()</p>

<!--
⑥ 文字列リテラルの落とし穴 / 60秒 / 累計 13:30
型を指定しない文字列リテラルには、最初はunknownという仮の型が付きます。chr('65')では引数型のintegerに決まり、integerの入力関数で65を読み込みます。
'65'::textではすでにtext型が確定しています。chrへ渡すにはtextからintegerへの暗黙キャストが必要ですが、それがないため失敗します。
なお、SELECT '42'のように出力列に型未確定のリテラルが残った場合は、textに解決されます。
-->

---

<!-- _class: dense -->
<p class="eyebrow">06 / 文字列リテラルの落とし穴</p>

# 数値の変換と、文字列の読み込みは処理が違う

| SQL | 主な経路 | 結果 |
| --- | --- | --- |
| `1.5::integer` | numeric → 変換関数 → integer | `2` |
| `'1.5'::integer` | unknownのリテラル → `int4in` | エラー |
| `'1.5'::text::integer` | text → I/O変換 → `int4in` | エラー |
| `'1.5'::numeric::integer` | `numeric_in` → 数値の変換関数 | `2` |

**数値を丸める処理** と **文字列を整数として読む処理** は別。

> 冒頭の違いを説明できた。最後に、型変換を調べる手順を整理しよう。

<p class="source">根拠：<a href="https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c">parse_coerce.c</a> / coerce_type()、<a href="https://github.com/postgres/postgres/blob/master/src/backend/utils/adt/int.c">int.c</a> / int4in()、<a href="https://github.com/postgres/postgres/blob/master/src/backend/utils/adt/numeric.c">numeric.c</a> / numeric_int4()</p>

<!--
⑥ 文字列リテラルの落とし穴 / 60秒 / 累計 14:30
冒頭の1.5はnumeric型で、integerへの変換関数が値を丸めます。一方、'1.5'::integerでは整数の入力関数int4inが文字列を読むため、小数点のところで失敗します。
'1.5'::numeric::integerなら、まずnumericの入力関数で読み込み、その数値をintegerへ変換するので2になります。
冒頭の結果の違いを説明できたので、型変換を調べる手順として整理します。
-->

---

<!-- _class: finish -->
<p class="eyebrow">07 / まとめ</p>

# 型変換を調べる手順

1. **変換前と変換後の型** を確認する
2. **暗黙・代入・明示** のどの場面かを確認する
3. **`pg_cast` と型解析の規則** で許可条件・方式を調べる
4. 方式に応じて、**変換関数・入出力関数や関連処理の実装** を読む

<p class="small">型未指定の文字列リテラルは unknown。<br>pg_castに登録がない変換には、自動I/O変換などの規則もある。</p>

<!--
⑦ まとめ / 30秒 / 累計 15:00
まず変換前後の型と、暗黙・代入・明示のどの場面かを確認します。次にpg_castの登録と型解析の規則を調べ、方式に応じた実装を読みます。
bigintからintegerの例では、castcontextはa、castmethodはf、SQLの関数はint4(bigint)、Cの実装はint84でした。
本編はここまでです。付録は質疑用で、15分に含みません。
-->

---

<!-- _class: appendix -->
<p class="eyebrow">APPENDIX A / 参照先</p>

# 参考文献・ソースコード

- [CREATE CAST：許可・3方式・自動I/O変換](https://www.postgresql.org/docs/devel/sql-createcast.html)
- [pg_cast：各列と、登録されない変換](https://www.postgresql.org/docs/18/catalog-pg-cast.html)
- [Type Conversion：文字列リテラルとunknown](https://www.postgresql.org/docs/18/typeconv-overview.html)
- [parse_coerce.c：型変換経路の選択・式の生成](https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c)
- [int8.c：int84()](https://github.com/postgres/postgres/blob/master/src/backend/utils/adt/int8.c)

<p class="small">実装の確認対象：<code>master / 7787aec8ab</code>（20devel）<br>リンク先はGitHubの master ブランチ。SQLの実行条件は同梱READMEに記載。</p>

<!--
付録 / 本編の時間外
公式文書と、PostgreSQL公式GitHubのmasterブランチへのリンクです。
-->

---

<!-- _class: appendix dense -->
<p class="eyebrow">APPENDIX B / 方式をカタログで比較</p>

# 同じクエリで `f` と `b` を見比べる

```sql
SELECT castsource::regtype, casttarget::regtype,
       castcontext, castmethod, castfunc::regprocedure
FROM pg_cast
WHERE (castsource = 'bigint'::regtype
       AND casttarget = 'integer'::regtype)
   OR (castsource = 'varchar'::regtype
       AND casttarget = 'text'::regtype);
```

| 方向 | context | method | func |
| --- | :---: | :---: | --- |
| bigint → integer | `a` | `f` | `int4(bigint)` |
| varchar → text | `i` | `b` | `-`（OID 0） |

<p class="small">自動I/O変換には <code>pg_cast</code> の行がない場合がある。<code>castfunc = 0</code> だけで方式を判断しない。</p>

<!--
付録 / 本編の時間外
bigintからintegerはf、varcharからtextはbです。変換関数を使わない場合、castfuncは0になります。
登録されたI/O変換でもcastfuncは0なので、方式の判別にはcastmethodを使います。自動I/O変換の場合は、pg_castの行自体がないこともあります。
-->

---

<!-- _class: appendix -->
<p class="eyebrow">APPENDIX C / ソースの検索</p>

# 関連する関数をソースから探す

```sh
rg -n 'transformTypeCast' src/backend/parser/parse_expr.c
rg -n 'find_coercion_pathway' src/backend/parser/parse_coerce.c
rg -n "prosrc => 'int84'" src/include/catalog/pg_proc.dat
rg -n 'int84\(PG_FUNCTION_ARGS\)' src/backend/utils/adt/int8.c
```

| 確認したいこと | ファイル・関数 |
| --- | --- |
| キャストの定義 | [src/include/catalog/pg_cast.dat](https://github.com/postgres/postgres/blob/master/src/include/catalog/pg_cast.dat) |
| unknownの定数の解釈 | [parse_coerce.c の coerce_type()](https://github.com/postgres/postgres/blob/master/src/backend/parser/parse_coerce.c) |
| integerの入力形式 | [src/backend/utils/adt/int.c の int4in()](https://github.com/postgres/postgres/blob/master/src/backend/utils/adt/int.c) |

<!--
付録 / 本編の時間外
行番号は版によって変わるため、関数名で検索します。見つけた関数の呼び出し元・呼び出し先を確認すると、SQLから実装までの処理を追えます。
-->

---

<!-- _class: appendix dense -->
<p class="eyebrow">APPENDIX D / キャストの登録を調べる</p>

# 型名と関数名で `pg_cast` を読む

```sql
SELECT castsource::regtype AS source,
       casttarget::regtype AS target,
       castcontext, castmethod,
       castfunc::regprocedure AS function
FROM pg_cast
WHERE (castsource = 'bigint'::regtype
       AND casttarget = 'integer'::regtype)
   OR (castsource = 'integer'::regtype
       AND casttarget = 'bigint'::regtype)
ORDER BY castsource::regtype::text;
```

`regtype` は型名、`regprocedure` は関数名と引数型を表示する。

<!--
付録 / 本編の時間外
第3章の表を取得するSQLです。castsourceとcasttargetには型のOID、castfuncには関数のOIDが入っています。
regtypeで型名に、regprocedureでSQLの関数名と引数型に変えて表示します。Cの関数名は第5章のようにpg_procで確認します。
-->
