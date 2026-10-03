# cam-proxy-pi-display

[![Release](https://img.shields.io/github/v/release/klaushofrichter/cam-proxy-pi-display?label=release&color=blue)](https://github.com/klaushofrichter/cam-proxy-pi-display/releases)
[![PR checks](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/pr-checks.yml/badge.svg)](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/pr-checks.yml)
[![Release workflow](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/release.yml/badge.svg?branch=production)](https://github.com/klaushofrichter/cam-proxy-pi-display/actions/workflows/release.yml)
[![Dependabot](https://img.shields.io/badge/dependabot-enabled-025E8C?logo=dependabot&logoColor=white)](https://github.com/klaushofrichter/cam-proxy-pi-display/security/dependabot)

<!-- The release badge is the newest tag, which the release workflow cuts from
     production. Dependabot is a static badge (it has no status endpoint);
     alerts and security updates are on in the repository settings, version
     updates come from .github/dependabot.yml. No version numbers in the text
     below: they go stale; the badge and the releases page carry them. -->

A small always-on status display for [cam-proxy](https://github.com/klaushofrichter/cam-proxy)
on a Raspberry Pi: a Python service that draws cam-proxy's health on a Waveshare
2.7 inch e-Paper HAT (V1) and handles its four keys. It answers "is everything fine?"
at a glance.

It reads only cam-proxy's local health API (`GET /api/local/health`, schema 1),
which answers on loopback only and carries no secrets. Everything on the display is
also on cam-proxy's Status page, with the same thresholds, so the two never disagree.
cam-proxy does not depend on this service; this service keeps running (and says
"proxy unreachable") when cam-proxy is down.

The first version is on its way in a pull request.

## License

MIT, see [LICENSE](LICENSE).
