# cam-proxy-pi-display

A Python service on the cam-proxy Raspberry Pi that draws cam-proxy's health on a Waveshare 2.7" e-Paper HAT (V1 driver `epd2in7`, landscape, 264×176) and handles its 4 keys. It reads only cam-proxy's local health API (`GET http://127.0.0.1:8480/api/local/health`, schema 1; the schema lives in cam-proxy's API docs). Design: `~/Development/reolink/epaper-display-design.md` (part B). README has pages, keys, refresh policy, install/update/uninstall.

## Commands

- `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt` (dev only).
- `scripts/fetch-test-fonts.sh` once (Debian's DejaVu build into `.fonts/`, as on the Pi), then `.venv/bin/pytest`, `.venv/bin/ruff check . && .venv/bin/ruff format --check .`, `shellcheck deploy/*.sh`.
- `UPDATE_GOLDEN=1 .venv/bin/pytest tests/test_render.py` after an intended layout change; `scripts/render_review.py OUT --scale 3` renders the review set.
- `python3 -m cam_proxy_pi_display --fake-panel DIR [--once PAGE] [--health-file FILE]`: PNGs instead of the panel.

## Rules

- **Public repo**: no secrets, tokens, LAN IPs or private host names anywhere (code, tests, docs, commit messages). Tests use 192.0.2.x and `example.test`. The PR check greps for private addresses.
- **Klaus reviews page images before panel changes**: any change to what a page looks like goes to him as PNGs (scaled 3×) before it is merged or drawn on the real panel. Regenerated goldens are part of that review.
- On the Pi: Debian packages only (python3-pil, python3-gpiozero, python3-lgpio, python3-spidev, fonts-dejavu-core); no pip. Python ≥ 3.13.
- Never `Clear` before a draw (init + clear 18 s vs. a 2.5 s draw); only the daily 03:30 clear. The panel sleeps after every draw. Only the service loop touches the panel.
- The install needs Klaus's sudo on the Pi; don't install or restart the service there without his go. Running the renderer as `admin` against the real panel only when asked (stop the service first; it owns the panel).
- The vendored driver (`cam_proxy_pi_display/vendor/waveshare_epd/`) stays unchanged, with its MIT notice; NOTICE names the source commit. Ruff excludes it.

## Branches and releases

- Feature branch → PR to `main` (checks `test`, `codeql`). `production` is protected (required `test` + `codeql`, strict, enforce_admins off); `main` is open.
- Release: PR `main` → `production`, merge; `.github/workflows/release.yml` tests the commit, tags `vYYYY.MM.DD.N` (America/Chicago) and writes notes from `## Unreleased`. No version in the sources (`VERSION` is written at install).
- Put user-visible changes under `## Unreleased` in CHANGELOG.md. The release does not clear it: after a release, move the entries under `## vYYYY.MM.DD.N` in a small PR (pull main first).
- Merge only when all checks pass (JSON check of `gh pr checks`, non-empty, all `pass`). Stage files explicitly.
