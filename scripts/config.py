"""Central configuration for the rugby schedule site.

Edit the values below to change your favorite team, timezone, or how far
ahead the schedule looks. No other script should need editing for that.
"""

# ---------------------------------------------------------------------------
# Your team
# ---------------------------------------------------------------------------

FAVORITE_TEAM = "South Africa"

# IANA timezone name used to convert kickoff times.
TARGET_TIMEZONE = "America/Los_Angeles"

# How many days ahead (from today) to pull fixtures for.
LOOKAHEAD_DAYS = 14

# ---------------------------------------------------------------------------
# Tier 1 nations -> their English Wikipedia article title (used to scrape the
# "Current squad" section for caps/club info). Keys must match the team
# names returned by ESPN's API.
# ---------------------------------------------------------------------------

TIER1_NATIONS = {
    "South Africa": "South Africa national rugby union team",
    "New Zealand": "New Zealand national rugby union team",
    "Australia": "Australia national rugby union team",
    "Argentina": "Argentina national rugby union team",
    "England": "England national rugby union team",
    "France": "France national rugby union team",
    "Ireland": "Ireland national rugby union team",
    "Scotland": "Scotland national rugby union team",
    "Wales": "Wales national rugby union team",
    "Italy": "Italy national rugby union team",
}

# Alternate/short names ESPN sometimes uses, mapped back to the canonical
# names above.
NATION_ALIASES = {
    "RSA": "South Africa",
    "Springboks": "South Africa",
    "NZL": "New Zealand",
    "All Blacks": "New Zealand",
    "AUS": "Australia",
    "Wallabies": "Australia",
    "ARG": "Argentina",
    "Los Pumas": "Argentina",
    "ENG": "England",
    "FRA": "France",
    "IRE": "Ireland",
    "SCO": "Scotland",
    "WAL": "Wales",
    "ITA": "Italy",
}

# ---------------------------------------------------------------------------
# ESPN's unofficial site API. These are undocumented endpoints -- they can
# change or disappear without notice, which is the tradeoff for "free".
# ---------------------------------------------------------------------------

ESPN_LEAGUES = {
    "Six Nations": 180659,
    "Rugby Championship": 244293,
    "Nations Championship": 17567,
    "International Test Match": 289234,
}

ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/rugby/{league_id}/scoreboard?dates={start}-{end}"

# ---------------------------------------------------------------------------
# US broadcaster info has no free structured API, so it's a best-effort
# static map by competition. Edit data/broadcast_overrides.json for
# specific fixtures that don't match these defaults (e.g. a one-off ESPN+
# simulcast) -- that file is loaded on top of this map and always wins.
# ---------------------------------------------------------------------------

BROADCAST_DEFAULTS = {
    "Six Nations": "Peacock (NBC Sports)",
    "Rugby Championship": "FloRugby",
    "Nations Championship": "Peacock (NBC Sports) -- unconfirmed, verify",
    "International Test Match": "FloRugby (check Peacock as alternate)",
}

# ---------------------------------------------------------------------------
# Rugby position code -> full name, for readable squad tables.
# ---------------------------------------------------------------------------

POSITION_NAMES = {
    "HK": "Hooker",
    "PR": "Prop",
    "LK": "Lock",
    "FL": "Flanker",
    "N8": "Number 8",
    "SH": "Scrum-half",
    "FH": "Fly-half",
    "CE": "Centre",
    "WG": "Wing",
    "FB": "Fullback",
}
