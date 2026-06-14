#!/usr/bin/env python3
"""Fetch CUPL Human Resources Office notices and keep a daily history."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import http.cookiejar
import json
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


BASE_URL = "https://rsc.cupl.edu.cn"
USER_AGENT = "Mozilla/5.0 (compatible; cupl-rsc-notice-watch/1.0; +https://github.com/houdemingfagewuzhigong)"
DATA_DIR = Path("data")

SECTIONS = [
    {"name": "通知公告", "path": "tzgg.htm"},
    {"name": "招聘信息", "path": "zpxx.htm"},
    {"name": "人事政策", "path": "rszc1.htm"},
]


@dataclass
class Notice:
    id: str
    title: str
    date: str
    url: str
    summary: str
    section: str
    source_url: str
    first_seen_at: str
    last_seen_at: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def request(url: str, data: bytes | None = None, referer: str | None = None) -> urllib.request.Request:
    headers = {"User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if referer:
        headers["Referer"] = referer
    return urllib.request.Request(url, data=data, headers=headers)


def open_with_challenge(url: str) -> str:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    body = opener.open(request(url), timeout=30).read().decode("utf-8", "ignore")
    if "dynamic_challenge" not in body:
        return body

    challenge = re.search(r'challengeId\s*=\s*"([^"]+)"', body)
    answer = re.search(r"answer\s*=\s*(\d+)", body)
    if not challenge or not answer:
        raise RuntimeError("site returned a dynamic challenge but no challenge_id/answer was found")

    payload = json.dumps(
        {
            "challenge_id": challenge.group(1),
            "answer": int(answer.group(1)),
            "browser_info": {
                "userAgent": USER_AGENT,
                "language": "zh-CN",
                "platform": "MacIntel",
                "cookieEnabled": True,
                "hardwareConcurrency": 8,
                "deviceMemory": 8,
                "timezone": "Asia/Shanghai",
            },
        }
    ).encode()
    opener.open(request(BASE_URL + "/dynamic_challenge", payload, url), timeout=30).read()
    return opener.open(request(url), timeout=30).read().decode("utf-8", "ignore")


def clean(text: str) -> str:
    text = re.sub(r"<script.*?</script>", "", text or "", flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<.*?>", "", text, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def absolute_url(href: str, source_url: str) -> str:
    return urllib.parse.urljoin(source_url, href)


def notice_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def parse_list(html_text: str, section: str, source_url: str) -> list[Notice]:
    items: list[Notice] = []
    seen_at = now_iso()
    row_pattern = re.compile(
        r'<tr[^>]+id="line_u\d+_\d+"[^>]*>.*?<a\s+href="([^"]+)".*?title="([^"]+)".*?</a>.*?'
        r"<td[^>]*>\s*<span>(20\d{2}-\d{2}-\d{2})</span>",
        re.S | re.I,
    )
    for href, title, date in row_pattern.findall(html_text):
        url = absolute_url(href, source_url)
        items.append(
            Notice(
                id=notice_id(url),
                title=clean(title),
                date=date,
                url=url,
                summary="",
                section=section,
                source_url=source_url,
                first_seen_at=seen_at,
                last_seen_at=seen_at,
            )
        )
    return items


def section_pages(path: str, html_text: str, max_pages: int) -> list[str]:
    pages = [path]
    for link in re.findall(r'href="([^"]+?/\d+\.htm)"', html_text):
        candidate = urllib.parse.urljoin(path, link)
        if candidate not in pages and Path(candidate).name != Path(path).name:
            pages.append(candidate)
        if len(pages) >= max_pages:
            break
    return pages


def fetch(max_pages_per_section: int = 2) -> list[Notice]:
    notices: list[Notice] = []
    for section in SECTIONS:
        first_url = urllib.parse.urljoin(BASE_URL + "/", section["path"])
        first_html = open_with_challenge(first_url)
        for page_path in section_pages(section["path"], first_html, max_pages_per_section):
            page_url = urllib.parse.urljoin(BASE_URL + "/", page_path)
            page_html = first_html if page_path == section["path"] else open_with_challenge(page_url)
            notices.extend(parse_list(page_html, section["name"], page_url))
    unique = {notice.id: notice for notice in notices}
    return sorted(unique.values(), key=lambda item: (item.date, item.section, item.title), reverse=True)


def load_existing() -> dict[str, Notice]:
    path = DATA_DIR / "notices.json"
    if not path.exists():
        return {}
    return {item["id"]: Notice(**item) for item in json.loads(path.read_text(encoding="utf-8"))}


def save(notices: list[Notice]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "history").mkdir(exist_ok=True)
    existing = load_existing()
    merged: dict[str, Notice] = existing.copy()
    seen_at = now_iso()
    for notice in notices:
        if notice.id in merged:
            notice.first_seen_at = merged[notice.id].first_seen_at
        notice.last_seen_at = seen_at
        merged[notice.id] = notice

    rows = sorted(merged.values(), key=lambda item: (item.date, item.section, item.title), reverse=True)
    payload = [asdict(item) for item in rows]
    (DATA_DIR / "notices.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATA_DIR / "history" / f"{dt.date.today().isoformat()}.json").write_text(
        json.dumps([asdict(item) for item in notices], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (DATA_DIR / "notices.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(Notice.__dataclass_fields__.keys()))
        writer.writeheader()
        writer.writerows(payload)
    meta = {
        "site": "中国政法大学人事处",
        "base_url": BASE_URL,
        "notice_url": BASE_URL + "/tzgg.htm",
        "updated_at": seen_at,
        "total_notices": len(rows),
        "sections": sorted({item.section for item in rows}),
        "latest_date": rows[0].date if rows else None,
        "disclaimer": "非官方项目，仅归档公开网页信息，不代表中国政法大学官方。",
    }
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    notices = fetch(max_pages)
    save(notices)
    print(f"fetched {len(notices)} notices from {len(SECTIONS)} sections")
    if notices:
        print(f"latest: {notices[0].date} {notices[0].section} {notices[0].title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
