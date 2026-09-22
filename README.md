# Morning feed

A tiny self-hosted RSS reader. A scheduled GitHub Action fetches a few feeds
each morning, renders a single `index.html`, and publishes it to GitHub Pages.
You bookmark one URL and check it anywhere.

## What it tracks

- Simon Willison — Agentic Engineering Patterns (`/tags/agentic-engineering.atom`)
- Simon Willison — Blog, everything (`/atom/everything/`)
- Latent Space
- Ahead of AI (Sebastian Raschka)

Edit the `FEEDS` list at the top of `build.py` to change any of this.

## Running locally (optional)

```bash
pip install feedparser
python build.py
open index.html   # or just open the file in a browser
```

## Changing the schedule

The `cron` line in `.github/workflows/build.yml` is in **UTC**. `0 5 * * *`
is 05:00 UTC (≈ 07:00 Madrid in summer, 06:00 in winter). Change the numbers
to move it. You can also hit **Run workflow** any time for an on-demand refresh.

## Notes

- A broken or moved feed shows an inline error line for that source only; it
  never takes down the rest of the page.
- The page is fully static and self-contained (one HTML file, inline CSS),
  respects your system light/dark setting, and reads fine on a phone.
- No state is stored — each run regenerates the page from the live feeds, so
  it always reflects the current latest posts.
