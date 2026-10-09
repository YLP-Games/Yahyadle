# Adding a playlist to Songdle

1. Export the playlist as a CSV:
   - **Spotify:** [Exportify](https://exportify.app)
   - **Apple Music:** [TuneMyMusic](https://www.tunemymusic.com) → export to file
2. On GitHub, open the folder for whoever it belongs to: `playlists/layla/` or `playlists/yahya/`.
3. Choose **Add file → Upload files** and commit the CSV.

That's it. The **Update Songdle songs** action (Actions tab) then does the rest automatically:
- adds the new songs to that person's library in `playlists.json`, skipping ones already there;
- sorts genres into Songdle's categories;
- merges duplicates;
- looks up iTunes IDs so the clips load quickly.

It commits the result and redeploys the site. A big playlist can take a while because Apple limits how fast songs can be looked up: roughly a minute per 25 new artists.

Any CSV with a title column and an artist column works. Once imported, the CSV moves to an `imported/` folder next to it, so it isn't imported twice. Imports only ever add songs. To take songs out of a library:

- **In Songdle:** after a round, songs that are only in Layla's library have a **Remove from my library** button. The song disappears from Songdle on that device straight away. Then use **Save … for everyone**, there or under Settings → Songdle, which opens GitHub with a file listing the removals. Tap **Commit changes**.
- **By hand:** add a text file to `playlists/layla/remove/` (or `playlists/yahya/remove/`), one song per line as `Title — Artist`.

The action removes those songs from the library, deletes the file and remembers them in `playlists/removed.json`, so a later import won't add them back.
