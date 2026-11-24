# whatdahack → Discord

Posts every new hackathon from [whatdahack.pl](https://whatdahack.pl) to a Discord channel.
Runs on GitHub Actions every 3 hours, free, no server.

It watches the site's public `sitemap.xml` for new `/events/...` pages and reads each
event's details (name, dates, place, organizer, registration link) from the page's
schema.org data.

## Setup (≈5 min)

1. **Discord webhook** – in your server: channel → ⚙️ Edit Channel → Integrations →
   Webhooks → New Webhook → Copy Webhook URL.
2. **Repo** – create a new GitHub repo (private is fine) and push these files:
   ```
   notify.py
   .github/workflows/notify.yml
   ```
3. **Secret** – repo → Settings → Secrets and variables → Actions → New repository secret:
   `DISCORD_WEBHOOK_URL` = the webhook URL.
4. **(Optional) city filter** – same page, *Variables* tab → `CITY_FILTER`,
   e.g. `Łódź,Warszawa,online`. Leave unset to get everything.
5. **First run** – Actions tab → *whatdahack → Discord* → Run workflow.
   The first run only records the ~190 existing events (nothing is posted);
   from then on, only new ones appear in Discord.

## Test locally

```bash
DRY_RUN=1 python3 notify.py   # first run: seeds seen.json
rm seen.json                  # (or delete a few lines from it to see embeds printed)
```

To force a test post, delete one URL from `seen.json` and run the workflow.