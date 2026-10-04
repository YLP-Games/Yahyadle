#!/usr/bin/env python3
"""Keep Songdle's song lists tidy. Runs automatically on GitHub (.github/workflows/songs.yml) whenever song
data changes, and can be run by hand:  python3 tools/songs.py

1. Imports playlist CSVs dropped into playlists/layla/ or playlists/yahya/ (Exportify, TuneMyMusic or any CSV
   with title and artist columns). New songs are added to that person's library; songs already there are skipped.
   Each CSV then moves to an imported/ subfolder, so it isn't imported again (and deleted songs stay deleted).
2. Sorts every genre into one shared set of categories (the same rules as genreCat() in index.html).
3. Merges duplicates within each list: same title and main artist, ignoring feat. credits and remaster/edit tags.
4. Adds iTunes track IDs (and original release years) to songs that don't have one yet, including Charts.
5. Fills in missing genres from Apple's genre for each song.

Files: playlists.json ({"layla": [...], "yahya": [...]}) and the CHARTS list inside index.html.
Options: --no-lookup (tidy only, no network), --retry-missing (look again for songs not found before).
"""
import argparse, csv, glob, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import itunes_ids as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYLISTS = os.path.join(ROOT, "playlists.json")
INDEX = os.path.join(ROOT, "index.html")
CHARTS_RE = re.compile(r"const CHARTS=(\[\[.*?\]\]);", re.S)

# ---- Genre categories (keep in step with GENRE_CATS in index.html) ----
# First match wins, so the specific ones come before the broad ones (e.g. "pop latino" is Latin, "pop rap" is Hip-Hop/Rap).
CATS = [
    ("K-Pop", r"k-?pop|korean"),
    ("J-Pop", r"j-?pop|j-?rock|japanese|city pop|vocaloid"),
    ("Anime", r"anime"),
    ("Soundtrack", r"soundtrack|score|video game|musical|show tunes"),
    ("Latin", r"latin|reggaeton|urbano|baile funk|funk carioca|brazil|sertanejo|bachata|salsa|cumbia|corrido|mpb|pagode|forro"),
    ("Afrobeats", r"afro|amapiano|naija|nigerian|gqom|\balte\b|(?<!north )african|kwaito"),
    ("Reggae", r"reggae|dancehall|\bska\b"),
    ("Hip-Hop/Rap", r"hip.?hop|rap\b|\brap|drill|trap|grime|crunk|phonk|boom bap|plugg"),
    ("R&B/Soul", r"r&b|rnb|soul|\bfunk\b|motown|quiet storm"),
    ("Pop", r"dance pop|electropop|synthpop|synth-pop|indie pop|art pop|bedroom pop|hyperpop"),
    ("Dance/Electronic", r"dance|electro|house|techno|trance|edm|dubstep|drum.?n.?bass|dnb|jungle|\bbass\b|hardcore|hardstyle|garage|disco|club|breakbeat"),
    ("Rock/Alternative", r"rock|metal|punk|indie|alternative|emo|grunge|shoegaze"),
    ("Country", r"country|folk|bluegrass|americana"),
    ("Pop", r"pop|singer|chanson|schlager|bollywood|filmi"),
    ("World", r"world|arabic|maghreb|north african|afrikaans|indian|turkish|greek|celtic"),
]
CAT_RE = [(name, re.compile(rx, re.I)) for name, rx in CATS]
CATEGORY_NAMES = {name for name, _ in CATS} | {"Other"}

def genre_category(g):
    g = (g or "").strip()
    if not g:
        return ""
    if g in CATEGORY_NAMES:
        return g
    for name, rx in CAT_RE:
        if rx.search(g):
            return name
    return "Other"

# ---- CSV import (same rules as parseCSV / joinArtists in index.html) ----
def join_artists(s):
    s = str(s or "")
    parts = [p.strip() for p in re.split(r"\s*;\s*" if ";" in s else r"\s*\|\s*", s) if p.strip()]
    return ", ".join(parts[:-1]) + " & " + parts[-1] if len(parts) > 1 else (parts[0] if parts else "")

def read_csv(path):
    text = open(path, encoding="utf-8-sig", errors="replace").read()
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return []
    head = [h.lower().strip() for h in rows[0]]
    def col(*keys):   # keys in order of preference; link/ID columns (Exportify's "Artist URI(s)") never count
        for k in keys:
            for i, h in enumerate(head):
                if k in h and not re.search(r"\b(uri|url|id)s?\b|\buri\(s\)", h):
                    return i
        return -1
    ti, ai, yi, gi = col("track name", "title", "song", "name"), col("artist name", "artist"), col("release date", "year", "date"), col("genre")
    li, di = col("album name", "album"), col("duration (ms)", "duration")
    if ti < 0 or ai < 0:
        print(f"  skipped {os.path.relpath(path, ROOT)}: no title/artist columns", flush=True)
        return []
    out = []
    for r in rows[1:]:
        get = lambda i: r[i].strip() if 0 <= i < len(r) else ""
        t, a = get(ti), join_artists(get(ai))
        if not t or not a or t.lower() == "undefined" or a.lower() == "undefined":   # Exportify ends some exports with a blank "undefined" row
            continue
        y = re.match(r"\d{4}", get(yi))
        cats = [genre_category(g) for g in re.split(r"[;,]", get(gi)) if g.strip()]   # first tag that fits a real category
        g = next((c for c in cats if c != "Other"), cats[0] if cats else "")
        d = re.match(r"\d+", get(di))
        ms = int(d.group()) if d else 0
        # _al/_d (album, length in seconds) help pick the exact recording on iTunes; they aren't saved in playlists.json
        out.append({"t": t, "a": a, "y": int(y.group()) if y else 0, "g": g, "_al": get(li), "_d": round(ms / 1000) if ms > 1000 else ms})
    return out

def csv_hints():
    """{song key: (album, seconds)} from every playlist CSV, imported or not, for picking the right recording."""
    hints = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "playlists", "*", "*.csv")) + glob.glob(os.path.join(ROOT, "playlists", "*", "imported", "*.csv"))):
        for s in read_csv(path):
            if s["_al"] or s["_d"]:
                hints.setdefault(key(s), (s["_al"], s["_d"]))
    return hints

# ---- Tidy a list: categories, duplicates merged, sorted ----
def key(s):
    return (T.title_key(s["t"]), T.main_artist(s["a"]))

TAGGED = re.compile(r"remaster|radio edit|single version|album version|explicit", re.I)

def merge(a, b):
    """Fold b into a: keep the fuller artist credit (and its title), a title without remaster/edit tags,
    the earliest year, any genre and ID."""
    if len(str(b["a"])) > len(str(a["a"])):
        a["t"], a["a"] = b["t"], b["a"]
    if TAGGED.search(a["t"]) and not TAGGED.search(b["t"]):
        a["t"] = b["t"]
    if b.get("y") and (not a.get("y") or b["y"] < a["y"]):
        a["y"] = b["y"]
    if not a.get("g") and b.get("g"):
        a["g"] = b["g"]
    if not a.get("i") and b.get("i"):
        a["i"] = b["i"]
        if b.get("c"):
            a["c"] = b["c"]
        else:
            a.pop("c", None)

def tidy(songs, sort_key):
    seen, out = {}, []
    for s in songs:
        s["g"] = genre_category(s.get("g"))
        if not s["g"]:
            s.pop("g")
        k = key(s)
        if k in seen:
            merge(seen[k], s)
        else:
            seen[k] = s
            out.append(s)
    out.sort(key=sort_key)
    # tidy field order: t, a, y, g, i, c
    return [{f: s[f] for f in ("t", "a", "y", "g", "i", "c") if f in s and (s[f] or f == "i" or f == "y")} for s in out]

by_artist_title = lambda s: (str(s["a"]).lower(), str(s["t"]).lower())
by_year = lambda s: (s.get("y") or 0, str(s["a"]).lower(), str(s["t"]).lower())

# ---- Files ----
def load():
    data = json.load(open(PLAYLISTS, encoding="utf-8"))
    html = open(INDEX, encoding="utf-8").read()
    m = CHARTS_RE.search(html)
    # A chart row is [title, artist, year, genre, iTunes ID?, "GB"?]: no ID = not looked up yet, 0 = looked up, not found
    charts = [dict(zip(("t", "a", "y", "g", "i", "c"), r)) for r in json.loads(m.group(1))] if m else []
    return data, charts

def save(data, charts):
    rows = lambda songs: ",\n".join("  " + json.dumps(s, ensure_ascii=False, separators=(",", ":")) for s in songs)
    text = "{" + ",\n".join(f'"{who}":[\n{rows(songs)}\n]' for who, songs in data.items()) + "}\n"
    if open(PLAYLISTS, encoding="utf-8").read() != text:
        open(PLAYLISTS, "w", encoding="utf-8").write(text)
    html = open(INDEX, encoding="utf-8").read()
    if CHARTS_RE.search(html):
        arr = [[c["t"], c["a"], c.get("y") or 0, c.get("g") or ""] + ([c["i"]] if "i" in c else []) + (["GB"] if c.get("i") and c.get("c") == "GB" else [])
               for c in charts]
        new = CHARTS_RE.sub(lambda _: "const CHARTS=" + json.dumps(arr, ensure_ascii=False, separators=(",", ":")) + ";", html, count=1)
        if new != html:
            open(INDEX, "w", encoding="utf-8").write(new)

# ---- iTunes ----
def lookup_ids(lists, retry, hints=None):
    todo = {}
    for songs in lists:
        for s in songs:
            if "i" in s and not (retry and not s["i"]):
                continue
            todo.setdefault(key(s), []).append(s)
    if not todo:
        return 0
    by_artist = {}
    for k, copies in todo.items():
        by_artist.setdefault(k[1], []).append((k, copies[0]))
    print(f"looking up {len(todo)} songs by {len(by_artist)} artists", flush=True)
    found = 0
    for n, (artist, songs) in enumerate(by_artist.items(), 1):
        try:
            res = T.resolve_artist(songs[0][1]["a"], songs, hints or {})
        except Exception as e:
            print("  error:", songs[0][1]["a"], e, flush=True)
            continue
        for k, (tid, country, year) in res.items():
            for s in todo[k]:
                s["i"] = tid
                if country == "GB":
                    s["c"] = "GB"
                if year >= 1950 and (not s.get("y") or (year < s["y"] and s["y"] - year <= 40)):
                    s["y"] = year
            found += bool(tid)
        if n % 50 == 0:
            print(f"  {n}/{len(by_artist)} artists, {found} found", flush=True)
            yield_progress()
    print(f"found {found} of {len(todo)}", flush=True)
    return found

_progress = []
def yield_progress():
    for f in _progress:
        f()

def fill_genres(lists):
    """Songs with an ID but no genre take Apple's genre for that track (200 IDs per request)."""
    need = {}
    for songs in lists:
        for s in songs:
            if s.get("i") and not s.get("g"):
                need.setdefault(s.get("c") or "US", {}).setdefault(s["i"], []).append(s)
    filled = 0
    for country, ids in need.items():
        idl = list(ids)
        for i in range(0, len(idl), 150):
            for r in T.itunes({"id": ",".join(map(str, idl[i:i + 150])), "country": country}, "lookup"):
                g = genre_category(r.get("primaryGenreName"))
                for s in ids.get(r.get("trackId"), []):
                    if g and not s.get("g"):
                        s["g"] = g
                        filled += 1
    if filled:
        print(f"filled {filled} missing genres from Apple", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-lookup", action="store_true")
    ap.add_argument("--retry-missing", action="store_true")
    args = ap.parse_args()

    data, charts = load()

    # 1. CSV imports
    imported = []
    for who in data:
        have = {key(s) for s in data[who]}
        for path in sorted(glob.glob(os.path.join(ROOT, "playlists", who, "*.csv"))):
            new = [s for s in read_csv(path) if key(s) not in have]   # duplicates within the CSV are merged by tidy()
            keys = {key(s) for s in new}
            have |= keys
            data[who].extend(new)
            imported.append(path)
            print(f"imported {len(keys)} new songs for {who} from {os.path.relpath(path, ROOT)}", flush=True)

    # 2-3. Categories and duplicates
    def tidy_all():
        for who in data:
            data[who] = tidy(data[who], by_artist_title)
        charts[:] = tidy(charts, by_year)
    tidy_all()
    save(data, charts)
    for path in imported:   # saved, so park the CSV where it won't be imported again
        done_dir = os.path.join(os.path.dirname(path), "imported")
        os.makedirs(done_dir, exist_ok=True)
        os.replace(path, os.path.join(done_dir, os.path.basename(path)))

    # 4-5. iTunes IDs and missing genres (saved as it goes, so a long run never loses work)
    if not args.no_lookup:
        _progress.append(lambda: save(data, charts))
        lookup_ids(list(data.values()) + [charts], args.retry_missing, csv_hints())
        fill_genres(list(data.values()) + [charts])
        tidy_all()
        save(data, charts)

    total = sum(len(v) for v in data.values()) + len(charts)
    have = sum(1 for v in list(data.values()) + [charts] for s in v if s.get("i"))
    print(f"done: {', '.join(f'{w} {len(v)}' for w, v in data.items())}, charts {len(charts)}; {have}/{total} with iTunes IDs", flush=True)

if __name__ == "__main__":
    main()
