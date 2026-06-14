# CUPL RSC Notice Watch

[中文说明](README.zh-CN.md)

An unofficial daily archive and static dashboard for public notices from the Human Resources Office of China University of Political Science and Law.

![Dashboard demo](assets/demo.svg)

## What It Tracks

- Site: China University of Political Science and Law Human Resources Office
- Base URL: `https://rsc.cupl.edu.cn/`
- Notice URL: `https://rsc.cupl.edu.cn/tzgg.htm`
- Sections: notices, recruitment information, and personnel policies
- Fields: title, date, URL, section, source page, first seen time, last seen time

This project only collects publicly visible web pages. It is not affiliated with or endorsed by China University of Political Science and Law.

## Quick Start

```bash
python3 scraper.py 3
python3 -m http.server 8000
```

Open `http://localhost:8000` to view the dashboard.

## Data Files

- `data/notices.json`: merged historical notices
- `data/notices.csv`: spreadsheet-friendly export
- `data/history/YYYY-MM-DD.json`: notices fetched in a single run
- `data/meta.json`: site metadata, update time, section list, total count

Repeated runs merge by notice URL hash, so existing history is kept and duplicate rows are not inserted.

## GitHub Actions

`.github/workflows/update.yml` runs the scraper every day and commits changed files under `data/`.

```yaml
on:
  schedule:
    - cron: "20 23 * * *"
```

The workflow uses `GITHUB_TOKEN` with `contents: write`; no external secrets are required.

## Dashboard

The static frontend in `index.html`, `styles.css`, and `app.js` loads local JSON data and provides:

- total count, latest date, section coverage
- keyword search over title, section, and summary
- section filtering
- JSON and CSV download links
- responsive layout for desktop and mobile screenshots

## Compliance Notes

- Public pages only; no login, no personal data scraping, no access-control bypass.
- The crawler handles the public dynamic challenge returned by the site before reading ordinary HTML pages.
- This repository is unofficial and should not be used as an authoritative school notice source.

## Roadmap

- Add more CUPL office and college watchers with the same data schema.
- Publish a combined dashboard that aggregates all daily watcher repositories.
- Add RSS/Atom export for students, faculty, and researchers.
- Track changed titles or removed notices as separate history events.

## License

MIT
