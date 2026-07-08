"""Second lineup source, tried between ESPN and the SA-only fallback.

supersport.com has no public API, but its pages embed a large JSON blob
server-side (via Next.js's streaming RSC format) that includes an explicit
areLineUpsAvailable flag and, once true, the full 23-player lineup with
shirt numbers -- for any Tier 1 fixture it covers, not just South Africa's.

It does not include caps or club, so results still go through the same
Wikipedia-based enrichment as ESPN's lineups. It also doesn't label which
half of the player list is which team, so the caller must resolve that
itself (see resolve_side_names below) -- typically by cross-checking names
against each nation's known squad, which build_schedule.py already has on
hand from the Wikipedia lookup.
"""
import re
import urllib.error
import urllib.request

from config import JERSEY_POSITIONS, SUPERSPORT_NATION_ALIASES, SUPERSPORT_TOURS

HEADERS = {"User-Agent": "personal-rugby-schedule-hobby-project/1.0 (contact: not-provided; free/non-commercial)"}

# eventDateEnd/eventDateStart/eventId/eventName sit close together and in
# this fixed order, so they're matched as one anchor. areLineUpsAvailable
# and feedId are elsewhere in the same event object at a variable distance
# (there's a channel/broadcast listing of unpredictable length in between),
# so those are found via bounded backward/forward search around the anchor
# instead of being baked into one long fragile regex.
EVENT_ANCHOR_RE = re.compile(
    r'"eventDateEnd":"[^"]*","eventDateStart":"(?P<date>[^"]*)",'
    r'"eventId":"(?P<event_id>\d+)","eventName":"(?P<name>[^"]+)"'
)
AVAILABLE_RE = re.compile(r'"areLineUpsAvailable":(true|false)')
FEED_ID_RE = re.compile(r'"feedId":"(?P<feed_id>[a-f0-9\-]{36})"')
_SEARCH_WINDOW = 2000


def _normalize_nation(name):
    name = name.strip()
    for suffix in (" Men", " Women"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return SUPERSPORT_NATION_ALIASES.get(name, name)


def _fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_fixtures(competition):
    """Return a list of {event_id, feed_id, home, away, lineups_available}
    for every fixture SuperSport lists under this competition's tour, or []
    if the competition isn't one SuperSport tracks separately or the fetch
    fails.
    """
    tour_id = SUPERSPORT_TOURS.get(competition)
    if not tour_id:
        return []

    url = f"https://supersport.com/rugby/tour/{tour_id}/fixtures"
    try:
        html = _fetch(url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"    [warn] SuperSport fixtures fetch failed: {exc}")
        return []

    # The embedded JSON is inside a JS string literal, so quotes are
    # backslash-escaped in the raw HTML -- unescape once and work in plain
    # JSON text from here on.
    text = html.replace('\\"', '"')

    fixtures = []
    for m in EVENT_ANCHOR_RE.finditer(text):
        window_start = max(0, m.start() - _SEARCH_WINDOW)
        avail_match = None
        for am in AVAILABLE_RE.finditer(text, window_start, m.start()):
            avail_match = am  # keep the last (closest) one before the anchor
        feed_match = FEED_ID_RE.search(text, m.end(), m.end() + _SEARCH_WINDOW)
        if not avail_match or not feed_match:
            continue
        fixtures.append({
            "event_id": m.group("event_id"),
            "feed_id": feed_match.group("feed_id"),
            "name": m.group("name"),
            "date": m.group("date"),
            "lineups_available": avail_match.group(1) == "true",
        })
    return fixtures


def match_fixture(fixtures, home, away, date_utc):
    """Find the SuperSport fixture (from an already-fetched list) matching
    one of our ESPN-derived fixtures, by team names (either order) and same
    calendar date. Callers that need this for many fixtures in the same
    competition should fetch the list once with get_fixtures() and reuse it
    here, rather than re-fetching per fixture.
    """
    target_day = (date_utc or "")[:10]
    wanted = {home, away}
    for fx in fixtures:
        if fx["date"][:10] != target_day:
            continue
        parts = fx["name"].split(" v ")
        if len(parts) != 2:
            continue
        teams = {_normalize_nation(parts[0]), _normalize_nation(parts[1])}
        if teams == wanted:
            return fx
    return None


def get_lineup_players(feed_id):
    """Return the raw list of up to 46 players (both sides combined, in
    whatever order SuperSport lists them) as {jersey, name, position}, or
    [] if unavailable/unparseable. Splitting this into two 23-player teams
    and assigning them to home/away is the caller's job (see
    split_into_two_sides) since SuperSport's data doesn't label sides.
    """
    url = f"https://supersport.com/rugby/match/{feed_id}"
    try:
        html = _fetch(url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"    [warn] SuperSport match fetch failed for {feed_id}: {exc}")
        return []

    text = html.replace('\\"', '"')
    start_marker = '"players":['
    start = text.find(start_marker)
    if start == -1:
        return []
    start += len(start_marker)

    depth = 1
    i = start
    while depth > 0 and i < len(text):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
        i += 1
    players_text = text[start:i]

    player_re = re.compile(
        r'\{"player":\{[^}]*"fullName":"(?P<name>[^"]+)"[^}]*\},'
        r'"position":"[^"]*","shirtNumber":"(?P<shirt>\d+)"\}'
    )
    players = []
    for pm in player_re.finditer(players_text):
        jersey = int(pm.group("shirt"))
        if 1 <= jersey <= 23:
            players.append({
                "jersey": jersey,
                "name": pm.group("name").strip(),
                "position": JERSEY_POSITIONS.get(jersey, "Replacement"),
            })
    return players


def split_into_two_sides(players):
    """SuperSport lists both teams' 23 players back to back in one array
    with no side label. Split on the point where the jersey number resets
    (e.g. ...23, 1...) into two ~23-player chunks. Returns (chunk_a,
    chunk_b) or ([], []) if the data doesn't look like two clean teams.
    """
    if len(players) < 30:  # need close to 2x23 to trust this
        return [], []
    split_at = None
    for idx in range(1, len(players)):
        if players[idx]["jersey"] < players[idx - 1]["jersey"]:
            split_at = idx
            break
    if split_at is None:
        return [], []
    chunk_a, chunk_b = players[:split_at], players[split_at:]
    if len(chunk_a) < 15 or len(chunk_b) < 15:
        return [], []
    return chunk_a, chunk_b


def _normalize_name(name):
    return " ".join(name.strip().lower().split())


def assign_sides_by_name(chunk_a, chunk_b, home_name_index, away_name_index):
    """Decide which chunk is home vs away by counting how many player
    names in each chunk match names already known for each nation (from
    the Wikipedia squad index build_schedule.py builds anyway). Returns
    (home_players, away_players). If there's no name-match signal at all,
    or the two chunks are equally consistent with both orderings, this
    returns ([], []) rather than guess -- an unlabeled lineup is treated
    as unavailable rather than risk swapping the two teams.
    """
    def score(chunk, name_index):
        return sum(1 for p in chunk if _normalize_name(p["name"]) in name_index)

    # "a as home" reading vs "b as home" reading -- whichever pairing has
    # the higher combined match count wins, as long as it actually beats
    # the alternative (not just ties).
    a_as_home_score = score(chunk_a, home_name_index) + score(chunk_b, away_name_index)
    b_as_home_score = score(chunk_b, home_name_index) + score(chunk_a, away_name_index)

    if a_as_home_score > b_as_home_score:
        return chunk_a, chunk_b
    if b_as_home_score > a_as_home_score:
        return chunk_b, chunk_a
    return [], []
