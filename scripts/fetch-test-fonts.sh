#!/bin/sh
# Puts DejaVuSans.ttf and DejaVuSans-Bold.ttf from Debian's fonts-dejavu-core 2.37-8
# (the package on the Pi, Debian 13) into .fonts/, for the golden-image tests.
# Debian builds these fonts from source, so they differ from the upstream release
# files and from other distributions' builds; the goldens are drawn with exactly these.
#
#   scripts/fetch-test-fonts.sh        # then: pytest (tests/conftest.py finds .fonts/)
set -eu

URL=https://deb.debian.org/debian/pool/main/f/fonts-dejavu/fonts-dejavu-core_2.37-8_all.deb
SHA256=86635b3d25b3655fc11cb3ecc3af59f0bf19643b02b94f2de48bd10253cdba12

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$ROOT/.fonts
if [ -f "$OUT/DejaVuSans.ttf" ] && [ -f "$OUT/DejaVuSans-Bold.ttf" ]; then
  echo "$OUT already has the fonts"
  exit 0
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
curl -fsSL -o "$TMP/fonts.deb" "$URL"
if command -v sha256sum >/dev/null 2>&1; then
  got=$(sha256sum "$TMP/fonts.deb" | cut -d' ' -f1)
else
  got=$(shasum -a 256 "$TMP/fonts.deb" | cut -d' ' -f1)
fi
[ "$got" = "$SHA256" ] || { echo "checksum mismatch: $got" >&2; exit 1; }
(cd "$TMP" && ar x fonts.deb && tar -xf data.tar.xz ./usr/share/fonts/truetype/dejavu/DejaVuSans.ttf ./usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf)
mkdir -p "$OUT"
cp "$TMP/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf" "$TMP/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" "$OUT/"
echo "fonts in $OUT"
