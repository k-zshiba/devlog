前日のソフトウェア関連ニュースダイジェストを生成します。

以下の手順を実行してください:

1. 依存パッケージが未インストールの場合はインストールする:
   ```
   source venv/bin/activate && pip3 install -r requirements.txt -q
   ```

2. ダイジェスト生成スクリプトを実行する:
   ```
   python3 scripts/generate_digest.py
   ```

3. 生成されたMarkdownファイル（`digests/YYYY-MM-DD.md`）の内容を読み込み、ユーザーに概要を報告する。

4. 生成に失敗した場合は、エラーメッセージを確認してユーザーに原因を説明する。
   - `ANTHROPIC_API_KEY` が未設定の場合はその旨を伝える
   - ネットワークエラーの場合はその旨を伝える
