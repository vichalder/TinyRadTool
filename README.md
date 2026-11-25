# TinyRadTool — Radar Evaluation Software (macOS & Linux)

**TinyRadTool** is the desktop application for controlling and viewing measurements from the **Analog Devices EV-TINYRAD24G** 24 GHz radar board.

---

## Step 1: Download the App

You do **not** need to install Python or know how to use programming tools to run TinyRadTool.

1. Go to the **[Latest Release page](https://github.com/vichalder/TinyRadTool/releases/latest)** (or click **Releases** on the right-hand side of this page).
2. Under the latest release, scroll down to **Assets** and download the file for your computer:
   - **Mac (M1, M2, M3, M4 / Apple Silicon):** `TinyRadTool-macOS-arm64.dmg`
   - **Mac (older Intel Macs):** `TinyRadTool-macOS-x86_64.dmg`
   - **Linux (Ubuntu / Debian, standard PC):** `tinyradtool_1.1.2_amd64.deb`

*(Not sure which Mac you have? Click the Apple menu **** in the top-left corner → **About This Mac**. If it says **Apple M1/M2/M3/M4**, pick `arm64`. If it says **Intel**, pick `x86_64`.)*

---

## Step 2: Install & Open

### On Mac
1. Open your **Downloads** folder and double-click the `.dmg` file you downloaded.
2. In the window that opens, drag **TinyRadTool** onto the **Applications** folder icon.
3. Open **Applications** (Finder → Applications) and double-click **TinyRadTool**.
4. **If macOS says the app cannot be opened (security warning):**
   - Click **Done** / **OK** on the popup.
   - Open **System Settings** → **Privacy & Security**.
   - Scroll down to the Security section where it mentions *TinyRadTool* and click **Open Anyway**, then confirm.
   - *(Alternatively, open the **Terminal** app and run: `xattr -cr /Applications/TinyRadTool.app`)*

### On Linux (Ubuntu / Debian)
1. Open your **Downloads** folder.
2. Double-click `tinyradtool_1.1.2_amd64.deb` to open it in Software Center and click **Install** (or open a terminal in Downloads and run `sudo apt install ./tinyradtool_1.1.2_amd64.deb`).
3. If your EV-TINYRAD24G radar board was already plugged in, **unplug and plug it back in** once so USB permissions take effect.
4. Open **TinyRadTool** from your application menu (or run `tinyradtool` in a terminal).

---

## Step 3: First-Time Use

1. Connect the **EV-TINYRAD24G** radar board to your computer with a USB cable.
2. Open **TinyRadTool**.
3. On first launch, a startup/license window will appear:
   - Check the box to accept the license agreement.
   - Click **OK**.
4. Choose a measurement mode (such as **FMCW** or **Range-Doppler**) in the main window to start using the radar.

---

## For Developers

### Running from Source

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python TinyRadTool.py
```

### Building Standalone Distributable Apps

#### Linux (`.tar.gz` bundle + `.deb` package + `udev` rules)
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

#### macOS (`TinyRadTool.app` + `TinyRadTool-macOS-<arch>.dmg`)
```bash
brew install libusb
bash packaging/macos/build_macos.sh
```
Artifacts produced in `dist/`:
- `dist/TinyRadTool.app` (bundles `libusb-1.0.dylib`, `config/*.rtc`, and `firmware/*.img`)
- `dist/TinyRadTool-macOS-<arch>.dmg` (`arm64` on Apple Silicon, `x86_64` on Intel)

> To produce signed and notarized builds, set `DEVELOPER_ID_APP`, `APPLE_ID`, `APPLE_TEAM_ID`, and `APPLE_APP_PASSWORD` before running `build_macos.sh` (or configure them as GitHub Actions secrets).

### Running Tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -v
```

See [`PLAN.md`](PLAN.md) and [`docs/superpowers/specs/2026-11-25-tinyradtool-macos-linux-design.md`](docs/superpowers/specs/2026-11-25-tinyradtool-macos-linux-design.md) for the full REA reverse-engineering findings and architectural plan.
