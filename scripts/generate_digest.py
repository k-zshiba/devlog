#!/usr/bin/env python3
"""Generate a daily software news digest from Hacker News using Claude."""

import os
import sys
import subprocess
import requests
from datetime import datetime, timedelta, timezone

ALGOLIA_HN_URL = "https://hn.algolia.com/api/v1/search_by_date"
STORIES_LIMIT = 60


def get_target_date(offset_days: int = 1) -> datetime:
    return (datetime.now(timezone.utc) - timedelta(days=offset_days)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def fetch_hn_stories(date: datetime) -> list[dict]:
    start_ts = int(date.timestamp())
    end_ts = start_ts + 86400  # +24h

    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
        "hitsPerPage": STORIES_LIMIT,
        "attributesToRetrieve": "title,url,points,num_comments,objectID",
    }

    resp = requests.get(ALGOLIA_HN_URL, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return sorted(hits, key=lambda x: x.get("points", 0), reverse=True)


def build_stories_text(stories: list[dict]) -> str:
    lines = []
    for s in stories:
        url = s.get("url") or f"https://news.ycombinator.com/item?id={s['objectID']}"
        lines.append(
            f"- [{s['title']}]({url}) "
            f"(score: {s.get('points', 0)}, comments: {s.get('num_comments', 0)})"
        )
    return "\n".join(lines)


def generate_digest(stories: list[dict], date: datetime) -> str:
    date_ja = date.strftime("%Y年%m月%d日")
    date_str = date.strftime("%Y-%m-%d")
    stories_text = build_stories_text(stories)

    system = (
        "あなたは優秀なテックジャーナリストです。"
        "Hacker Newsのストーリーをもとに、日本語でソフトウェア開発者向けのニュースダイジェストを作成します。"
        "ソフトウェア開発・プログラミング・AI・セキュリティ・インフラに関連するものを優先し、"
        "各カテゴリに簡潔な日本語の説明を付けてください。"
    )

    user_prompt = f"""{date_ja}のHacker Newsトップストーリーから、ソフトウェア関連ニュースのダイジェストを作成してください。

## 要件
- タイトルは `# {date_str} ソフトウェアニュースダイジェスト` とする
- カテゴリ別に整理する（例: AI/ML, セキュリティ, 言語/ツール, インフラ/クラウド, その他）
- 各記事に1〜2文の日本語説明を追加する
- 特に重要度の高い記事には ⭐ を付ける
- 末尾に「本ダイジェストはHacker Newsの情報を元にClaude AIが生成しました。」と記載する

## ストーリー一覧
{stories_text}
"""

    result = subprocess.run(
        ["claude", "-p", user_prompt, "--system-prompt", system],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")

    return result.stdout.strip()


def save_digest(content: str, date: datetime) -> str:
    filename = f"digests/{date.strftime('%Y-%m-%d')}.md"
    os.makedirs("digests", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def update_index(date: datetime) -> None:
    index_path = "digests/index.md"
    date_str = date.strftime("%Y-%m-%d")
    new_entry = f"- [{date_str}](./{date_str}.md)"

    entries: list[str] = []
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("- [") and line != new_entry:
                    entries.append(line)

    entries.insert(0, new_entry)

    header = "# Daily Dev News Digest\n\nHacker Newsをもとに毎日自動生成されるソフトウェア開発者向けニュースダイジェストです。\n\n"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(entries) + "\n")


def main() -> None:
    date = get_target_date(offset_days=1)
    print(f"Fetching Hacker News stories for {date.strftime('%Y-%m-%d')}...")

    stories = fetch_hn_stories(date)
    if not stories:
        print("No stories found for the target date.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(stories)} stories. Generating digest with Claude...")
    digest = generate_digest(stories, date)

    output_file = save_digest(digest, date)
    update_index(date)

    print(f"Digest saved to: {output_file}")
    print("Index updated: digests/index.md")


if __name__ == "__main__":
    main()
