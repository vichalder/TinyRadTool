# TinyRadTool — macOS & Linux Standalone Port

Analog Devices Python GUI application for the **EV-TINYRAD24G** 24 GHz MIMO FMCW Radar Evaluation Platform (`idVendor=0x064B`, `idProduct=0x7823`), updated for native **macOS** (Apple Silicon & Intel) and **Linux** (x86_64 & ARM64) execution and standalone app distribution.

See [`PLAN.md`](PLAN.md) and [`docs/superpowers/specs/2026-11-25-tinyradtool-macos-linux-design.md`](docs/superpowers/specs/2026-11-25-tinyradtool-macos-linux-design.md) for the full REA reverse-engineering findings and architectural plan.

---

## Quick Start (Running from Source)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python TinyRadTool.py
```

---

## Building Standalone Distributable Apps

### Linux (`.tar.gz` bundle + `.deb` package + `udev` rules)
```bash
# Install udev rule for non-root USB access to EV-TINYRAD24G (064b:7823)
sudo cp packaging/linux/99-tinyrad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# Build standalone app bundle and .deb package
bash packaging/linux/build_linux.sh
```
Artifacts produced in `dist/`:
- `dist/TinyRadTool/TinyRadTool` (self-contained executable folder)
- `dist/TinyRadTool-linux-x86_64.tar.gz`
- `dist/tinyradtool_1.1.2_amd64.deb`

### macOS (`TinyRadTool.app` + `TinyRadTool-macOS.dmg`)
```bash
brew install libusb
bash packaging/macos/build_macos.sh
```
Artifacts produced in `dist/`:
- `dist/TinyRadTool.app` (bundles `libusb-1.0.dylib`, `config/*.rtc`, and `firmware/*.img`)
- `dist/TinyRadTool-macOS.dmg`

---

## Running Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -v
```
