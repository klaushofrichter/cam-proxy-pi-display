# Changelog

## Unreleased

## v2026.10.03.2

- Every time on the display carries its full date, as the screen may be read a day or more after it was drawn: the header says "updated Sat Oct 3 10:25", and online since, last frame, last clip, last data, up since, retention run and inventory run use the same format (local time, with each timestamp's own DST offset). The stopped page shows "Display stopped" with the date and time. The Camera page has "Since" and "Last clip" lines, and the clock offset next to the address; the Proxy page has "Inventory run".

## v2026.10.03.1

- First version: cam-proxy's health (local API, schema 1) on the Waveshare 2.7 inch e-Paper HAT (V1). Pages Overview (resting), Camera, Proxy (the installed version first) and Pi (works without the proxy from the Pi's own disk, CPU temperature and uptime); problem lines inverted; "updated HH:MM" on every page; "Display stopped HH:MM" on a normal stop.
- Keys (GPIO 5, 6, 13, 19 top to bottom, configurable): Camera, Proxy, Pi, and Update (short) / Overview (long press ≥ 2 s); presses during a draw are queued, the last wins; back to the Overview after 10 minutes.
- Refresh policy: 15-minute timer; the API polled every minute; problem changes redraw the Overview after 2 polls in a row, at most once per 5 minutes (coalesced) and 6 times an hour ("changing often"); the panel sleeps after every draw; a full clear daily at 03:30.
- systemd service as user `campdisplay` (groups spi, gpio), `deploy/install.sh` and `deploy/update.sh`; config `/etc/cam-proxy-pi-display.toml`; `--fake-panel DIR` and `--once PAGE` for development.
