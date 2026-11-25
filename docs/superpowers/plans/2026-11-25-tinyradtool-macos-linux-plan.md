# TinyRadTool macOS & Linux Standalone Port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port Analog Devices' `TinyRadTool` to run natively on macOS and Linux (including modern Python 3.10–3.13+ and NumPy 2.x) and package it as standalone distributable apps (`.app`/`.dmg` for macOS, standalone bundle/`.tar.gz`/`.deb` for Linux).

**Architecture:** Introduce a cross-platform path, asset, and `libusb-1.0` backend resolver (`src/cmd_modules/PlatformPaths.py`); make `Connection.py`/`UsbADI.py`/`TinyRad.py` resilient when the radar USB device (`0x064B:0x7823`) is unplugged at startup while restoring the missing firmware-upgrade protocol (`0x6009`) and multi-packet USB reads recovered via REA; modernize all PyQt4/NumPy 1.x leftovers across `src/`; bundle the recovered `.rtc` configs and `.img` firmware images with PyInstaller build scripts for macOS and Linux.

**Tech Stack:** Python 3.10–3.12+, PyQt5 5.15+, pyqtgraph 0.13+, NumPy 1.24+/2.x, PyUSB 1.2+ (`libusb-1.0`), h5py 3.x, PyInstaller 6.x, pytest.

**Spec:** `docs/superpowers/specs/2026-11-25-tinyradtool-macos-linux-design.md`

## Global Constraints

- USB Hardware Target: Analog Devices Blackfin BF707 Bulk Device (`idVendor=0x064B`, `idProduct=0x7823`).
- Must start and render all GUI tabs (`FMCW`, `RangeDoppler`, `DBF`, `Target-Detection`, `Performance Estimation`, `System Config`, `Calibration`, `Firmware Upgrade`, `About`) even when no physical radar is connected via USB.
- Must work under both source execution (`python TinyRadTool.py`) and PyInstaller frozen bundles (`sys._MEIPASS`) regardless of current working directory.
- Zero reliance on removed NumPy 2.0 APIs (`np.fromstring` binary mode, `.tostring()`, `np.float`, `complex_`) or PyQt4-only APIs (`QtGui.QApplication`, `QtGui.QFileDialog`, `QtCore.SIGNAL`, `tkinter.filedialog`).

## Review Focus

1. **Startup without USB hardware attached:** `TinyRad()` instantiation during `StackGui.__init__()` must not raise an unhandled `IOError` or `usb.core.NoBackendError`; `BrdGetUID()` and `Dsp_GetSwVers()` must return `(False, ...)` / `-1` cleanly when offline.
2. **USB multi-packet `CmdRecv` (>128 bytes):** `Dsp_FmwrUpdtRdPt` reads 128 `uint32` words (516 bytes including 4-byte header); `Connection.CmdRecv()` must read the remaining `RecvLen` bytes instead of dropping them at 128 bytes.
3. **Config file typo in shipped `TinyRad-24.rtc`:** Line 58 of the official `TinyRad-24.rtc` has `PageRangeDopplerMeas_SetNrFrms(10ß000)` which silently fails regex parsing unless fixed to `10000`.
4. **PyQt5 `QFileDialog.getSaveFileName` return type:** Returns `(filename, selected_filter)` tuple in PyQt5; passing the tuple directly to `open()` raises `TypeError`.
5. **macOS Apple Silicon `libusb` discovery in frozen `.app`:** Homebrew installs `libusb-1.0.dylib` in `/opt/homebrew/lib` (not on default `dlopen` search path for GUI apps launched from Finder); `find_usb_backend()` must probe bundled frameworks and `/opt/homebrew/lib` / `/usr/local/lib`.

---

### Task 1: Cross-Platform Path, Config, Firmware & LibUSB Resolver (`PlatformPaths.py`) + Bundled Assets

**Files:**
- Create: `src/cmd_modules/PlatformPaths.py`
- Create: `config/TinyRad-24.rtc`
- Create: `config/Default.rtc`
- Create: `firmware/TinyRad-FW_R-2-6-1.img`
- Create: `firmware/TinyRad-FW_R-2-6-2.img`
- Create: `firmware/TinyRad-FW_R-3-0-1.img`
- Create: `firmware/TinyRad-FW_R-3-0-3.img`
- Test: `tests/test_cross_platform.py`

**Interfaces:**
- Produces:
  - `get_bundle_dir() -> pathlib.Path`
  - `get_resource_path(*parts: str) -> str`
  - `get_config_dirs() -> list[pathlib.Path]`
  - `get_default_config_dir() -> str`
  - `get_default_config_file() -> str`
  - `get_firmware_dirs() -> list[pathlib.Path]`
  - `find_usb_backend() -> object | None`
  - `center_window(widget) -> None`

- [ ] **Step 1: Write the failing test in `tests/test_cross_platform.py`**

```python
import os
import pathlib
from src.cmd_modules import PlatformPaths

def test_platform_paths_and_bundled_assets():
    bundle_dir = PlatformPaths.get_bundle_dir()
    assert (bundle_dir / "TinyRadTool.py").exists()
    logo = PlatformPaths.get_resource_path("src", "ressource", "img", "adi.png")
    assert os.path.isfile(logo)
    cfg_file = PlatformPaths.get_default_config_file()
    assert os.path.isfile(cfg_file)
    assert "10ß000" not in pathlib.Path(cfg_file).read_text(encoding="utf-8")
    fw_dirs = PlatformPaths.get_firmware_dirs()
    assert any((d / "TinyRad-FW_R-3-0-3.img").is_file() for d in fw_dirs)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_cross_platform.py::test_platform_paths_and_bundled_assets -v`
Expected: FAIL with `ImportError: cannot import name 'PlatformPaths'`

- [ ] **Step 3: Implement `src/cmd_modules/PlatformPaths.py` and fix `config/TinyRad-24.rtc` + `config/Default.rtc`**

Implement `PlatformPaths.py` resolving `sys._MEIPASS` or repo root, probing `/opt/homebrew/lib`, `/usr/local/lib`, `/opt/local/lib`, and bundled frameworks for `libusb-1.0`, and fixing `10ß000` -> `10000` in `config/TinyRad-24.rtc` and `config/Default.rtc`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_cross_platform.py::test_platform_paths_and_bundled_assets -v`
Expected: PASS

---

### Task 2: USB Transport Resilience, Multi-Packet `CmdRecv`, NumPy 2.x & Recovered Firmware Upgrade Protocol

**Files:**
- Modify: `src/cmd_modules/Connection.py`
- Modify: `src/cmd_modules/UsbADI.py`
- Modify: `src/cmd_modules/TinyRad.py`
- Modify: `src/cmd_modules/Computation.py`
- Modify: `src/cmd_modules/RadarProc.py`
- Modify: `src/cmd_modules/FileStore.py`
- Test: `tests/test_cross_platform.py`

**Interfaces:**
- Consumes: `PlatformPaths.find_usb_backend()`
- Produces:
  - `Connection.UsbOpen() -> bool` (non-fatal when device is absent; sets `self.hCon = -1`, `self.usbDev = None`)
  - `Connection.CmdRecv(dispError=True, stopOnError=False) -> np.ndarray | list` (supports multi-packet USB responses > 128 bytes)
  - `UsbADI.CmdExec(Ack, Cod, Data, Open=1) -> tuple[bool, np.ndarray]` (returns `(False, np.array([], dtype=np.uint32))` when offline)
  - `UsbADI.Dsp_FmwrUpdtRmFlsh()`, `UsbADI.Dsp_FmwrUpdtRdPt(Block, Sector, Addr)`, `UsbADI.Dsp_FmwrUpdtWrPt(Block, Sector, Addr, Data)`

- [ ] **Step 1: Write failing tests for offline USB init, multi-packet `CmdRecv`, firmware protocol, and `RadarProc` NumPy 2.x compatibility**

```python
import numpy as np
from src.cmd_modules import TinyRad, RadarProc

def test_offline_tinyrad_and_multipacket_cmdrecv():
    rad = TinyRad.TinyRad()
    assert rad.hCon == -1
    uid_ok, uid_data = rad.BrdGetUID()
    assert uid_ok is False
    vers = rad.BrdGetSwVers()
    assert vers["SwMaj"] == -1
    assert rad.FrmwrFlshNrBlcks == 64
    assert rad.FrmwrFlshSzSctrByts == 4096
    assert hasattr(rad, "Dsp_FmwrUpdtRmFlsh")
    assert hasattr(rad, "Dsp_FmwrUpdtRdPt")
    assert hasattr(rad, "Dsp_FmwrUpdtWrPt")

def test_radarproc_numpy2():
    proc = RadarProc.RadarProc()
    proc.CfgRangeProfile({"fs": 1e6, "kf": 1e12, "FFT": 256, "NIni": 1})
    data = np.ones((128, 4), dtype=np.float64)
    rp = proc.RangeProfile(data)
    assert rp.shape == (128, 4)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_cross_platform.py -k "test_offline_tinyrad or test_radarproc" -v`
Expected: FAIL with `OSError: Device not found.` and `ValueError` in NumPy 2.x.

- [ ] **Step 3: Update `Connection.py`, `UsbADI.py`, `TinyRad.py`, `Computation.py`, `RadarProc.py`, and `FileStore.py`**

- In `Connection.py`: use `PlatformPaths.find_usb_backend()`, catch `USBError`/`NoBackendError`/`IOError` in `__init__` and `UsbOpen`, implement multi-packet read when `RecvLen > 0` in `CmdRecv`, replace all binary `fromstring` with `frombuffer` and `.tostring()` with `.tobytes()`, and `numpy.float` with `np.float64`.
- In `UsbADI.py`: add `FrmwrFlsh*` constants and `Dsp_FmwrUpdtRmFlsh`/`Dsp_FmwrUpdtRdPt`/`Dsp_FmwrUpdtWrPt`, make `CmdExec` return `(True, Ret)` only when `len(Ret) > 0`, and guard `BrdGetCalDat` when offline.
- In `TinyRad.py`: guard `RfMeas` and `BrdGetData` when offline so no `IndexError` or `TypeError` occurs.
- In `RadarProc.py`, `Computation.py`, `FileStore.py`: replace `complex_` with `np.complex128`, `fromstring`/`tostring` with `frombuffer`/`tobytes`, and uncomment `import h5py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_cross_platform.py -v`
Expected: PASS

---

### Task 3: PyQt5 & Cross-Platform UI Modernization Across `src/ui/` and `src/proc_modes/`

**Files:**
- Modify: `TinyRadTool.py`
- Modify: `src/ui/StackGui.py`
- Modify: `src/ui/StrtupBrd.py`
- Modify: `src/ui/fwupgrd.py`
- Modify: `src/ui/about.py`
- Modify: `src/ui/setupBoard.py`
- Modify: `src/ui/ProgressBarDialog.py`
- Modify: `src/ui/ui_Strtup.py`
- Modify: `src/ui/ui_fwupgrd.py`
- Modify: `src/ui/ui_setupBoard.py`
- Modify: `src/ui/ui_ProgressBarDialog.py`
- Modify: `src/ui/proc_modes/ui_CfgStatus.py`
- Modify: `src/ui/proc_modes/ui_ModFmcw.py`
- Modify: `src/ui/proc_modes/ui_ModRangeDoppler.py`
- Modify: `src/ui/proc_modes/ui_ModBpa.py`
- Modify: `src/ui/proc_modes/ui_ModCal.py`
- Modify: `src/ui/proc_modes/ui_ModPerf.py`
- Modify: `src/ui/proc_modes/ui_ModTarDet.py`
- Modify: `src/proc_modes/ModFmcw.py`
- Modify: `src/proc_modes/ModRangeDoppler.py`
- Modify: `src/proc_modes/ModBpa.py`
- Modify: `src/proc_modes/ModTarDet.py`
- Modify: `src/proc_modes/ModCal.py`
- Modify: `src/proc_modes/ModPerf.py`
- Test: `tests/test_cross_platform.py`

**Interfaces:**
- Consumes: `PlatformPaths` functions
- Produces: Clean PyQt5 initialization of `StackGui`, `StrtupBrd`, `FwUpgrdDialog`, `AboutDialog`, `SetupBoard`, and all 7 mode pages (`ModFmcw`, `ModRangeDoppler`, `ModBpa`, `ModTarDet`, `ModPerf`, `CfgStatus`, `ModCal`).

- [ ] **Step 1: Write failing GUI instantiation & firmware image verification tests in `tests/test_cross_platform.py`**

```python
def test_gui_and_dialogs_headless(monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5 import QtWidgets
    import src.ui.StackGui as StackGui
    import src.ui.StrtupBrd as StrtupBrd
    import src.ui.fwupgrd as fwupgrd
    import src.ui.about as about

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(StrtupBrd.StrtupBrd, "exec_", lambda self: setattr(self.patre, "GuiAgree", True) or setattr(self.patre, "GuiSelIni", True))
    win = StackGui.StackGui()
    assert win.GuiAgree is True
    assert len(win.lView) >= 5
    fw_dlg = fwupgrd.FwUpgrdDialog(win)
    assert fw_dlg.FilesAvailable is True
    assert len(fw_dlg.lFile) >= 4
    abt_dlg = about.AboutDialog()
    assert "TinyRadTool" in abt_dlg.label_version.text()
    win.cleanUp()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_cross_platform.py::test_gui_and_dialogs_headless -v`
Expected: FAIL due to hardcoded `c:/Tools/TinyRadTool/` paths and unfound firmware/config files.

- [ ] **Step 3: Apply cross-platform UI & PyQt5 updates across `src/ui/` and `src/proc_modes/`**

- Use `PlatformPaths.get_default_config_file()` and `PlatformPaths.get_default_config_dir()` in `StackGui.py` and `StrtupBrd.py`.
- Use `PlatformPaths.get_firmware_dirs()` in `fwupgrd.py` so bundled `.img` files are discovered automatically.
- Use `PlatformPaths.get_resource_path("src", "ressource", "img", "adi.png")` across all UI files.
- Convert remaining `QtGui.*` widgets/dialogs/shortcuts/actions and `QtCore.SIGNAL` connections in `ui_ModTarDet.py`, `ModTarDet.py`, `ModBpa.py`, `ModCal.py`, `ProgressBarDialog.py`, `ui_ProgressBarDialog.py`, `ui_setupBoard.py`, `StackGui.py` to `QtWidgets.*` and `.connect(...)`.
- Replace `tkinter.filedialog` in `ModCal.py` with `QtWidgets.QFileDialog.getOpenFileName`, and unpack `(FileName, _)` from `QtWidgets.QFileDialog.getSaveFileName` in `ModFmcw.py`, `ModRangeDoppler.py`, `ModBpa.py`, `ModTarDet.py`.
- Uncomment `import h5py` in `ModFmcw.py`, `ModRangeDoppler.py`, `ModBpa.py`, `ModTarDet.py`, `ModPerf.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_cross_platform.py -v`
Expected: PASS

---

### Task 4: Standalone App Packaging Infrastructure (macOS `.app`/`.dmg` & Linux Bundle/`.deb`)

**Files:**
- Create: `requirements.txt` (UTF-8)
- Create: `pyproject.toml`
- Create: `TinyRadTool.spec`
- Create: `packaging/macos/build_macos.sh`
- Create: `packaging/linux/build_linux.sh`
- Create: `packaging/linux/99-tinyrad.rules`
- Create: `packaging/linux/tinyradtool.desktop`
- Create: `.github/workflows/build-releases.yml`
- Modify: `README.md`
- Create: `PLAN.md`

**Interfaces:**
- Produces:
  - `dist/TinyRadTool/TinyRadTool` (Linux standalone executable bundle) and `dist/TinyRadTool-linux-x86_64.tar.gz` / `dist/tinyradtool_1.1.2_amd64.deb` when `packaging/linux/build_linux.sh` is executed on Linux.
  - `dist/TinyRadTool.app` and `dist/TinyRadTool-macOS.dmg` when `packaging/macos/build_macos.sh` is executed on macOS.

- [ ] **Step 1: Create `TinyRadTool.spec`, `pyproject.toml`, `requirements.txt`, `packaging/macos/build_macos.sh`, `packaging/linux/build_linux.sh`, `99-tinyrad.rules`, `tinyradtool.desktop`, and `.github/workflows/build-releases.yml`**

Configure `TinyRadTool.spec` to bundle `config/*.rtc`, `firmware/*.img`, and `src/ressource/img/*`, dynamically include `libusb-1.0` shared library if present on the build host, and emit `BUNDLE(coll, name='TinyRadTool.app', bundle_identifier='com.analog.tinyradtool', ...)` on Darwin.

- [ ] **Step 2: Execute `packaging/linux/build_linux.sh` to verify the standalone build and test the built artifact**

Run: `bash packaging/linux/build_linux.sh`
Expected: Builds `dist/TinyRadTool/TinyRadTool`, `dist/TinyRadTool-linux-x86_64.tar.gz`, and `dist/tinyradtool_1.1.2_amd64.deb` with exit code 0.

- [ ] **Step 3: Run the full pytest suite to verify everything passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -v`
Expected: All tests PASS.
