#!/usr/bin/env python3
"""Check the release year of every Songdle song (both libraries and Charts) against more than one source.

Runs from tools/songs.py on GitHub whenever the file playlists/.check-years exists, and deletes it when done.
Progress is kept in playlists/.year-check.json, so a run that hits the time limit carries on next time.

For each song the candidate years are:
  * Apple: the release year of the exact track Songdle plays, and of every other release of the same song by the
    same artist (same Apple artist ID, so another artist who happens to share the name never counts; versions
    crediting everyone on the song only; remixes/live/acoustic only for songs that are themselves one).
  * MusicBrainz: the first release date of the recording, found by ISRC when the playlist CSV has one
    (Spotify exports do), otherwise by title + artist search.
  * The playlist CSV's release date (Spotify album date), when there is one.
A year only counts when two independent sources agree on it (within a year): two different Apple releases,
or Apple + MusicBrainz, or either + the CSV. The song gets the earliest year that counts. That way a single
odd date (an Apple listing dated decades early, a same-name artist on MusicBrainz) can't win, and neither can
a remaster or compilation date when the original release is known.
"""
import csv, glob, io, json, os, re, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itunes_ids as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = os.path.join(ROOT, "playlists", ".check-years")
PROGRESS = os.path.join(ROOT, "playlists", ".year-check.json")
THIS_YEAR = time.gmtime().tm_year
UA = "Yahyadle-Songdle/1.0 ( https://github.com/YLP-Games/Yahyadle )"

def key(s):
    return (T.title_key(s["t"]), T.main_artist(s["a"]))

def kstr(k):
    return k[0] + "|" + k[1]

# ---- MusicBrainz (1 request a second, as they ask) ----
_mb_lock, _mb_next = threading.Lock(), [0.0]

def mb(query):
    url = "https://musicbrainz.org/ws/2/recording?" + urllib.parse.urlencode({"query": query, "fmt": "json", "limit": 25})
    for attempt in range(6):
        with _mb_lock:
            wait = _mb_next[0] - time.time()
            _mb_next[0] = max(time.time(), _mb_next[0]) + 1.1
        if wait > 0:
            time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.load(r).get("recordings", [])
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(5 * (attempt + 1))
                continue
            return []
        except Exception:
            time.sleep(3 * (attempt + 1))
    return []

def lucene(x):
    return re.sub(r'([+\-!(){}\[\]^"~*?:\\/]|&&|\|\|)', r"\\\1", x)

def year_of(d):
    m = re.match(r"(\d{4})", d or "")
    y = int(m.group(1)) if m else 0
    return y if 1900 < y <= THIS_YEAR else 0   # Apple uses 1900 as a "don't know" date

def mb_years(s, isrc):
    """[(year, source)] from MusicBrainz recordings that are this song."""
    out = []
    if isrc:
        for r in mb(f"isrc:{isrc}"):
            y = year_of(r.get("first-release-date"))
            if y:
                out.append((y, "mb-isrc"))
        if out:
            return out
    t, a = s["t"], s["a"]
    lt, ma, distinct = T.loose_title(t), T.main_artist(a), T.distinct(t)
    title = T.search_title(t)
    for r in mb(f'recording:"{lucene(title)}" AND artist:"{lucene(T.main_artist_raw(a))}"'):
        if (r.get("score") or 0) < 80 or r.get("video"):
            continue
        if T.loose_title(r.get("title", "")) != lt or T.distinct(r.get("title", "") + " " + (r.get("disambiguation") or "")) != distinct:
            continue
        credit = " & ".join(c.get("name", "") for c in r.get("artist-credit", []) if isinstance(c, dict))
        if ma not in T.artists(credit):
            continue
        y = year_of(r.get("first-release-date"))
        if y:
            out.append((y, "mb"))
    return out

# ---- Apple ----
def apple_tracks(ids_by_country):
    """{trackId: track} for our IDs (150 per request)."""
    out = {}
    for country, ids in ids_by_country.items():
        ids = list(ids)
        for i in range(0, len(ids), 150):
            for r in T.itunes({"id": ",".join(map(str, ids[i:i + 150])), "country": country}, "lookup"):
                if r.get("wrapperType") == "track":
                    out[r["trackId"]] = r
    return out

_cat = {}
def catalogue(artist_id, country):
    k = (artist_id, country)
    if k not in _cat:
        _cat[k] = [x for x in T.itunes({"id": artist_id, "entity": "song", "limit": 200, "country": country}, "lookup")
                   if x.get("wrapperType") == "track"]
    return _cat[k]

def apple_years(s, track, country):
    """[(year, collectionId)]: the played track plus same-artist releases of the same song."""
    out, played = {}, None
    if track:
        y = year_of(track.get("releaseDate"))
        played = track.get("collectionId") or track["trackId"]
        if y:
            out[played] = y
        want = set(T.artists(s["a"]))
        for t in catalogue(track["artistId"], country):
            if T.loose_title(t.get("trackName", "")) != T.loose_title(s["t"]):
                continue
            if T.distinct(t.get("trackName", "")) != T.distinct(s["t"]):
                continue
            if want and not want <= T.credited(t):
                continue
            y = year_of(t.get("releaseDate"))
            if y:
                cid = t.get("collectionId") or t["trackId"]
                out[cid] = min(y, out.get(cid, 9999))
    return [(y, ("apple-played:" if c == played else "apple:") + str(c)) for c, y in out.items()]

def kind(src):
    return "apple" if src.startswith("apple") else "mb" if src.startswith("mb") else src

REISSUE = re.compile(r"remaster|\bmono\b|\bstereo\b|single version|radio edit|\bedit\b|anniversary|deluxe", re.I)

def near(y, ys):
    return any(abs(y - x) <= 1 for x in ys)

def decide(cands, current, title=""):
    """Pick the year.
    * With an ISRC (the playlist CSV identifies the exact recording): MusicBrainz's first release date of that
      recording. Only for a remaster/single version/edit does an earlier original win, and only when at least
      three Apple listings agree on it.
    * Without one: keep the current year when an Apple listing of this song by this artist backs it (within a
      year). Otherwise take the earliest year Apple and MusicBrainz (or the CSV) agree on; failing that, the
      earliest year at least two Apple listings agree on; failing that, leave it alone."""
    isrc = [y for y, s in cands if s == "mb-isrc"]
    apple = [y for y, s in cands if kind(s) == "apple"]
    other = [y for y, s in cands if kind(s) != "apple"]
    if isrc:
        y = min(isrc)
        if REISSUE.search(title):
            early = sorted(a for a in apple if a < y - 1 and sum(abs(a - b) <= 1 for b in apple) >= 3)
            if early:
                return early[0]
        return y
    if current and near(current, apple):
        return current
    both = sorted(a for a in apple if near(a, other))
    if both:
        return both[0]
    two = sorted(a for a in apple if sum(abs(a - b) <= 1 for b in apple) >= 2)
    if two:
        return two[0]
    # Nothing backs the current year at all: the release year of the exact track Songdle plays beats a number from nowhere
    played = [y for y, s in cands if s.startswith("apple-played")]
    if played and not near(current or 0, [y for y, _ in cands]):
        return played[0]
    return current

# ---- CSV info (ISRC and album year) ----
def csv_info():
    info = {}
    import songs as S
    for path in sorted(glob.glob(os.path.join(ROOT, "playlists", "*", "*.csv")) + glob.glob(os.path.join(ROOT, "playlists", "*", "imported", "*.csv"))):
        text = open(path, encoding="utf-8-sig", errors="replace").read()
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 2:
            continue
        head = [h.lower().strip() for h in rows[0]]
        ii = head.index("isrc") if "isrc" in head else -1
        ti = next((i for i, h in enumerate(head) if h in ("track name", "title", "song", "name")), -1)
        ai = next((i for i, h in enumerate(head) if h.startswith("artist name") or h == "artist"), -1)
        yi = next((i for i, h in enumerate(head) if h in ("release date", "year", "date")), -1)
        if ti < 0 or ai < 0:
            continue
        for r in rows[1:]:
            g = lambda i: r[i].strip() if 0 <= i < len(r) else ""
            t, a = g(ti), S.join_artists(g(ai))
            if not t or not a or t.lower() == "undefined":
                continue
            k = key({"t": t, "a": a})
            d = info.setdefault(k, {"isrc": "", "years": []})
            if ii >= 0 and g(ii) and not d["isrc"]:
                d["isrc"] = g(ii).upper()
            y = year_of(g(yi))
            if y:
                d["years"].append(y)
    return info

# ---- Run ----
def check(data, charts, save):
    if not os.path.exists(MARKER):
        return
    prog = json.load(open(PROGRESS)) if os.path.exists(PROGRESS) else {}
    info = csv_info()
    lists = list(data.values()) + [charts]
    todo = {}
    for songs in lists:
        for s in songs:
            k = key(s)
            if kstr(k) not in prog:
                todo.setdefault(k, []).append(s)
    print(f"checking years: {len(todo)} songs to go ({len(prog)} already done)", flush=True)
    # Our own Apple tracks first (fast, 150 a request)
    by_country = {}
    for copies in todo.values():
        s = next((c for c in copies if c.get("i")), None)
        if s:
            by_country.setdefault(s.get("c") or "US", set()).add(s["i"])
    tracks = apple_tracks(by_country)
    lock, done, changed = threading.Lock(), [0], [0]
    report = prog.setdefault("_report", {"changed": [], "mb_hits": 0, "apple_hits": 0, "kept": 0})

    def work(item):
        k, copies = item
        s = copies[0]
        idd = next((c for c in copies if c.get("i")), None)
        country = (idd or {}).get("c") or "US"
        tr = tracks.get(idd["i"]) if idd else None
        meta = info.get(k, {"isrc": "", "years": []})
        cands = []
        try:
            cands += apple_years(s, tr, country)
        except Exception as e:
            print("  apple error:", s["t"], s["a"], e, flush=True)
        cands += mb_years(s, meta["isrc"])
        cands += [(y, "csv") for y in meta["years"][:1]]
        cur = min((c.get("y") or 9999) for c in copies)
        cur = 0 if cur == 9999 else cur
        y = decide(cands, cur, s["t"])
        with lock:
            report["mb_hits"] += any(kind(src) == "mb" for _, src in cands)
            report["apple_hits"] += any(kind(src) == "apple" for _, src in cands)
            report["kept"] += y == cur
            if y and y != cur:
                changed[0] += 1
                report["changed"].append([s["t"], s["a"], cur, y, sorted(cands)])
            elif cands and not near(cur or 0, [c for c, _ in cands]):
                report.setdefault("unbacked", []).append([s["t"], s["a"], cur, sorted(cands)])
                print(f"  {s['t']} — {s['a']}: {cur or '?'} -> {y}   {sorted(cands)}", flush=True)
            for c in copies:
                if y:
                    c["y"] = y
            prog[kstr(k)] = y
            done[0] += 1
            if done[0] % 100 == 0:
                print(f"  {done[0]}/{len(todo)} checked, {changed[0]} changed", flush=True)
                save()
                json.dump(prog, open(PROGRESS, "w"))

    # Apple and MusicBrainz have separate rate limits, so a few songs at a time keeps both busy
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(work, todo.items()))
    save()
    print(f"years checked: {done[0]} songs, {changed[0]} changed", flush=True)
    # A readable record of what changed (the run log isn't always easy to get at)
    with open(os.path.join(ROOT, "playlists", "year-check-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=0)
    for f in (MARKER, PROGRESS):
        if os.path.exists(f):
            os.remove(f)
