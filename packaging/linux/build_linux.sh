#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="1.1.2"
ARCH="$(uname -m)"
if [ "$ARCH" = "x86_64" ]; then
    DEB_ARCH="amd64"
elif [ "$ARCH" = "aarch64" ]; then
    DEB_ARCH="arm64"
else
    DEB_ARCH="$ARCH"
fi

if [ -x "$ROOT_DIR/.venv/bin/pyinstaller" ]; then
    PYINSTALLER="$ROOT_DIR/.venv/bin/pyinstaller"
else
    PYINSTALLER="pyinstaller"
fi

echo "==> [1/3] Building standalone Linux bundle with PyInstaller..."
"$PYINSTALLER" --noconfirm --clean "$ROOT_DIR/TinyRadTool.spec"

cp "$ROOT_DIR/packaging/linux/99-tinyrad.rules" "$ROOT_DIR/dist/TinyRadTool/"
cp "$ROOT_DIR/packaging/linux/tinyradtool.desktop" "$ROOT_DIR/dist/TinyRadTool/"

TARBALL="$ROOT_DIR/dist/TinyRadTool-linux-${ARCH}.tar.gz"
echo "==> [2/3] Creating distributable tarball: $TARBALL"
tar -C "$ROOT_DIR/dist" -czf "$TARBALL" TinyRadTool

if command -v dpkg-deb >/dev/null 2>&1; then
    DEB_STAGE="$ROOT_DIR/build/deb_stage/tinyradtool_${VERSION}_${DEB_ARCH}"
    rm -rf "$DEB_STAGE"
    mkdir -p "$DEB_STAGE/DEBIAN"
    mkdir -p "$DEB_STAGE/opt/TinyRadTool"
    mkdir -p "$DEB_STAGE/usr/bin"
    mkdir -p "$DEB_STAGE/usr/share/applications"
    mkdir -p "$DEB_STAGE/usr/share/pixmaps"
    mkdir -p "$DEB_STAGE/lib/udev/rules.d"

    cp -a "$ROOT_DIR/dist/TinyRadTool/." "$DEB_STAGE/opt/TinyRadTool/"
    ln -sf /opt/TinyRadTool/TinyRadTool "$DEB_STAGE/usr/bin/tinyradtool"
    cp "$ROOT_DIR/packaging/linux/tinyradtool.desktop" "$DEB_STAGE/usr/share/applications/tinyradtool.desktop"
    cp "$ROOT_DIR/src/ressource/img/adi.png" "$DEB_STAGE/usr/share/pixmaps/tinyradtool.png"
    cp "$ROOT_DIR/packaging/linux/99-tinyrad.rules" "$DEB_STAGE/lib/udev/rules.d/99-tinyrad.rules"

    cat > "$DEB_STAGE/DEBIAN/control" <<EOF
Package: tinyradtool
Version: ${VERSION}
Section: science
Priority: optional
Architecture: ${DEB_ARCH}
Depends: libusb-1.0-0
Maintainer: TinyRadTool Maintainers <support@analog.com>
Description: Analog Devices EV-TINYRAD24G 24GHz Radar Evaluation GUI
 Standalone evaluation software and GUI for the Analog Devices EV-TINYRAD24G
 24GHz MIMO FMCW radar platform, including udev rules and firmware images.
EOF

    cat > "$DEB_STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v udevadm >/dev/null 2>&1; then
    udevadm control --reload-rules || true
    udevadm trigger || true
fi
EOF
    chmod 0755 "$DEB_STAGE/DEBIAN/postinst"

    DEB_OUT="$ROOT_DIR/dist/tinyradtool_${VERSION}_${DEB_ARCH}.deb"
    echo "==> [3/3] Building Debian/Ubuntu package: $DEB_OUT"
    dpkg-deb --build --root-owner-group "$DEB_STAGE" "$DEB_OUT"
else
    echo "==> [3/3] dpkg-deb not found; skipping .deb creation."
fi

echo "==> Build complete! Artifacts in $ROOT_DIR/dist:"
ls -lh "$ROOT_DIR/dist"
