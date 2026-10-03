# cam-proxy-pi-display

[![Release](https://img.shields.io/github/v/release/klaushofrichter/cam-proxy-pi-display?label=release&color=blue)](https://github.com/klaushofrichter/cam-proxy-pi-display/releases)
[![PR checks](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/pr-checks.yml)
[![Release workflow](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/release.yml/badge.svg?branch=production)](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/release.yml)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-025E8C?logo=dependabot&logoColor=white)](https://github.com/klaushofrichter/cam-proxy-pi-display/security/dependabot)

<!-- The release badge is the newest tag, which the release workflow cuts from
     production. There is no image-build or deploy badge: this service builds
     no container image and has no deploy pipeline. A release is a tag plus
     GitHub's source archive, installed on the Pi by hand (see Install).
     Dependabot is a static badge (it has no status endpoint); alerts and
     security updates are on in the repository settings, version updates come
     from .github/dependabot.yml. No version numbers in the text below: they
     go stale; the badge and the releases page carry them. -->

A small always-on status display for [cam-proxy](https://github.com/klaushofrichter/cam-proxy)
on a Raspberry Pi: a Python service that draws cam-proxy's health on a Waveshare
2.7 inch e-Paper HAT (V1) and handles its four keys. It answers "is everything fine?"
at a glance.

It reads only cam-proxy's local health API (`GET /api/local/health`, schema 1),
which answers on loopback only and carries no secrets. Everything on the display is
also on cam-proxy's Status page, with the same thresholds, so the two never disagree.
cam-proxy does not depend on this service; this service keeps running (and says
"proxy unreachable") when cam-proxy is down.

## Related repos

- [cam-proxy](https://github.com/klaushofrichter/cam-proxy): the camera gateway on the
  same Pi. This service reads its `GET /api/local/health` and nothing else.
- [cams](https://github.com/klaushofrichter/cams): the web viewer for the cameras. It
  reads cam-proxy's client API; it doesn't talk to this service.
- [cam-sim](https://github.com/klaushofrichter/cam-sim): the camera simulator, which
  stands in for the camera in cams' and cam-proxy's tests and as `cam2` in the cluster.
  This service's tests use sample health answers instead (`tests/fixtures/`).

## Hardware

- Waveshare 2.7 inch e-Paper HAT, 264 × 176 px black/white, **V1 driver** (`epd2in7`).
  Used in landscape with the keys on the left. A full draw takes about 2.5 s and
  flashes; init plus a full clear about 18 s, so a draw never clears first.
- Pins: SPI0 (GPIO 8, 10, 11), RST 17, DC 25, BUSY 24; keys on GPIO 5, 6, 13, 19
  (top to bottom; active low with pull-ups; configurable).
- The panel keeps its image without power. Every page shows the time of its data,
  so a stale screen is visible.

## Pages

Every page has a header with the page name and **"updated Sat Oct 3 10:25"**: the screen
may be read a day or more after it was drawn, so every time on the display carries its
full date (weekday, month, day, 24 h time, local time zone). Problem lines are
inverted (white on black), matching the red lines on cam-proxy's Status page. A figure
the API reports as `null` is left off.

| Page | Shows |
|---|---|
| **Overview** (resting page) | The API's `items` as given (camera, live stream, events intake, camera FTP upload, storage, disk with a bar, CPU temperature, under-voltage, last inventory, version), then "All OK" or "N problems" (and "changing often", see below). When the proxy can't be reached: "Proxy unreachable", the reason, the time of the last data, and the Pi's own disk, CPU temperature, uptime and IP address. |
| **Camera** | Online state and since when, model, firmware, address and clock offset; stream and the time of the last frame; ONVIF events state and resubscribes; camera FTP state and the time of the last clip; the FTP stall check; the PoE switch port. |
| **Proxy** | **The installed proxy version first, in full** (or "unreachable"); up since; clips stored; FTP failures; storage writing or paused; recordings cache fill; viewers (SSE clients); last retention run; last inventory and when it ran. |
| **Pi** | Model, disk bar, free GB, CPU temperature, memory, uptime, load, under-voltage, IP address. Works without the proxy: disk, temperature and uptime are read directly. |

On a normal stop (systemd) the service draws a last page, **"Display stopped"** with its
date and time, and the time of the last data.

## Keys

The keys are on the left side of the landscape display.

| Key (top to bottom) | Short press | Long press (≥ 2 s) |
|---|---|---|
| 1 | Camera | — |
| 2 | Proxy | — |
| 3 | Pi | — |
| 4 (bottom) | **Update**: fresh data for the page shown | **Overview** |

- A key always fetches fresh data and draws at once.
- Presses during a draw are queued; the last one wins. The panel is never driven twice at once.
- 10 minutes after a key press the display returns to the Overview.

## Refresh policy

e-paper wears and flashes, so the panel is driven only when it says something new:

- **Timer**: every 15 minutes, the page shown is redrawn.
- **Polling**: the API is read every minute (5 s timeout) without touching the panel.
- **Problem changes** (a problem appears or clears, including "proxy unreachable") redraw the Overview, but:
  - the change must hold for **2 polls in a row** (a one-minute blip draws nothing);
  - at most **one problem redraw per 5 minutes**; a change inside that time is drawn when the 5 minutes end, as one redraw;
  - at most **6 problem redraws per hour**; past that only the 15-minute timer draws and the Overview says **"changing often"**, until the hour has room again.
- **Keys** draw at once (Waveshare's 180 s guidance is about unattended refreshes).
- The panel **sleeps after every draw**. A **full clear once a day at 03:30** (local time) against ghosting.

All of these are settings (below).

## Install on the Pi

Needs Debian 13 (Python 3.13) with SPI enabled (`dtparam=spi=on` in
`/boot/firmware/config.txt`, then a reboot), and these Debian packages (no pip):

```sh
sudo apt install python3-pil python3-gpiozero python3-lgpio python3-spidev fonts-dejavu-core
```

Then, as a user with sudo:

```sh
curl -fsSLO https://raw.githubusercontent.com/klaushofrichter/cam-proxy-pi-display/production/deploy/update.sh
sudo sh update.sh          # the latest release; or: sudo sh update.sh vYYYY.MM.DD.N
rm update.sh
```

`update.sh` downloads the release and runs its `deploy/install.sh`, which:

1. checks the packages, Python 3.13+, and the `spi` and `gpio` groups;
2. creates the system user **`campdisplay`** (no login, no home) in the groups `spi` and `gpio`;
3. copies the release to **`/opt/cam-proxy-pi-display`** (root-owned; `VERSION` holds the tag);
4. installs the default config **`/etc/cam-proxy-pi-display.toml`** if there is none (an existing one is kept);
5. installs **`/etc/systemd/system/cam-proxy-pi-display.service`**, enables and (re)starts it.

From a checkout or an unpacked release, `sudo deploy/install.sh` does the same with
that copy.

The service runs as `campdisplay`, never as root, with no network listener. The unit
is hardened (read-only system, no capabilities, no new privileges) without hiding
`/dev/spidev*` or `/dev/gpiochip*`.

## Update

The installed copy has the same script:

```sh
sudo /opt/cam-proxy-pi-display/deploy/update.sh            # the latest release
sudo /opt/cam-proxy-pi-display/deploy/update.sh vYYYY.MM.DD.N
```

Downloading `update.sh` again and running `sudo sh update.sh` (as in Install) does the
same. The config is kept. The restart draws "Display stopped", then the Overview.

## Configuration

`/etc/cam-proxy-pi-display.toml` ([example with the defaults](deploy/config.example.toml));
every setting is optional. After a change: `sudo systemctl restart cam-proxy-pi-display`.

| Setting | Default | |
|---|---|---|
| `api.url` | `http://127.0.0.1:8480/api/local/health` | cam-proxy's local health API |
| `api.timeout_s` | 5 | |
| `api.poll_interval_s` | 60 | |
| `keys.pins` | `[5, 6, 13, 19]` | BCM GPIOs, top to bottom; the last is Update/Overview |
| `keys.long_press_s` | 2.0 | |
| `keys.bounce_s` | 0.05 | |
| `refresh.timer_min` | 15 | |
| `refresh.return_to_overview_min` | 10 | |
| `refresh.problem_confirm_polls` | 2 | |
| `refresh.problem_min_interval_min` | 5 | |
| `refresh.problem_max_per_hour` | 6 | |
| `refresh.daily_clear` | `"03:30"` | local time |
| `display.fonts_dir` | `""` | empty: `/usr/share/fonts/truetype/dejavu` |

The time zone is the system's (`timedatectl`).

## Troubleshooting

- **Logs**: `journalctl -u cam-proxy-pi-display -f`. Each draw logs the page, the reason
  (start, key, timer, problem, return, clear) and the problems.
- **"Proxy unreachable"**: is cam-proxy running and on host networking? From the Pi:
  `curl -s http://127.0.0.1:8480/api/local/health | head -c 300`. The API answers only
  loopback; from another machine it looks like an unknown route.
- **"API schema N not supported"**: cam-proxy changed the API incompatibly; update this service.
- **The service doesn't start**: `systemctl status cam-proxy-pi-display`. Missing packages,
  SPI off (`ls /dev/spidev0.0`), or `campdisplay` not in `spi`/`gpio` (`id campdisplay`).
- **Keys do nothing**: check the pins in the config, and that no other process holds
  them (`gpioinfo`, from the `gpiod` package).
- **Ghosting**: the daily 03:30 clear removes it; a restart also redraws.
- **Draw one page by hand** (stop the service first, it owns the panel):

  ```sh
  sudo systemctl stop cam-proxy-pi-display
  cd /opt/cam-proxy-pi-display && python3 -m cam_proxy_pi_display --once pi
  sudo systemctl start cam-proxy-pi-display
  ```

## Uninstall

```sh
sudo systemctl disable --now cam-proxy-pi-display
sudo rm /etc/systemd/system/cam-proxy-pi-display.service
sudo systemctl daemon-reload
sudo rm -rf /opt/cam-proxy-pi-display /etc/cam-proxy-pi-display.toml
sudo userdel campdisplay
```

The panel keeps its last image ("Display stopped").

## Development

On a Mac or in CI, `--fake-panel DIR` writes PNGs instead of driving the panel, and
`--once PAGE` draws one page and exits:

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
scripts/fetch-test-fonts.sh
.venv/bin/python -m cam_proxy_pi_display --fake-panel out --once overview \
    --health-file tests/fixtures/pi-ok.json
.venv/bin/python -m cam_proxy_pi_display --fake-panel out --config my.toml   # the service, against a cam-proxy
```

- `pytest` runs everything: config, collector (against a local HTTP server), local
  figures, the refresh policy on a fake clock (blips, coalescing, the hourly cap, the
  daily clear), keys (logic and gpiozero's mock pins), the service loop, the CLI, and
  **golden images** of every page in OK and problem states (`tests/golden/`).
- The tests need the DejaVu fonts as the Pi has them: `scripts/fetch-test-fonts.sh` puts
  the two files from Debian 13's `fonts-dejavu-core` (pinned by checksum) into `.fonts/`,
  where the tests find them. Debian builds these fonts from source, so other builds move
  pixels in the golden images.
- After an intended layout change: `UPDATE_GOLDEN=1 pytest tests/test_render.py`, then
  look at the images. `scripts/render_review.py OUT --scale 3` renders the review set
  scaled up for reading on a screen.
- `ruff check . && ruff format --check .` for lint.
- The code is a plain package (`cam_proxy_pi_display/`), run with `python3 -m`; on the Pi
  only Debian's `python3-pil`, `python3-gpiozero`, `python3-lgpio` and `python3-spidev`.

### Layout

| Module | |
|---|---|
| `collector.py` | the API (schema check, short error reasons) and the problem set |
| `localstats.py` | the Pi's own disk, CPU temperature, uptime, model, IP (direct reads, no shell-outs) |
| `render.py` | pure: data + page + time → 264×176 1-bit image |
| `policy.py` | pure: when to draw (timer, problem changes and their limits, return, daily clear) |
| `panel.py` | the V1 panel (init, draw, sleep) or the PNG fake |
| `keys.py` | the four keys (gpiozero), short and long press |
| `service.py` | the loop: keys, polls, policy, draws, the stop page |

## Releases

Work goes to `main` through pull requests (checks `test` and `codeql`). A release is a
PR `main` → `production`; the release workflow tests that commit, tags it
`vYYYY.MM.DD.N` (America/Chicago date, N counts that day's releases) and writes the
release notes from `CHANGELOG.md`'s Unreleased section. The release is the tag and
GitHub's source archive; `deploy/update.sh` installs it on the Pi. Nothing deploys on
its own: there is no container image and no deploy job, and a release reaches the Pi only
when someone runs `update.sh` there.

## License

MIT, see [LICENSE](LICENSE). Includes Waveshare's `epd2in7` driver and `epdconfig`
(MIT), copied unchanged from [waveshareteam/e-Paper](https://github.com/waveshareteam/e-Paper)
commit `a794fbc`; see [NOTICE](NOTICE).
