"""Scrape a national team's "Current squad" section from English Wikipedia.

Most Tier 1 nation articles build their squad table from the shared
{{nat rs player|...}} template, so one parser works across nations. This is
a *best-effort* source: it reflects Wikipedia's most recently edited squad
list for the nation, which usually tracks the squad named for the current
Test window but can lag a same-week injury change or lack the exact
matchday 23 (starting XV + bench) split.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

WIKI_API = "https://en.wikipedia.org/w/api.php"
# Wikipedia's API etiquette asks for a descriptive User-Agent so requests
# aren't mistaken for anonymous abuse and rate-limited.
HEADERS = {"User-Agent": "personal-rugby-schedule-hobby-project/1.0 (contact: not-provided; free/non-commercial)"}

SQUAD_SECTION_TITLES = {"current squad", "squad"}

# Be polite: small gap between requests, with backoff if we still get 429s.
_MIN_REQUEST_GAP_SECONDS = 0.6
_last_request_at = 0.0


def _api_get(params, max_retries=3):
    global _last_request_at
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"{WIKI_API}?{query}"
    req = urllib.request.Request(url, headers=HEADERS)

    for attempt in range(max_retries):
        wait = _MIN_REQUEST_GAP_SECONDS - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                _last_request_at = time.monotonic()
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            _last_request_at = time.monotonic()
            if exc.code == 429 and attempt < max_retries - 1:
                retry_after = float(exc.headers.get("Retry-After", 2 * (attempt + 1)))
                time.sleep(retry_after)
                continue
            raise


def _find_squad_section_index(page_title):
    data = _api_get({"action": "parse", "page": page_title, "prop": "sections", "format": "json"})
    sections = data.get("parse", {}).get("sections", [])
    for s in sections:
        if s.get("line", "").strip().lower() in SQUAD_SECTION_TITLES:
            return s.get("index")
    return None


def _find_template_blocks(wikitext, template_name):
    """Return all balanced {{template_name|...}} blocks (brace-depth aware)."""
    blocks = []
    lower = wikitext.lower()
    needle = "{{" + template_name.lower()
    i = 0
    while True:
        idx = lower.find(needle, i)
        if idx == -1:
            break
        depth = 0
        j = idx
        while j < len(wikitext):
            if wikitext[j:j + 2] == "{{":
                depth += 1
                j += 2
                continue
            if wikitext[j:j + 2] == "}}":
                depth -= 1
                j += 2
                if depth == 0:
                    break
                continue
            j += 1
        blocks.append(wikitext[idx:j])
        i = max(j, idx + 1)
    return blocks


def _split_top_level(text, sep="|"):
    parts, depth, current = [], 0, ""
    for ch in text:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return parts


def _template_params(block):
    inner = block.strip()[2:-2]  # strip outer {{ }}
    parts = _split_top_level(inner)
    params = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            params[k.strip()] = v.strip()
    return params


def _clean_value(text):
    if not text:
        return ""
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*/>", "", text)
    # {{sortname|First|Last|...}} -> "First Last"
    text = re.sub(
        r"\{\{[Ss]ortname\|([^|{}]*)\|([^|{}]*)(?:\|[^{}]*)?\}\}",
        r"\1 \2",
        text,
    )
    # [[Target|Display]] -> Display ; [[Target]] -> Target
    text = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    # drop any remaining templates (flags etc.) we didn't special-case
    for _ in range(3):
        new_text = re.sub(r"\{\{[^{}]*\}\}", "", text)
        if new_text == text:
            break
        text = new_text
    text = text.replace("'''", "").replace("''", "")
    return text.strip()


def _extract_as_of_date(wikitext):
    m = re.search(r"\{\{Birth date and age2\|(\d{4})\|(\d{1,2})\|(\d{1,2})\|", wikitext)
    if m:
        year, month, day = m.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def get_squad(page_title):
    """Return (squad, as_of_date). squad is a list of dicts with
    name, position, caps, club, club_nation. Returns ([], None) if the
    squad section can't be found or parsed.
    """
    section_index = _find_squad_section_index(page_title)
    if section_index is None:
        return [], None

    data = _api_get({
        "action": "parse", "page": page_title, "prop": "wikitext",
        "section": section_index, "format": "json",
    })
    wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
    if not wikitext:
        return [], None

    as_of = _extract_as_of_date(wikitext)
    blocks = _find_template_blocks(wikitext, "nat rs player")
    squad = []
    for block in blocks:
        params = _template_params(block)
        name = _clean_value(params.get("name", ""))
        if not name:
            continue
        caps_raw = _clean_value(params.get("caps", ""))
        try:
            caps = int(re.sub(r"[^\d]", "", caps_raw)) if caps_raw else None
        except ValueError:
            caps = None
        squad.append({
            "name": name,
            "position": params.get("pos", "").strip(),
            "caps": caps,
            "club": _clean_value(params.get("club", "")),
            "club_nation": params.get("clubnat", "").strip(),
        })
    return squad, as_of


if __name__ == "__main__":
    import sys
    title = sys.argv[1] if len(sys.argv) > 1 else "South Africa national rugby union team"
    squad, as_of = get_squad(title)
    print(f"as_of: {as_of}, players: {len(squad)}")
    for p in squad[:10]:
        print(" ", p)
