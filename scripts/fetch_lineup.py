"""Pull the announced matchday 23 (jersey numbers 1-23) for a specific
fixture from ESPN's per-event summary endpoint.

Unions typically announce this 2-4 days before kickoff, so for fixtures
further out this will legitimately come back empty -- that's not a bug,
it means "not announced yet".
"""
import json
import urllib.error
import urllib.request

from config import ESPN_LEAGUES

HEADERS = {"User-Agent": "personal-rugby-schedule-hobby-project/1.0 (contact: not-provided; free/non-commercial)"}
ESPN_SUMMARY_URL = "https://site.api.espn.com/apis/site/v2/sports/rugby/{league_id}/summary?event={event_id}"


def get_lineups(competition, event_id):
    """Return {"home": [players], "away": [players]}. A missing or empty
    list for a side means that side's team hasn't been announced yet.
    Each player dict has: jersey, name, position, captain, starter.
    """
    league_id = ESPN_LEAGUES.get(competition)
    if league_id is None:
        return {}

    url = ESPN_SUMMARY_URL.format(league_id=league_id, event_id=event_id)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"    [warn] lineup fetch failed for event {event_id}: {exc}")
        return {}

    result = {}
    for entry in data.get("rosters", []):
        home_away = entry.get("homeAway")
        players = []
        for p in entry.get("roster", []):
            athlete = p.get("athlete", {})
            position = p.get("position", {})
            jersey_raw = p.get("jersey")
            try:
                jersey = int(jersey_raw) if jersey_raw else None
            except ValueError:
                jersey = None
            name = athlete.get("displayName", "").strip()
            if not name:
                continue
            position_name = (position.get("displayName") or position.get("abbreviation") or "").title()
            players.append({
                "jersey": jersey,
                "name": name,
                # ESPN's own "starter" flag is unreliable pre-kickoff (often
                # false for the whole team); jersey <=15 is the actual rugby
                # convention for the starting XV vs the bench (16-23).
                "position": position_name,
                "captain": bool(p.get("captain")),
                "starter": jersey is not None and jersey <= 15,
            })
        players.sort(key=lambda x: x["jersey"] if x["jersey"] is not None else 99)
        if home_away:
            result[home_away] = players
    return result


if __name__ == "__main__":
    import sys
    competition = sys.argv[1] if len(sys.argv) > 1 else "Nations Championship"
    event_id = sys.argv[2] if len(sys.argv) > 2 else "603985"
    lineups = get_lineups(competition, event_id)
    for side, players in lineups.items():
        print(side, "-", len(players), "players")
        for p in players:
            print(" ", p)
