#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Error: build_macos.sh must be run on macOS (Darwin)." >&2
    exit 1
fi

if [ ! -d "$ROOT_DIR/.venv" ]; then
    python3 -m venv "$ROOT_DIR/.venv"
    "$ROOT_DIR/.venv/bin/pip" install --upgrade pip
    "$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/requirements.txt"
fi

echo "==> [1/4] Generating macOS .icns icon from src/ressource/img/adi.png..."
ICONSET_DIR="$ROOT_DIR/build/TinyRadTool.iconset"
ICNS_PATH="$ROOT_DIR/build/TinyRadTool.icns"
rm -rf "$ICONSET_DIR" "$ICNS_PATH"
mkdir -p "$ICONSET_DIR"
for sz in 16 32 64 128 256 512; do
    sips -z $sz $sz "$ROOT_DIR/src/ressource/img/adi.png" --out "$ICONSET_DIR/icon_${sz}x${sz}.png" >/dev/null 2>&1 || true
done
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_PATH" >/dev/null 2>&1 || true

echo "==> [2/4] Building TinyRadTool.app with PyInstaller..."
"$ROOT_DIR/.venv/bin/pyinstaller" --noconfirm --clean "$ROOT_DIR/TinyRadTool.spec"

if [ -f "$ICNS_PATH" ]; then
    cp "$ICNS_PATH" "$ROOT_DIR/dist/TinyRadTool.app/Contents/Resources/TinyRadTool.icns" || true
fi

echo "==> [3/4] Signing TinyRadTool.app..."
SIGN_IDENTITY="${DEVELOPER_ID_APP:--}"
if [ "$SIGN_IDENTITY" = "-" ]; then
    echo "    Using ad-hoc signature (set DEVELOPER_ID_APP for Developer ID signing)."
    codesign --force --deep --sign - "$ROOT_DIR/dist/TinyRadTool.app"
else
    echo "    Using Developer ID: $SIGN_IDENTITY"
    codesign --force --deep --options runtime --timestamp --sign "$SIGN_IDENTITY" "$ROOT_DIR/dist/TinyRadTool.app"
fi

ARCH="$(uname -m)"
DMG_STAGE="$ROOT_DIR/build/dmg_stage"
DMG_OUT="$ROOT_DIR/dist/TinyRadTool-macOS-${ARCH}.dmg"
rm -rf "$DMG_STAGE" "$DMG_OUT"
mkdir -p "$DMG_STAGE"
cp -R "$ROOT_DIR/dist/TinyRadTool.app" "$DMG_STAGE/"
ln -s /Applications "$DMG_STAGE/Applications"

echo "==> [4/4] Creating distributable disk image: $DMG_OUT"
hdiutil create -volname "TinyRadTool" -srcfolder "$DMG_STAGE" -ov -format UDZO "$DMG_OUT"

if [ "$SIGN_IDENTITY" != "-" ]; then
    codesign --force --timestamp --sign "$SIGN_IDENTITY" "$DMG_OUT"
    if [ -n "${APPLE_ID:-}" ] && [ -n "${APPLE_TEAM_ID:-}" ] && [ -n "${APPLE_APP_PASSWORD:-}" ]; then
        echo "==> Submitting $DMG_OUT for Apple notarization..."
        xcrun notarytool submit "$DMG_OUT" \
            --apple-id "$APPLE_ID" \
            --team-id "$APPLE_TEAM_ID" \
            --password "$APPLE_APP_PASSWORD" \
            --wait
        xcrun stapler staple "$DMG_OUT"
    fi
fi

echo "==> macOS build complete! Artifacts in $ROOT_DIR/dist:"
ls -lh "$ROOT_DIR/dist"
