# Rugby Schedule Tracker

A free, static site that shows your favorite national rugby team's upcoming
fixtures plus every other Tier 1 nation's fixtures for the same window --
opponent, venue, kickoff time in your timezone, US broadcaster, and the
announced matchday 23 (jersey numbers 1-23, position, career caps, current
club) for both sides.

## How it works

- `scripts/build_schedule.py` pulls fixtures from ESPN's public rugby API,
  the announced matchday 23 for each fixture (also ESPN, once a union
  confirms it), and caps/club info from Wikipedia, then writes the result
  to `data/schedule.json`.
- `index.html` / `app.js` / `style.css` are a plain static site (no
  framework, no build step) that reads that JSON file and renders it.
- `.github/workflows/update.yml` runs the build script automatically every
  Monday and Thursday via GitHub Actions (free for public repos) and
  commits the refreshed `data/schedule.json`.

Total cost: $0. GitHub Pages hosting is free, GitHub Actions minutes are
free for public repos, and both data sources are free/unauthenticated.

## Data limitations -- read before you rely on this

This is a hobby project built entirely on free, unofficial sources. Known
rough edges:

- **Fixtures/venues/times**: from ESPN's undocumented rugby API. It's
  reliable in practice but could change shape or drop a competition without
  notice. If fixtures stop showing up, check the league IDs in
  `scripts/config.py` are still correct (search "espn rugby scoreboard
  league id").
- **Matchday 23**: comes from ESPN's per-event data, which is only
  populated once the union actually announces the team -- typically 2-4
  days before kickoff. Until then the site correctly shows "not yet
  announced"; that's expected, not a bug.
- **Caps/club**: looked up separately by matching each announced player's
  name against their nation's Wikipedia "Current squad" list. This can
  occasionally miss (shown as "?") if Wikipedia hasn't caught up on a very
  recent transfer, or if the name doesn't match cleanly (e.g. a nickname).
- **Caps**: career total as of the date shown on the page, not caps
  *entering* that specific match.
- **US broadcaster**: there's no free API for this at all. It's a static
  guess per competition in `scripts/config.py` (`BROADCAST_DEFAULTS`).
  Fix a specific fixture by adding an entry to
  `data/broadcast_overrides.json`, e.g.:
  ```json
  { "South Africa vs New Zealand": "NBC / Peacock" }
  ```

## Changing your favorite team or timezone

Edit `scripts/config.py`:

- `FAVORITE_TEAM` -- must match one of the keys in `TIER1_NATIONS`.
- `TARGET_TIMEZONE` -- any IANA timezone name (e.g. `America/New_York`,
  `America/Chicago`, `America/Denver`, `America/Los_Angeles`).
- `LOOKAHEAD_DAYS` -- how many days ahead to pull fixtures for.

Then regenerate the data:

```
pip install -r requirements.txt
python scripts/build_schedule.py
```

## Running locally

```
pip install -r requirements.txt
python scripts/build_schedule.py   # generates data/schedule.json
python -m http.server 8080         # serve the site
```

Open http://localhost:8080

## Deploying to GitHub Pages (free)

1. Create a new **public** GitHub repository and push this folder to it:
   ```
   git init
   git add .
   git commit -m "Initial rugby schedule tracker"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```
2. In the repo on GitHub: **Settings -> Pages** -> under "Build and
   deployment", set Source to **Deploy from a branch**, branch **main**,
   folder **/ (root)**. Save.
3. Your site will be live at
   `https://<your-username>.github.io/<repo-name>/` within a minute or two.
4. The included GitHub Actions workflow will keep `data/schedule.json`
   fresh automatically (Mondays and Thursdays). You can also trigger it
   manually from the repo's **Actions** tab ("Run workflow").

No further setup, servers, or paid tiers required.
