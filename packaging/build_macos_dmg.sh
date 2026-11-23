#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="LNG Simulator.app"
DMG_NAME="LNG-Simulator-macOS-arm64.dmg"
APP_PATH="$ROOT_DIR/dist/$APP_NAME"
DMG_PATH="$ROOT_DIR/dist/$DMG_NAME"
STAGING_DIR="$(mktemp -d "${TMPDIR:-/tmp}/lng-dmg-staging.XXXXXX")"

cleanup() {
  rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

echo "[1/4] Running PyInstaller (arm64)..."
python3 -m PyInstaller --clean --noconfirm "$ROOT_DIR/packaging/lng_simulator.spec"

if [[ ! -d "$APP_PATH" ]]; then
  echo "ERROR: Expected app bundle not found at $APP_PATH" >&2
  exit 1
fi

echo "[2/4] Ad-hoc signing $APP_NAME for Apple Silicon..."
codesign --force --deep --sign - "$APP_PATH"

echo "[3/4] Preparing DMG staging folder..."
ditto "$APP_PATH" "$STAGING_DIR/$APP_NAME"
ln -s /Applications "$STAGING_DIR/Applications"

echo "[4/4] Creating and verifying $DMG_NAME..."
rm -f "$DMG_PATH"
hdiutil create \
  -volname "LNG Simulator" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

hdiutil verify "$DMG_PATH"
echo "Done: $DMG_PATH ($(du -sh "$DMG_PATH" | awk '{print $1}'))"
