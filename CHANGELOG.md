# Changelog

## Unreleased

- When the daily 03:30 clear fails to reach the panel, it is tried again a minute later instead of being skipped until the next day.

## v2026.11.17.1

- Internal cleanup, no change to the pages: one definition of a problem item and of a health snapshot, shared Pi rows, dead code removed. `--once` no longer stops with an error when the Pi's own figures can't be read; it draws without them, like the service. A `--fake-panel` run no longer keeps every drawn image in memory.
- An answer from the proxy address that is not HTTP (a bad status line, for example) now shows as "bad answer" instead of stopping the service. If the service stops on an unexpected error, it still draws the stopped page and releases the panel.
- A health answer of an unexpected shape (a part that is not an object, a time out of range) no longer stops the drawing loop: the pages leave such parts off or show "?", and if a page still can't be drawn the error is logged and the panel keeps its last image.
- A draw that fails no longer counts as shown: a problem the panel could not draw is tried again a minute later (it used to wait for the 15-minute timer, and the failed draw counted against the hourly limit of problem redraws).
- A null text or label in cam-proxy's answer shows as empty (or the page's own fallback, such as the camera's online state) instead of the word "None".
- The Camera page no longer has a "PoE switch" row: cam-proxy no longer sends the switch (it moved to cams-admin), so the row was never shown.
- When cam-proxy's answer has no problem count, the Overview and the stopped page both count the flagged items, all of them: the stopped page used to say "All OK", and the Overview counted only the items that fit on the page.

## v2026.10.07.1

- The Overview keeps its summary line ("All OK" / "N problems") when cam-proxy lists more items than fit: the last items without a problem give way (the version first; it is on the Proxy page). cam-proxy's Archive item already made 11 items on the Pi, which pushed the summary off the screen; its SD card item (cam-proxy #199) makes 12.

## v2026.10.03.2

- Every time on the display carries its full date, as the screen may be read a day or more after it was drawn: the header says "updated Sat Oct 3 10:25", and online since, last frame, last clip, last data, up since, retention run and inventory run use the same format (local time, with each timestamp's own DST offset). The stopped page shows "Display stopped" with the date and time. The Camera page has "Since" and "Last clip" lines, and the clock offset next to the address; the Proxy page has "Inventory run".

## v2026.10.03.1

- First version: cam-proxy's health (local API, schema 1) on the Waveshare 2.7 inch e-Paper HAT (V1). Pages Overview (resting), Camera, Proxy (the installed version first) and Pi (works without the proxy from the Pi's own disk, CPU temperature and uptime); problem lines inverted; "updated HH:MM" on every page; "Display stopped HH:MM" on a normal stop.
- Keys (GPIO 5, 6, 13, 19 top to bottom, configurable): Camera, Proxy, Pi, and Update (short) / Overview (long press ≥ 2 s); presses during a draw are queued, the last wins; back to the Overview after 10 minutes.
- Refresh policy: 15-minute timer; the API polled every minute; problem changes redraw the Overview after 2 polls in a row, at most once per 5 minutes (coalesced) and 6 times an hour ("changing often"); the panel sleeps after every draw; a full clear daily at 03:30.
- systemd service as user `campdisplay` (groups spi, gpio), `deploy/install.sh` and `deploy/update.sh`; config `/etc/cam-proxy-pi-display.toml`; `--fake-panel DIR` and `--once PAGE` for development.
