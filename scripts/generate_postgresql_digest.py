#!/usr/bin/env python3
"""Generate a daily PostgreSQL digest from HN, git commits, and mailing list discussions."""

import os
import re
import sys
import subprocess
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from generate_digest import get_target_date, build_stories_text

ALGOLIA_HN_URL = "https://hn.algolia.com/api/v1/search_by_date"
GITHUB_COMMITS_URL = "https://api.github.com/repos/postgres/postgres/commits"
HN_LIMIT = 30
COMMITS_LIMIT = 50
THREAD_CHAR_LIMIT = 2000


def fetch_hn_stories(date: datetime) -> list[dict]:
    start_ts = int(date.timestamp())
    params = {
        "query": "postgresql postgres",
        "tags": "story",
        "numericFilters": f"created_at_i>{start_ts},created_at_i<{start_ts + 86400}",
        "hitsPerPage": HN_LIMIT,
        "attributesToRetrieve": "title,url,points,num_comments,objectID",
    }
    resp = requests.get(ALGOLIA_HN_URL, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    return sorted(hits, key=lambda x: x.get("points", 0), reverse=True)


def fetch_pg_commits(date: datetime) -> list[dict]:
    date_str = date.strftime("%Y-%m-%d")
    params = {
        "since": f"{date_str}T00:00:00Z",
        "until": f"{date_str}T23:59:59Z",
        "per_page": COMMITS_LIMIT,
    }
    resp = requests.get(
        GITHUB_COMMITS_URL,
        params=params,
        headers={"Accept": "application/vnd.github.v3+json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def extract_discussion_urls(commit_message: str) -> list[str]:
    return re.findall(r"Discussion:\s*(https?://\S+)", commit_message)


def fetch_thread_text(url: str) -> str | None:
    """Fetch mailing list thread text from a postgr.es or postgresql.org URL."""
    try:
        resp = requests.get(url, timeout=10, allow_redirects=True)
        final_url = resp.url

        # Convert to flat thread view on postgresql.org
        if "message-id" in final_url and "/flat/" not in final_url:
            msg_id = final_url.split("message-id/")[-1].strip("/")
            flat_url = f"https://www.postgresql.org/message-id/flat/{msg_id}"
            resp = requests.get(flat_url, timeout=10)

        # Extract <pre> blocks which contain email bodies in the archive
        pre_blocks = re.findall(r"<pre[^>]*>(.*?)</pre>", resp.text, re.DOTALL)
        if not pre_blocks:
            return None

        text = "\n\n---\n\n".join(
            re.sub(r"<[^>]+>", "", block).strip() for block in pre_blocks[:3]
        )
        return text[:THREAD_CHAR_LIMIT]
    except Exception:
        return None


def build_commits_section(commits: list[dict]) -> str:
    """Build text with commit summaries and fetched discussion threads."""
    if not commits:
        return "（この日のコミットはありません）"

    parts = []
    seen_urls: set[str] = set()

    for c in commits:
        message = c["commit"]["message"]
        subject = message.split("\n")[0]
        author = c["commit"]["author"]["name"]
        url = c["html_url"]
        sha = c["sha"][:8]

        # Full commit message body (useful for Claude)
        body = message[len(subject):].strip()

        section = f"### [{subject}]({url})\nAuthor: {author} ({sha})\n"
        if body:
            section += f"\n{body[:500]}\n"

        # Fetch mailing list discussion if linked
        discussion_urls = extract_discussion_urls(message)
        for disc_url in discussion_urls:
            if disc_url in seen_urls:
                continue
            seen_urls.add(disc_url)
            print(f"  Fetching discussion: {disc_url}")
            thread_text = fetch_thread_text(disc_url)
            if thread_text:
                section += f"\n**メーリングリスト議論** ({disc_url}):\n```\n{thread_text}\n```\n"

        parts.append(section)

    return "\n\n".join(parts)


def generate_digest(
    hn_stories: list[dict],
    commits: list[dict],
    commits_section: str,
    date: datetime,
) -> str:
    date_ja = date.strftime("%Y年%m月%d日")
    date_str = date.strftime("%Y-%m-%d")

    hn_text = build_stories_text(hn_stories) if hn_stories else "（この日のHNストーリーはありません）"

    system = (
        "あなたは優秀なPostgreSQLエキスパートです。"
        "Hacker News、GitHubコミット、メーリングリスト議論をもとに"
        "PostgreSQL開発者・運用者向けのニュースダイジェストを日本語で作成します。"
    )

    user_prompt = f"""{date_ja}のPostgreSQLに関するニュースダイジェストを作成してください。

## 要件
- タイトルは `# {date_str} PostgreSQL ニュースダイジェスト` とする
- 以下の3つのセクションで構成する:
  1. **コミット** — その日のコミット内容と、メーリングリストでの背景議論をまとめる
  2. **HN ニュース** — Hacker News上のPostgreSQL関連ストーリーをまとめる
  3. **まとめ** — 当日の注目ポイントを2〜3文で総括する
- 各項目に1〜2文の日本語説明を追加する
- 特に重要度の高いものには ⭐ を付ける
- 末尾に「本ダイジェストはHacker News・GitHub・PostgreSQLメーリングリストの情報を元にClaude AIが生成しました。」と記載する

## コミット（{len(commits)}件）

{commits_section}

## HN ストーリー

{hn_text}
"""

    result = subprocess.run(
        ["claude", "-p", user_prompt, "--system-prompt", system],
        capture_output=True,
        text=True,
        timeout=180,
    )

    if result.returncode != 0:
        raise RuntimeError(f"claude CLI error: {result.stderr.strip()}")

    return result.stdout.strip()


def save_digest(content: str, date: datetime) -> str:
    filename = f"digests/postgresql/{date.strftime('%Y-%m-%d')}.md"
    os.makedirs("digests/postgresql", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    return filename


def update_index(date: datetime) -> None:
    index_path = "digests/postgresql/index.md"
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

    header = "# PostgreSQL News Digest\n\nHacker News・GitHub・メーリングリストをもとに毎日自動生成されるPostgreSQL向けニュースダイジェストです。\n\n"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(entries) + "\n")


def main() -> None:
    if len(sys.argv) > 1:
        try:
            date = datetime.strptime(sys.argv[1], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"Invalid date format: {sys.argv[1]}. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
    else:
        date = get_target_date(offset_days=1)

    date_str = date.strftime("%Y-%m-%d")
    print(f"Fetching data for {date_str}...")

    print("  [1/3] Fetching HN stories...")
    hn_stories = fetch_hn_stories(date)
    print(f"        Found {len(hn_stories)} HN stories.")

    print("  [2/3] Fetching PostgreSQL commits...")
    commits = fetch_pg_commits(date)
    print(f"        Found {len(commits)} commits.")

    if not hn_stories and not commits:
        print("No data found for the target date.", file=sys.stderr)
        sys.exit(1)

    print("  [3/3] Fetching mailing list discussions...")
    commits_section = build_commits_section(commits)

    print("Generating digest with Claude...")
    digest = generate_digest(hn_stories, commits, commits_section, date)

    output_file = save_digest(digest, date)
    update_index(date)

    print(f"Digest saved to: {output_file}")
    print("Index updated: digests/postgresql/index.md")


if __name__ == "__main__":
    main()
