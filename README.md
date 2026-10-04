# Yahyadle

**Play it here: https://layla310803.github.io/Yahyadle/**

Every "dle" guessing game Layla and Yahya play, in one page. Each game has a **Daily** puzzle (the same one for both of you) and an **Unlimited** mode, a sortable, filterable list of every answer, and its own look and series logo.

## Games

| Game | What you guess | How many (default settings) | Modes |
|---|---|---|---|
| Bleachdle | Bleach characters | 131 | Classic |
| Jujutsudle | Jujutsu Kaisen characters | 97 | Classic |
| Cloverdle | Black Clover characters | 78 | Classic |
| Hunterdle | Hunter x Hunter characters | 108 | Classic |
| Starwarsdle | Star Wars characters | 217 | Classic, with hints |
| Marveldle | MCU characters | 338 | Classic, with hints |
| Harry Potterdle | Characters, spells, places, quotes, descriptions | 121 characters | Classic, Spell, Location, Quote, Description |
| Planespottle | Aircraft from a zoomed-in photo | 454 | Make, model and airline |
| Songdle | Songs from a short audio clip | 2,099 + 1,488 library songs, 619 chart songs | Song |

## How to play

- **Classic:** guess a character and every column turns green (match), amber (partial match) or red (miss). Arrows point towards the answer for numbers and dates (higher / later, lower / earlier).
- **Hints:** Starwarsdle and Marveldle unlock hints after a set number of guesses; click one to reveal it.
- **Harry Potterdle:** also has Spell, Location, Quote and Description modes. Guess what's described; after 3 wrong guesses you get the first letter and length.
- **Planespottle:** the photo starts zoomed in and pans out with each guess. Pick the make, model and airline; you get 5 guesses. Photo captions that name the plane stay hidden until the round ends.
- **Songdle:**
  - The clip grows each guess: 0.1s, 0.5s, 2s, 8s, then 15s. Skip moves on to the next length.
  - Drag or tap the play bar (or use the arrow keys) to move around inside the part you've unlocked.
  - Each guess shows the song, artist and year. The artist box is green for exactly the same artists, orange when at least one artist matches and red otherwise.
  - Genre and Era filters choose which songs come up.
  - After a round you see which library the song is in, how many seconds of clip you needed, and optional Apple Music / Spotify buttons to save it.
- **Colour-blind colours** (under the guess grid) swaps green / amber / red for blue / orange / grey.

## Daily and Unlimited

The **Daily / Unlimited** switch sits next to the mode tabs. Songdle is Unlimited only.

- **Daily** gives one puzzle per game and mode each day, picked from the date, so you both get the same one. It works through the whole list before an answer repeats.
- **Saved progress:** reloading keeps your guesses. Once a daily is done, a countdown shows when the next one arrives.
- **Carry-over:** a daily that isn't finished by midnight stays until you finish it (win or give up), then you move on to the current day's. Missed days are skipped, so it's always one a day.
- **Unlimited** deals a random answer every round; **Shuffle** starts a new one.

## Settings

The gear button opens Settings, with a tab per game. Everything is saved on your device.

- **Bleachdle, Jujutsudle, Cloverdle, Hunterdle:** Anime only (default) or Anime + manga.
- **Starwarsdle:** switch individual shows on or off (Ahsoka, The Bad Batch, The Acolyte, Skeleton Crew, Maul - Shadow Lord).
- **Marveldle:** all movies or Phase 1-3 only, whether to include series-only characters, and a switch per series.
- **Harry Potterdle:** Books & movies, Books only or Movies only, applied to every mode.
- **Planespottle:** hide the plane list.
- **Songdle:**
  - which song lists to use (Layla's library, Yahya's library, Charts);
  - Connect Spotify, so the Add to Spotify button can save songs for you;
  - Add to my library buttons;
  - whether Skip carries on playing from where the music got to;
  - importing your own playlist.

Changing a setting re-deals rounds nobody has guessed in yet. The Daily keeps the shared answer unless it's been switched off, then moves to the next one.

Wins, streaks, daily progress, settings, the last game you played and the colour-blind setting are all saved in your own browser.

## Run it locally

```
python3 -m http.server 8765
```

Then open http://localhost:8765. Opening `index.html` straight from disk also works, but `quotes.json` and `playlists.json` can't load that way, so Songdle libraries, Marveldle quote hints and the Harry Potterdle quote, description and location text are missing.

Pushing to `main` deploys the site to GitHub Pages automatically (`.github/workflows/static.yml`).

## Files

| File | What's in it |
|---|---|
| `index.html` | The whole site: page, styles, game logic and the character, spell, aircraft and chart data |
| `quotes.json` | Marveldle quotes, plus Harry Potterdle quotes, descriptions and locations (edit these without touching the code) |
| `playlists.json` | Songdle libraries: `{"layla": [...], "yahya": [...]}`, each song `{"t": title, "a": artist, "y": year, "g": genre, "i": iTunes ID, "c": "GB" if UK-only}` |
| `logos/` | Series logos used for each game's title |
| `tools/itunes_ids.py` | Adds iTunes IDs to new songs in `playlists.json` |

## Songdle details

- **Audio:** free 30-second iTunes previews.
  - Songs with an iTunes ID load their clip with one exact lookup. 3,510 of the 3,587 library songs have one, and so do 134 chart songs.
  - Songs without an ID are searched by title and artist (US store, then UK). Covers, karaoke and remixes are skipped unless the song itself is one.
  - If a song has no preview, another is dealt automatically.
- **Speed:** while you play, the next song is picked and its clip loads in the background, so **Next song** starts instantly.
- **Both libraries on:** songs you both have are merged into one. They match on title and main artist, ignoring feat. credits, remaster or edit tags, accents and punctuation. After the round you see whether it's on both libraries or only one.
- **Libraries:** Layla's comes from her Spotify export. Yahya's is his Apple Music library, plus songs that are only in his playlists.
- **Charts:** each year's Billboard top 10 since 1970, plus extra hits.
- **Adding songs:**
  - Add them to `playlists.json`, then run `python3 tools/itunes_ids.py`. It only looks up songs without an ID, using each artist's iTunes catalogue (more reliable than song search), and corrects years to the original release. Add `--retry-missing` to retry songs it couldn't find before.
  - It paces itself to stay under Apple's request limits: a few new songs take seconds, the whole library about an hour.
  - Anyone can also import a playlist CSV in Settings → Songdle. That copy is saved on their device only.

## Data and credits

- **Character databases:** Bleach, JJK, Black Clover, Hunter x Hunter, Star Wars and Marvel come from the original dle sites. With the default Anime only setting, Jujutsudle and Hunterdle only include characters seen in the anime (JJK through season 3, HxH through the Election arc).
- **Harry Potterdle:** uses the site's character and spell lists, with details checked against the books. Each character, spell and place is tagged books, movies or both.
- **Character pictures:** load from each original dle site (Harry Potter pictures from the links in Harry Potterdle's list).
- **Planespottle:**
  - 242 photos from Planespottle's list: Wikimedia Commons photos, credited to each photographer.
  - 212 more aircraft by registration, with photos from the [Planespotters.net Photo API](https://planespotters.net/photo/api).
- **Series logos:** in `logos/`, from Wikimedia Commons, where they're listed as public domain because they're simple text logos. They're cropped and recoloured for the dark theme, and remain trademarks of their owners: [Bleach](https://commons.wikimedia.org/wiki/File:Bleach_(manga)_Logo.png), [Jujutsu Kaisen](https://commons.wikimedia.org/wiki/File:Jujutsu_Kaisen_logo.svg), [Black Clover](https://commons.wikimedia.org/wiki/File:Black_Clover_English_logo.png), [Hunter x Hunter](https://commons.wikimedia.org/wiki/File:Hunter_x_hunter.png), [Star Wars](https://commons.wikimedia.org/wiki/File:Star_wars_logo_alternate.svg), [Marvel](https://commons.wikimedia.org/wiki/File:Marvel_Studios_2016_logo.svg), [Harry Potter](https://commons.wikimedia.org/wiki/File:Harry_Potter_wordmark.svg). The "dle" beside each logo uses the closest free Google Font.
- **Song previews and IDs:** from the iTunes Search API.

Unofficial fan project, not affiliated with any of the original sites or rights holders.
