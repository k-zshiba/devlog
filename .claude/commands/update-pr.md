dev ブランチの open な Pull Request のタイトルと本文を、現在の差分に合わせて更新します。

以下の手順を実行してください:

1. `gh` コマンドの存在を確認し、なければインストールする:
   ```
   which gh || (command -v apt && sudo apt install -y gh || sudo dnf install -y gh)
   ```
   インストールにも失敗した場合はその旨をユーザーに伝えて中断する。

2. 現在のブランチが dev であることを確認する:
   ```
   git branch --show-current
   ```
   dev でない場合はその旨をユーザーに伝えて中断する。

3. dev → main の open な PR を確認する:
   ```
   gh pr list --base main --head dev --state open
   ```
   PR が存在しない場合はその旨をユーザーに伝えて中断する。

4. origin/main と origin/dev の差分コミットを確認する:
   ```
   git log origin/main..origin/dev --oneline
   ```

5. 差分ファイルを確認する:
   ```
   git diff origin/main...origin/dev --stat
   ```

6. コミット一覧と差分をもとに新しい PR タイトルと本文を作成して、`gh api` で更新する:
   ```
   gh api repos/{owner}/{repo}/pulls/<PR番号> --method PATCH -f title="<タイトル>" -f body="<本文>"
   ```
   `{owner}` と `{repo}` は `gh repo view --json owner,name` で取得する。
   - タイトルは 70 文字以内で変更内容を簡潔に表す
   - 本文には変更内容の箇条書きサマリーを含める

7. 更新された PR の URL をユーザーに報告する。
