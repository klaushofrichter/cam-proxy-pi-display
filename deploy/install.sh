#!/bin/sh
# Installs (or re-installs) cam-proxy-pi-display from this release on the Pi.
#
#   sudo deploy/install.sh            # from an unpacked release or a checkout
#
# Idempotent: creates the user campdisplay (groups spi, gpio), copies the release to
# /opt/cam-proxy-pi-display, installs the systemd unit and, only if there is none yet,
# the default config /etc/cam-proxy-pi-display.toml; then enables and (re)starts the
# service. Python packages come from Debian (no pip): python3-pil, python3-gpiozero,
# python3-lgpio, python3-spidev, fonts-dejavu-core.
set -eu

NAME=cam-proxy-pi-display
DEST=/opt/$NAME
CONFIG=/etc/$NAME.toml
UNIT=/etc/systemd/system/$NAME.service
USER_NAME=campdisplay

if [ "$(id -u)" != 0 ]; then
  echo "run with sudo: sudo $0" >&2
  exit 1
fi

SRC=$(cd "$(dirname "$0")/.." && pwd)
[ -f "$SRC/cam_proxy_pi_display/__main__.py" ] || { echo "no release found at $SRC" >&2; exit 1; }
VERSION=${CPPD_VERSION:-$(git -C "$SRC" describe --tags --exact-match 2>/dev/null || echo dev)}

echo "Installing $NAME $VERSION from $SRC"

# 1. Debian packages (checked, not installed).
missing=""
python3 -c 'import PIL' 2>/dev/null || missing="$missing python3-pil"
python3 -c 'import gpiozero' 2>/dev/null || missing="$missing python3-gpiozero"
python3 -c 'import lgpio' 2>/dev/null || missing="$missing python3-lgpio"
python3 -c 'import spidev' 2>/dev/null || missing="$missing python3-spidev"
[ -f /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf ] || missing="$missing fonts-dejavu-core"
if [ -n "$missing" ]; then
  echo "missing packages:$missing" >&2
  echo "install them with: sudo apt install$missing" >&2
  exit 1
fi
python3 -c 'import sys; sys.exit(sys.version_info < (3, 13))' || { echo "python3 3.13 or later needed" >&2; exit 1; }
for g in spi gpio; do
  getent group "$g" >/dev/null || { echo "group $g does not exist (is SPI enabled?)" >&2; exit 1; }
done
ls /dev/spidev0.0 >/dev/null 2>&1 || echo "warning: /dev/spidev0.0 not found: enable SPI (dtparam=spi=on) and reboot" >&2

# 2. The service user: no login, no home, only the spi and gpio groups.
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --system --user-group --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$USER_NAME"
  echo "created user $USER_NAME"
fi
usermod -a -G spi,gpio "$USER_NAME"

# 3. The code, replaced as a whole (root-owned, read-only for the service).
rm -rf "$DEST.new"
mkdir -p "$DEST.new"
cp -R "$SRC/cam_proxy_pi_display" "$SRC/deploy" "$DEST.new/"
for f in LICENSE NOTICE README.md CHANGELOG.md; do
  [ -f "$SRC/$f" ] && cp "$SRC/$f" "$DEST.new/"
done
printf '%s\n' "$VERSION" > "$DEST.new/VERSION"
find "$DEST.new" -name __pycache__ -type d -prune -exec rm -rf {} +
python3 -m compileall -q "$DEST.new/cam_proxy_pi_display" || true
chown -R root:root "$DEST.new"
chmod -R u=rwX,go=rX "$DEST.new"
chmod 0755 "$DEST.new/deploy/install.sh" "$DEST.new/deploy/update.sh"
if [ -d "$DEST" ]; then
  rm -rf "$DEST.old"
  mv "$DEST" "$DEST.old"
fi
mv "$DEST.new" "$DEST"
rm -rf "$DEST.old"

# 4. Config: never overwritten.
if [ ! -e "$CONFIG" ]; then
  install -m 0644 -o root -g root "$SRC/deploy/config.example.toml" "$CONFIG"
  echo "installed the default config $CONFIG"
else
  echo "kept the config $CONFIG"
fi

# 5. The unit.
install -m 0644 -o root -g root "$SRC/deploy/$NAME.service" "$UNIT"
systemctl daemon-reload
systemctl enable "$NAME" >/dev/null
systemctl restart "$NAME"

sleep 2
if systemctl is-active --quiet "$NAME"; then
  echo "$NAME $VERSION is running. Logs: journalctl -u $NAME -f"
else
  echo "$NAME did not start; see: journalctl -u $NAME -n 50" >&2
  exit 1
fi
