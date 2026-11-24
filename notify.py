#!/usr/bin/env python3
"""Post new hackathons from whatdahack.pl to a Discord channel.

How it works:
  1. Reads https://whatdahack.pl/sitemap.xml and collects every /events/<slug> URL.
  2. Compares them with seen.json (URLs already handled).
  3. For each new URL, reads the schema.org Event JSON-LD from the event page
     and posts a Discord embed through a webhook.
  4. Saves the updated seen.json.

On the very first run (no seen.json yet) it only records the existing events
and posts nothing, so your channel isn't flooded with ~190 old hackathons.

Env vars:
  DISCORD_WEBHOOK_URL  (required)  Discord channel webhook URL
  ONLY_UPCOMING        (optional)  "1" (default) = skip events that already ended
  CITY_FILTER          (optional)  comma-separated cities, e.g. "Łódź,Warszawa,online"
  DRY_RUN              (optional)  "1" = print instead of posting
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SITEMAP = "https://whatdahack.pl/sitemap.xml"
STATE = Path(__file__).with_name("seen.json")
UA = {"User-Agent": "whatdahack-discord-notifier/1.0 (+personal use)"}

WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")
ONLY_UPCOMING = os.environ.get("ONLY_UPCOMING", "1") == "1"
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
CITY_FILTER = [c.strip().lower() for c in os.environ.get("CITY_FILTER", "").split(",") if c.strip()]


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def event_urls() -> list[str]:
    xml = get(SITEMAP)
    return sorted(set(re.findall(r"<loc>(https://whatdahack\.pl/events/[^<]+)</loc>", xml)))


def event_data(url: str) -> dict | None:
    html = get(url)
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Event":
            return data
    return None


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "?"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"<t:{int(dt.timestamp())}:D>"  # Discord renders it in the reader's timezone
    except ValueError:
        return iso


def is_upcoming(ev: dict) -> bool:
    end = ev.get("endDate") or ev.get("startDate")
    if not end:
        return True
    try:
        return datetime.fromisoformat(end.replace("Z", "+00:00")) >= datetime.now(timezone.utc)
    except ValueError:
        return True


def city_of(ev: dict) -> str:
    loc = ev.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    if loc.get("@type") == "VirtualLocation":
        return "online"
    return ((loc.get("address") or {}).get("addressLocality") or "").strip()


def matches_city(ev: dict) -> bool:
    if not CITY_FILTER:
        return True
    mode = ev.get("eventAttendanceMode", "")
    city = city_of(ev).lower()
    if "online" in CITY_FILTER and ("Online" in mode or "Mixed" in mode or city == "online"):
        return True
    return city in CITY_FILTER


def build_embed(url: str, ev: dict) -> dict:
    mode = ev.get("eventAttendanceMode", "")
    mode_txt = "Online" if "Online" in mode else "Hybryda" if "Mixed" in mode else "Na miejscu"
    loc = ev.get("location") or {}
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    place = ", ".join(x for x in [loc.get("name"), city_of(ev)] if x and x != "online")
    offers = ev.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    org = (ev.get("organizer") or {})
    if isinstance(org, list):
        org = org[0] if org else {}

    fields = [
        {"name": "📅 Termin", "value": f"{fmt_date(ev.get('startDate'))} → {fmt_date(ev.get('endDate'))}", "inline": True},
        {"name": "📍 Tryb", "value": mode_txt + (f"\n{place}" if place else ""), "inline": True},
    ]
    if org.get("name"):
        fields.append({"name": "🏢 Organizator", "value": org["name"][:1024], "inline": True})
    if offers.get("url"):
        fields.append({"name": "📝 Rejestracja", "value": offers["url"][:1024], "inline": False})

    return {
        "title": (ev.get("name") or url.rsplit("/", 1)[-1])[:256],
        "url": url,
        "description": (ev.get("description") or "")[:600],
        "color": 0x3DDC84,
        "fields": fields,
        "footer": {"text": "whatdahack.pl"},
    }


def post(embed: dict) -> None:
    if DRY_RUN:
        print(json.dumps(embed, ensure_ascii=False, indent=2))
        return
    body = json.dumps({"username": "what_da_hack", "embeds": [embed]}).encode()
    req = urllib.request.Request(WEBHOOK, data=body, method="POST",
                                 headers={"Content-Type": "application/json", **UA})
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=30)
            return
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limited
                time.sleep(float(e.headers.get("Retry-After", "2")))
                continue
            raise


def main() -> int:
    if not WEBHOOK and not DRY_RUN:
        print("DISCORD_WEBHOOK_URL is not set", file=sys.stderr)
        return 1

    urls = event_urls()
    if not urls:
        print("No events found in sitemap — site structure may have changed.", file=sys.stderr)
        return 1

    first_run = not STATE.exists()
    seen = set() if first_run else set(json.loads(STATE.read_text()))
    new = [u for u in urls if u not in seen]

    if first_run:
        print(f"First run: recording {len(urls)} existing events, posting nothing.")
        new_posted = []
    else:
        new_posted = []
        for url in new:
            try:
                ev = event_data(url)
            except Exception as e:  # keep going, retry next run
                print(f"Failed to fetch {url}: {e}", file=sys.stderr)
                continue
            seen.add(url)
            if not ev:
                continue
            if ONLY_UPCOMING and not is_upcoming(ev):
                continue
            if not matches_city(ev):
                continue
            post(build_embed(url, ev))
            new_posted.append(url)
            time.sleep(1)

    seen.update(urls if first_run else [])
    STATE.write_text(json.dumps(sorted(seen), indent=0, ensure_ascii=False))
    if not first_run:
        print(f"{len(new)} new in sitemap, {len(new_posted)} posted to Discord.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
