"""Build data/schedule.json from live sources.

Run this locally (`python scripts/build_schedule.py`) or let the GitHub
Actions workflow run it on a schedule. It never touches the site's HTML/CSS/
JS -- it only regenerates the data file those files read.
"""
import json
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import (
    FAVORITE_TEAM, TARGET_TIMEZONE, TIER1_NATIONS, BROADCAST_DEFAULTS,
)
from fetch_fixtures import get_fixtures
from fetch_lineup import get_lineups
from fetch_sa_announcement import get_springbok_lineup
from fetch_squad import get_squad

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "schedule.json")
OVERRIDES_PATH = os.path.join(DATA_DIR, "broadcast_overrides.json")


def load_broadcast_overrides():
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        return {}
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def resolve_broadcaster(fixture, overrides_by_matchup):
    for key in (f"{fixture['home']} vs {fixture['away']}", f"{fixture['away']} vs {fixture['home']}"):
        if key in overrides_by_matchup:
            return overrides_by_matchup[key]
    return BROADCAST_DEFAULTS.get(fixture["competition"], "Check FloRugby / Peacock")


def format_local_time(date_utc_str, tz_name):
    if not date_utc_str:
        return None
    dt_utc = datetime.strptime(date_utc_str, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    dt_local = dt_utc.astimezone(ZoneInfo(tz_name))
    return dt_local.strftime("%a, %b %d, %Y - %I:%M %p %Z").replace(" 0", " ")


def venue_label(fixture):
    parts = [fixture["venue_name"]]
    city_state = ", ".join(p for p in (fixture["venue_city"], fixture["venue_state"]) if p)
    if city_state:
        parts.append(city_state)
    return " - ".join(parts)


def _normalize_name(name):
    return " ".join(name.strip().lower().split())


def build_caps_club_index(squad):
    """Map normalized player name -> (caps, club) from a Wikipedia squad list."""
    index = {}
    for p in squad:
        index[_normalize_name(p["name"])] = (p["caps"], p["club"])
    return index


def enrich_with_caps_club(players, name_index):
    """Attach caps/club to ESPN lineup players by matching name against the
    Wikipedia squad index. Falls back to a unique-surname match since
    ESPN and Wikipedia don't always format names identically.
    """
    surname_index = {}
    for norm_name, value in name_index.items():
        surname = norm_name.split()[-1]
        surname_index.setdefault(surname, []).append(value)

    enriched = []
    for player in players:
        norm_name = _normalize_name(player["name"])
        caps, club = name_index.get(norm_name, (None, None))
        if caps is None and club is None:
            surname = norm_name.split()[-1]
            candidates = surname_index.get(surname, [])
            if len(candidates) == 1:
                caps, club = candidates[0]
        enriched.append({**player, "caps": caps, "club": club})
    return enriched


def build():
    print("Fetching fixtures...")
    fixtures = get_fixtures()
    print(f"  found {len(fixtures)} fixtures involving Tier 1 nations")

    overrides_by_matchup = load_broadcast_overrides()

    squad_index_cache = {}
    squad_as_of_cache = {}

    def caps_club_index(nation):
        if nation not in TIER1_NATIONS:
            return {}
        if nation not in squad_index_cache:
            print(f"  fetching Wikipedia squad (for caps/club) for {nation}...")
            try:
                squad, as_of = get_squad(TIER1_NATIONS[nation])
            except Exception as exc:  # best-effort: never fail the whole build over one nation
                print(f"    [warn] squad fetch failed for {nation}: {exc}")
                squad, as_of = [], None
            squad_index_cache[nation] = build_caps_club_index(squad)
            squad_as_of_cache[nation] = as_of
        return squad_index_cache[nation]

    out_fixtures = []
    for fx in fixtures:
        print(f"  fetching matchday lineup for {fx['home']} vs {fx['away']}...")
        lineups = get_lineups(fx["competition"], fx["event_id"])

        home_players, home_pre_enriched = lineups.get("home", []), False
        away_players, away_pre_enriched = lineups.get("away", []), False

        # ESPN often lags SA Rugby's own team announcement by a few days.
        # For the Springboks specifically, try scraping springboks.rugby's
        # announcement article (already has caps/club inline) before giving
        # up and showing "not yet announced".
        if not home_players and fx["home"] == "South Africa":
            print("    ESPN has no Springbok lineup yet, trying springboks.rugby...")
            home_players = get_springbok_lineup(fx["away"])
            home_pre_enriched = bool(home_players)
        if not away_players and fx["away"] == "South Africa":
            print("    ESPN has no Springbok lineup yet, trying springboks.rugby...")
            away_players = get_springbok_lineup(fx["home"])
            away_pre_enriched = bool(away_players)

        # Players sourced from the SA Rugby article already carry caps/club
        # from the article itself; only ESPN-sourced players need the
        # separate Wikipedia lookup.
        home_lineup = home_players if home_pre_enriched else enrich_with_caps_club(home_players, caps_club_index(fx["home"]))
        away_lineup = away_players if away_pre_enriched else enrich_with_caps_club(away_players, caps_club_index(fx["away"]))

        home_as_of = "official team announcement (springboks.rugby)" if home_pre_enriched else squad_as_of_cache.get(fx["home"])
        away_as_of = "official team announcement (springboks.rugby)" if away_pre_enriched else squad_as_of_cache.get(fx["away"])

        out_fixtures.append({
            "event_id": fx["event_id"],
            "competition": fx["competition"],
            "home": fx["home"],
            "away": fx["away"],
            "is_favorite": FAVORITE_TEAM in (fx["home"], fx["away"]),
            "kickoff_local": format_local_time(fx["date_utc"], TARGET_TIMEZONE),
            "venue": venue_label(fx),
            "broadcast_us": resolve_broadcaster(fx, overrides_by_matchup),
            "home_lineup": home_lineup,
            "home_lineup_announced": len(home_lineup) > 0,
            "away_lineup": away_lineup,
            "away_lineup_announced": len(away_lineup) > 0,
            "caps_club_as_of": {
                fx["home"]: home_as_of,
                fx["away"]: away_as_of,
            },
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "favorite_team": FAVORITE_TEAM,
        "timezone": TARGET_TIMEZONE,
        "fixtures": out_fixtures,
        "caveats": [
            "Fixtures/venues/times come from ESPN's public (unofficial) rugby API.",
            "Matchday 23 (jersey numbers 1-23) comes from ESPN's per-event data, populated once "
            "the union announces it -- usually 2-4 days before kickoff. Until then a team shows "
            "as \"not yet announced\", which is expected, not an error.",
            "Caps and club are looked up separately from each nation's Wikipedia \"Current squad\" "
            "list by matching player names, and can occasionally miss a match (shows as \"?\") or "
            "lag a very recent transfer.",
            "Caps are career totals as of the date shown, not caps entering this specific match.",
            "For South Africa specifically, if ESPN hasn't posted the lineup yet, the site falls back "
            "to SA Rugby's own team-announcement article (found via Google Custom Search) -- this is "
            "usually available before ESPN and already includes caps/club straight from the source.",
            "US broadcaster is a best-effort mapping by competition (see data/broadcast_overrides.json "
            "to correct a specific fixture) -- always double check before making plans.",
        ],
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUTPUT_PATH} ({len(out_fixtures)} fixtures)")


if __name__ == "__main__":
    build()
