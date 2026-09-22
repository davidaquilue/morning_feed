#!/usr/bin/env python3
"""
Morning feed builder.

Fetches a handful of RSS/Atom feeds and writes a single static index.html
showing the latest posts from each, grouped by source. No database, no state:
every run regenerates the page from scratch. Designed to run in GitHub Actions
and publish to GitHub Pages, but also runs fine locally (`python build.py`).
"""

import datetime
import html
import sys
import time

import feedparser

# ---------------------------------------------------------------------------
# Configuration — edit this list to add/remove/reorder sources.
#   name:      label shown as the section heading
#   url:       the RSS/Atom feed URL
#   max_items: how many recent posts to show from this source
# ---------------------------------------------------------------------------
FEEDS = [
    {
        "name": "ALZFORUM (All)",
        "url": "http://feeds.feedburner.com/alzforum/PpcR",
        "max_items": 6,
    },
    {
        "name": "ALZFORUM (Papers of the Week)",
        "url": "http://feeds.feedburner.com/alzforum/PpcR",
        "max_items": 6,
    },
    {
        "name": "Simon Willison — Blog (everything)",
        "url": "https://simonwillison.net/atom/everything/",
        "max_items": 6,
    },
    {
        "name": "Latent Space",
        "url": "https://www.latent.space/feed",
        "max_items": 6,
    },
    {
        "name": "Ahead of AI — Sebastian Raschka",
        "url": "https://magazine.sebastianraschka.com/feed",
        "max_items": 6,
    },
    {
        "name": "Simon Willison — Agentic Engineering Patterns",
        "url": "https://simonwillison.net/tags/agentic-engineering.atom",
        "max_items": 8,
    },
]

# A browser-like User-Agent; some hosts reject the default feedparser agent.
USER_AGENT = "morning-feed/1.0 (+https://github.com; personal RSS reader)"

# Favicon: brain + circuit-node mark, embedded inline as a data URI so there's
# no separate file to host. Shows in the browser tab and next to bookmarks.
FAVICON = (
    "data:image/svg+xml;base64,"
    "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA2NCA2NCI+PHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iMTQiIGZpbGw9IiMxYTRmYTAiLz48cGF0aCBkPSJNMzIgMTNjLTUuNSAwLTkgMy4yLTkuMyA3LjJjLTMuNCAwLjYtNS43IDMuMS01LjcgNi4zYzAgMS44IDAuOCAzLjQgMiA0LjZjLTEuMiAxLjEtMiAyLjctMiA0LjVjMCAzLjQgMi43IDYuMSA2LjQgNi4zYzAuNiAzLjMgMy45IDUuOCA4LjYgNS44WiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZWFmMWZiIiBzdHJva2Utd2lkdGg9IjIuNCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PHBhdGggZD0iTTMyIDEzYzUuNSAwIDkgMy4yIDkuMyA3LjJjMy40IDAuNiA1LjcgMy4xIDUuNyA2LjNjMCAxLjgtMC44IDMuNC0yIDQuNmMxLjIgMS4xIDIgMi43IDIgNC41YzAgMy40LTIuNyA2LjEtNi40IDYuM2MtMC42IDMuMy0zLjkgNS44LTguNiA1LjhaIiBmaWxsPSJub25lIiBzdHJva2U9IiNlYWYxZmIiIHN0cm9rZS13aWR0aD0iMi40IiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz48bGluZSB4MT0iMzIiIHkxPSIxMyIgeDI9IjMyIiB5Mj0iNDcuOCIgc3Ryb2tlPSIjZWFmMWZiIiBzdHJva2Utd2lkdGg9IjIuNCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+PGNpcmNsZSBjeD0iMjQiIGN5PSIyNCIgcj0iMi40IiBmaWxsPSIjN2ZkNGZmIi8+PGNpcmNsZSBjeD0iNDAiIGN5PSIzMCIgcj0iMi40IiBmaWxsPSIjN2ZkNGZmIi8+PGNpcmNsZSBjeD0iMjUiIGN5PSIzOCIgcj0iMi40IiBmaWxsPSIjN2ZkNGZmIi8+PGxpbmUgeDE9IjI0IiB5MT0iMjQiIHgyPSI0MCIgeTI9IjMwIiBzdHJva2U9IiM3ZmQ0ZmYiIHN0cm9rZS13aWR0aD0iMS40IiBvcGFjaXR5PSIwLjc1Ii8+PGxpbmUgeDE9IjQwIiB5MT0iMzAiIHgyPSIyNSIgeTI9IjM4IiBzdHJva2U9IiM3ZmQ0ZmYiIHN0cm9rZS13aWR0aD0iMS40IiBvcGFjaXR5PSIwLjc1Ii8+PC9zdmc+Cg=="
)


def entry_datetime(entry):
    """Return a sortable datetime for an entry, or a very old date if missing."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime.datetime.fromtimestamp(time.mktime(parsed))
            except (OverflowError, ValueError):
                pass
    return datetime.datetime.min


def fetch_feed(feed):
    """
    Fetch and parse one feed. Returns (title, items, error).
    On failure, error is a human-readable string and items is empty — the page
    shows this inline so a single broken feed never takes down the whole page.
    """
    try:
        parsed = feedparser.parse(feed["url"], agent=USER_AGENT)
    except Exception as exc:  # noqa: BLE001 - want to surface any failure
        return feed["name"], [], f"Could not fetch feed: {exc}"

    # feedparser sets .bozo on malformed feeds but often still returns entries;
    # only treat it as fatal if we got nothing usable back.
    if not parsed.entries:
        reason = ""
        if getattr(parsed, "bozo", 0) and getattr(parsed, "bozo_exception", None):
            reason = f" ({parsed.bozo_exception})"
        status = getattr(parsed, "status", None)
        if status and status >= 400:
            reason = f" (HTTP {status}){reason}"
        return feed["name"], [], f"No entries returned{reason}"

    entries = sorted(parsed.entries, key=entry_datetime, reverse=True)
    items = []
    for entry in entries[: feed["max_items"]]:
        dt = entry_datetime(entry)
        items.append(
            {
                "title": entry.get("title", "(untitled)").strip(),
                "link": entry.get("link", "#"),
                "date": dt.strftime("%Y-%m-%d") if dt != datetime.datetime.min else "",
            }
        )
    return feed["name"], items, None


def render(sections, built_at):
    """Render the full HTML page from the fetched sections."""
    parts = []
    for name, items, error in sections:
        parts.append('    <section class="feed">')
        parts.append(f"      <h2>{html.escape(name)}</h2>")
        if error:
            parts.append(f'      <p class="error">{html.escape(error)}</p>')
        else:
            parts.append("      <ul>")
            for item in items:
                title = html.escape(item["title"])
                link = html.escape(item["link"], quote=True)
                date = html.escape(item["date"])
                date_span = f'<span class="date">{date}</span>' if date else ""
                parts.append(
                    f'        <li>{date_span}'
                    f'<a href="{link}" target="_blank" rel="noopener">{title}</a></li>'
                )
            parts.append("      </ul>")
        parts.append("    </section>")
    sections_html = "\n".join(parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Morning feed</title>
<link rel="icon" href="{FAVICON}">
<link rel="apple-touch-icon" href="{FAVICON}">
<style>
  :root {{
    color-scheme: light dark;
    --bg: #fbfbf9; --fg: #1a1a1a; --muted: #777; --line: #e4e4e0;
    --link: #1a4fa0; --accent: #b03a2e; --card: #ffffff;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #16171a; --fg: #e8e8e6; --muted: #8a8a8a; --line: #2c2e33;
      --link: #7fb0ff; --accent: #e0857a; --card: #1d1f23;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--fg);
    font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 720px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
  header {{ border-bottom: 2px solid var(--line); padding-bottom: 1rem; margin-bottom: 1.5rem; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 .25rem; }}
  .built {{ color: var(--muted); font-size: .8rem; }}
  .feed {{ background: var(--card); border: 1px solid var(--line); border-radius: 10px;
           padding: 1rem 1.25rem; margin-bottom: 1.25rem; }}
  .feed h2 {{ font-size: 1.02rem; margin: 0 0 .6rem; color: var(--accent); }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ padding: .35rem 0; border-top: 1px solid var(--line); }}
  li:first-child {{ border-top: none; }}
  .date {{ color: var(--muted); font-variant-numeric: tabular-nums; font-size: .8rem;
           margin-right: .6rem; }}
  a {{ color: var(--link); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .error {{ color: var(--accent); font-size: .85rem; margin: .3rem 0 0; font-style: italic; }}
  footer {{ color: var(--muted); font-size: .78rem; text-align: center; margin-top: 2rem; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>Morning feed</h1>
      <div class="built">Rebuilt {built_at}</div>
    </header>
{sections_html}
    <footer>Regenerated daily from source RSS/Atom feeds.</footer>
  </div>
</body>
</html>
"""


def main():
    sections = [fetch_feed(feed) for feed in FEEDS]
    built_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    page = render(sections, built_at)
    with open("index.html", "w", encoding="utf-8") as fh:
        fh.write(page)

    # Log a small summary so the Actions run is easy to eyeball.
    for name, items, error in sections:
        status = f"ERROR: {error}" if error else f"{len(items)} items"
        print(f"  {name}: {status}")
    print(f"Wrote index.html at {built_at}")

    # Never fail the build over one bad feed — the page already shows the error.
    return 0


if __name__ == "__main__":
    sys.exit(main())
