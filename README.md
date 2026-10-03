# Yahyadle

Every "dle" guessing game Layla and Yahya play, in one page. Each game picks a random character every round (no daily limit), and each has a sortable, filterable character list.

**Games:** Songdle (guess the song from a growing audio clip) · Bleachdle · Jujutsudle · Cloverdle · Hunterdle · Starwarsdle · Marveldle · Harry Potterdle (classic, spell, location, quote, description) · Planespottle

## Play
Visit https://layla310803.github.io/Yahyadle/, or run it locally from this folder:

```
python3 -m http.server 8765
```

then open http://localhost:8765. Opening `index.html` straight from disk also works, but `quotes.json` can't load that way, so Marveldle quote hints and the Harry Potterdle quote, description and location text fall back to the built-in versions.

## How it works
- Guess a character; each column turns green (match), amber (partial match) or red (miss). Arrows show whether the answer is higher/later or lower/earlier.
- **Shuffle new character** starts a fresh round.
- Wins, streaks, the last game you played and the colour-blind setting are saved in your own browser.
- **Colour-blind colours** (under the guess grid) swaps green / amber / red for blue / orange / grey.

## Data
- Bleach, JJK, Black Clover, Hunter x Hunter, Star Wars and Marvel use the character databases from the original dle sites.
- Jujutsudle and Hunterdle only include characters already seen in the anime (JJK through season 3, HxH through the Election arc).
- Harry Potterdle uses the site's character and spell lists, with details checked against the books. Quote mode uses paraphrased lines.
- Character pictures load from each original dle site, including Marveldle (Harry Potter pictures from the links in Harry Potterdle's list).
- Planespottle uses Planespottle's 242-photo list (Wikimedia Commons photos, credited to each photographer) plus extra aircraft with photos from the [Planespotters.net Photo API](https://planespotters.net/photo/api).

- Series logos in `logos/` are public-domain text logos from Wikimedia Commons, cropped and recoloured for the dark theme: [Bleach](https://commons.wikimedia.org/wiki/File:Bleach_(manga)_Logo.png), [Jujutsu Kaisen](https://commons.wikimedia.org/wiki/File:Jujutsu_Kaisen_logo.svg), [Black Clover](https://commons.wikimedia.org/wiki/File:Black_Clover_English_logo.png), [Hunter x Hunter](https://commons.wikimedia.org/wiki/File:Hunter_x_hunter.png), [Star Wars](https://commons.wikimedia.org/wiki/File:Star_wars_logo_alternate.svg), [Marvel](https://commons.wikimedia.org/wiki/File:Marvel_Studios_2016_logo.svg), [Harry Potter](https://commons.wikimedia.org/wiki/File:Harry_Potter_wordmark.svg). They remain trademarks of their owners. The "dle" beside each logo uses the closest free Google Font.

Unofficial fan project, not affiliated with any of the original sites or rights holders.

## Songdle
- Audio comes from free 30-second iTunes previews, looked up by song and artist (US store first, then the UK store). If a song has no preview, a new one is dealt automatically.
- Built-in chart pool with genre and era filters, or play your own playlists: export from Spotify (exportify.app) or Apple Music (tunemymusic.com) as CSV and import it in the Songdle tab, or add a shared `playlists.json` to the repo.
- `playlists.json` holds Yahya's Apple Music library (1,475 songs: music videos, a digital booklet and untagged local files removed, duplicates merged).
