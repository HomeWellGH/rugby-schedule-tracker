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
# SuperSport (South African broadcaster). Embeds structured-but-unofficial
# JSON server-side rather than exposing a real API. Used as a second
# lineup source (all Tier 1 nations) tried between ESPN and the SA Rugby
# fallback, since it sometimes has a lineup before ESPN does.
# ---------------------------------------------------------------------------

SUPERSPORT_TOURS = {
    "Six Nations": "3ce1b8cd-bc57-4f60-8f8d-734279bcbfe3",
    "Rugby Championship": "df76e82b-6ea3-4761-8322-71c152e55736",
    "Nations Championship": "89f3bb34-7097-49f8-8983-1891e663dd42",
}

# SuperSport names teams things like "Springboks Men" or "Scotland Men" --
# strip " Men"/" Women" and map nicknames back to the canonical names above.
SUPERSPORT_NATION_ALIASES = {
    "Springboks": "South Africa",
    "All Blacks": "New Zealand",
    "Wallabies": "Australia",
    "Los Pumas": "Argentina",
}

# Standard rugby union jersey-number -> position convention, shared by any
# source (SA Rugby announcement, SuperSport, ...) that gives a shirt number
# but not a clean position label. 16-23 are simply "Replacement" since the
# specific position they'll cover varies.
JERSEY_POSITIONS = {
    1: "Prop", 2: "Hooker", 3: "Prop", 4: "Lock", 5: "Lock",
    6: "Flanker", 7: "Flanker", 8: "Number 8", 9: "Scrum-half",
    10: "Fly-half", 11: "Wing", 12: "Centre", 13: "Centre",
    14: "Wing", 15: "Fullback",
}
