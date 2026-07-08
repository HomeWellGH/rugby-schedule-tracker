"""Pull upcoming Tier 1 rugby fixtures from ESPN's unofficial site API.

No API key needed, but the endpoints are undocumented -- they can change
shape without notice. If this starts returning nothing, check the league
IDs in config.py are still valid (search "espn rugby scoreboard league id").
"""
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from config import ESPN_LEAGUES, ESPN_SCOREBOARD_URL, TIER1_NATIONS, NATION_ALIASES, LOOKAHEAD_DAYS

HEADERS = {"User-Agent": "Mozilla/5.0 (rugby-schedule-hobby-project)"}


def canonical_nation(name):
    """Resolve an ESPN team name/abbreviation to our canonical nation name."""
    if name in TIER1_NATIONS:
        return name
    return NATION_ALIASES.get(name)


def _fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_fixtures(lookahead_days=LOOKAHEAD_DAYS):
    """Return a de-duplicated list of upcoming Tier 1 fixtures.

    Each fixture dict has: event_id, competition, date_utc, home, away,
    venue_name, venue_city, venue_state.
    """
    today = datetime.now(timezone.utc)
    start = today.strftime("%Y%m%d")
    end = (today + timedelta(days=lookahead_days)).strftime("%Y%m%d")

    fixtures = {}
    for competition, league_id in ESPN_LEAGUES.items():
        url = ESPN_SCOREBOARD_URL.format(league_id=league_id, start=start, end=end)
        try:
            payload = _fetch_json(url)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  [warn] could not fetch {competition} ({url}): {exc}")
            continue

        for event in payload.get("events", []):
            event_id = event.get("id")
            if event_id in fixtures:
                continue

            competitions = event.get("competitions", [{}])
            comp = competitions[0] if competitions else {}
            competitors = comp.get("competitors", [])
            if len(competitors) != 2:
                continue

            teams = {}
            for c in competitors:
                team_name = c.get("team", {}).get("displayName", "")
                teams[c.get("homeAway", "")] = team_name

            home, away = teams.get("home"), teams.get("away")
            home_nation = canonical_nation(home)
            away_nation = canonical_nation(away)
            if not home_nation and not away_nation:
                continue  # neither side is a Tier 1 nation we track

            venue = comp.get("venue", {})
            address = venue.get("address", {})

            fixtures[event_id] = {
                "event_id": event_id,
                "competition": competition,
                "date_utc": event.get("date"),
                "home": home_nation or home,
                "away": away_nation or away,
                "venue_name": venue.get("fullName", "TBA"),
                "venue_city": address.get("city", ""),
                "venue_state": address.get("state", ""),
            }

    return sorted(fixtures.values(), key=lambda f: f["date_utc"] or "")


if __name__ == "__main__":
    for f in get_fixtures():
        print(f)
