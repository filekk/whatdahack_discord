<div align="center">

# whatdahack → Discord

Posts new hackathons from [whatdahack.pl](https://whatdahack.pl) to a Discord channel.<br/>
Runs every 3 hours on GitHub Actions.

[![Notify](https://github.com/filekk/whatdahack_discord/actions/workflows/notify.yml/badge.svg)](https://github.com/filekk/whatdahack_discord/actions/workflows/notify.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
[![License](https://img.shields.io/badge/license-Apache%202.0-lightgrey)](LICENSE)

[**Use this template**](https://github.com/filekk/whatdahack_discord/generate) · [Setup](#setup) · [Options](#options)

</div>

---

## Setup

1. Click **Use this template** (or fork; if you fork, enable workflows in the **Actions** tab).
2. Create a webhook in Discord (channel settings → **Integrations** → **Webhooks**) and add its URL
   as a repository secret called `DISCORD_WEBHOOK_URL`.
3. Run the workflow once from the **Actions** tab. The first run only saves the events already
   on the site, so nothing gets posted. After that, only new ones are posted.

## Options

Optional repository variables:

| Variable | Default | Description |
|---|---|---|
| `CITY_FILTER` | *(all)* | Comma-separated cities to keep, e.g. `Łódź,Warszawa,online` |
| `ONLY_UPCOMING` | `1` | Skip events that already ended |

## How it works

The script reads the site's `sitemap.xml`, finds event pages it hasn't seen yet, and posts
their details to the webhook. Seen events are stored in `seen.json` on the `state` branch.

To test locally: `DRY_RUN=1 python3 notify.py` (Python 3.9+, no dependencies).

---

<div align="center">
<sub>Unofficial, not affiliated with whatdahack.pl</sub>
</div>
