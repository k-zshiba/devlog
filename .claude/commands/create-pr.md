dev ブランチから main ブランチへの Pull Request を作成します。

以下の手順を実行してください:

1. `gh` コマンドの存在を確認し、なければインストールする:
   ```
   which gh || (type -f "$(command -v apt)" && sudo apt install -y gh || sudo dnf install -y gh)
   ```
   インストールにも失敗した場合はその旨をユーザーに伝えて中断する。

2. 現在のブランチが dev であることを確認する:
   ```
   git branch --show-current
   ```
   dev でない場合はその旨をユーザーに伝えて中断する。

3. dev と main の差分コミットを確認する:
   ```
   git log main..dev --oneline
   ```

4. 差分ファイルを確認する:
   ```
   git diff main...dev --stat
   ```

5. コミット一覧と差分をもとに PR のタイトルと本文を作成して、`gh pr create` で Pull Request を作成する:
   ```
   gh pr create --base main --head dev --title "<タイトル>" --body "<本文>"
   ```
   - タイトルは 70 文字以内で変更内容を簡潔に表す
   - 本文には変更内容の箇条書きサマリーを含める

6. 作成された PR の URL をユーザーに報告する。
