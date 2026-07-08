"""Fallback source for the Springboks' own matchday 23, used only when
ESPN hasn't picked up the lineup yet.

SA Rugby (springboks.rugby) publishes a plain-text article with the full
numbered team the same day it's announced -- well ahead of ESPN in
practice. The site itself has no public API or feed to *discover* that
article automatically, so this uses the Google Custom Search JSON API
(free tier: 100 queries/day) restricted to springboks.rugby to find it,
then parses the article's own "1 Player Name (Club) -- N caps" list.

Requires two environment variables (see README for how to get them):
  GOOGLE_CSE_API_KEY
  GOOGLE_CSE_ID

If either is unset, this module is skipped entirely (returns no players)
-- it is a bonus source, not a required one.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from config import JERSEY_POSITIONS

HEADERS = {"User-Agent": "personal-rugby-schedule-hobby-project/1.0 (contact: not-provided; free/non-commercial)"}
CSE_URL = "https://www.googleapis.com/customsearch/v1"

PLAYER_LINE_RE = re.compile(
    r"(?P<jersey>\d{1,2})\s+"
    r"(?P<name>[A-Z][A-Za-zÀ-ſ'.\- ]*?)\s*"
    r"\((?P<club>[^)]+)\)[^\d\n]{0,6}"
    r"(?P<caps>\d+)\s*caps?\b",
)


def _has_credentials():
    return bool(os.environ.get("GOOGLE_CSE_API_KEY") and os.environ.get("GOOGLE_CSE_ID"))


def _find_article_url(opponent):
    api_key = os.environ["GOOGLE_CSE_API_KEY"]
    cse_id = os.environ["GOOGLE_CSE_ID"]
    query = f"springboks team announcement {opponent} caps"
    params = urllib.parse.urlencode({"key": api_key, "cx": cse_id, "q": query, "num": 5})
    req = urllib.request.Request(f"{CSE_URL}?{params}", headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"    [warn] Google CSE search failed: {exc}")
        return None

    for item in data.get("items", []):
        link = item.get("link", "")
        if "springboks.rugby/news-features/articles/" in link:
            return link
    return None


def _parse_article(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    players = []
    seen_jerseys = set()
    for m in PLAYER_LINE_RE.finditer(html):
        jersey = int(m.group("jersey"))
        if jersey < 1 or jersey > 23 or jersey in seen_jerseys:
            continue
        seen_jerseys.add(jersey)
        # The captain's line embeds "captain, " ahead of the club name inside
        # the same parentheses, e.g. "(captain, Toyota Verblitz)".
        club = m.group("club").strip()
        captain = False
        if re.match(r"captain\s*,\s*", club, re.IGNORECASE):
            captain = True
            club = re.sub(r"^captain\s*,\s*", "", club, flags=re.IGNORECASE).strip()
        players.append({
            "jersey": jersey,
            "name": m.group("name").strip(),
            "position": JERSEY_POSITIONS.get(jersey, "Replacement"),
            "captain": captain,
            "starter": jersey <= 15,
            "caps": int(m.group("caps")),
            "club": club,
        })
    players.sort(key=lambda p: p["jersey"])
    # A real matchday 23 has exactly 23 entries; anything less usually means
    # the regex caught an unrelated numbered list on the page.
    return players if len(players) == 23 else []


def get_springbok_lineup(opponent):
    """Return a list of 23 player dicts, or [] if unavailable/not found."""
    if not _has_credentials():
        return []
    url = _find_article_url(opponent)
    if not url:
        return []
    try:
        return _parse_article(url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"    [warn] failed to fetch/parse SA Rugby article {url}: {exc}")
        return []


if __name__ == "__main__":
    import sys
    opponent = sys.argv[1] if len(sys.argv) > 1 else "Scotland"
    lineup = get_springbok_lineup(opponent)
    print(f"{len(lineup)} players found")
    for p in lineup:
        print(" ", p)
