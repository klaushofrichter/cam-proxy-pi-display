#!/bin/sh
# Updates cam-proxy-pi-display to a release from GitHub (also does the first install).
#
#   sudo /opt/cam-proxy-pi-display/deploy/update.sh            # the latest release
#   sudo /opt/cam-proxy-pi-display/deploy/update.sh v2026.10.04.1
#
# Downloads the release's source archive and runs its deploy/install.sh, which keeps
# /etc/cam-proxy-pi-display.toml and restarts the service.
set -eu

REPO=klaushofrichter/cam-proxy-pi-display

if [ "$(id -u)" != 0 ]; then
  echo "run with sudo: sudo $0 [TAG]" >&2
  exit 1
fi

TAG=${1:-}
if [ -z "$TAG" ]; then
  TAG=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
    | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
fi
if ! printf '%s\n' "$TAG" | grep -Eq '^v[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$'; then
  echo "no valid release tag (got '${TAG}')" >&2
  exit 1
fi

INSTALLED=$(cat /opt/cam-proxy-pi-display/VERSION 2>/dev/null || echo none)
echo "installed: $INSTALLED, installing: $TAG"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL "https://github.com/$REPO/archive/refs/tags/$TAG.tar.gz" | tar -xz -C "$TMP" --strip-components=1
CPPD_VERSION=$TAG sh "$TMP/deploy/install.sh"
