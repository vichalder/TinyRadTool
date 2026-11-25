# TinyRadTool macOS & Linux Standalone Port — Design Specification

## 1. Intent & Why
Analog Devices' `TinyRadTool` is the evaluation GUI for the EV-TINYRAD24G (24 GHz FMCW/MIMO radar evaluation board based on Blackfin BF707, ADF4159 PLL, ADF5901 2-Ch TX, ADF5904 4-Ch RX, and ADAR7251 4-Ch 16-bit ADC).
Historically, it was distributed only as a 32-bit Windows executable (`TinyRadTool-x32.exe`) with a custom WinUSB wrapper (`usb.dll`). In 2023, Analog Devices published a partially migrated Python 3 / PyQt5 repository (`analogdevicesinc/TinyRadTool`), but left multiple Windows-only dependencies, missing firmware-upgrade routines, unbundled `.rtc`/`.img` assets, PyQt4 leftovers, and deprecated NumPy 1.x APIs that prevent it from running or being packaged on macOS and Linux.

The goal of this project is to:
1. Document the complete hardware/USB protocol and software architecture recovered via REA (`reverse-engineer-anything`).
2. Make `TinyRadTool` run natively and reliably on **macOS** (Intel & Apple Silicon) and **Linux** (x86_64 / ARM64) with modern Python (3.10–3.13+), NumPy (1.24+ / 2.x), PyQt5, pyqtgraph, pyusb (`libusb-1.0`), and h5py.
3. Provide complete build infrastructure in this repository to produce standalone distributable applications for macOS (`.app` bundle and `.dmg` disk image) and Linux (standalone bundle, `.tar.gz`, and `.deb` package with `udev` rules).

---

## 2. REA Reverse-Engineering Evidence & Findings

### 2.1 Shipped Release Package (`TinyRadToolAndDriver.zip`)
- **REA Evidence IDs:**
  - Archive Inventory Summary: `ev_022d950ce319f10c2885a16cd2494d540206b43d6683853ac6b196a83f7a28bc` (parent `ev_0291d499a1a0b06ec4b66abb79e3704eacc509bdc2745f2178e5750ed74a8957`, manifest `agm_b043a1ec88f61744c61caffadb989b23f25aad62dbb76792370a7a5d1c01bd8e`, SHA-256 `b6e5ec2866ce153d1fd549f0aef91686b3350a5ac8feea66f9aeeae3e5faf04f`)
  - Extracted Artifact Graph: `ev_04437bb1e9797b9329149008e5a5d9957d5e7e83097f44b3ee853366276f544e` (327 files across 93 directories)
- **Key Contents Discovered in Release Archive (Absent from Git Repo):**
  - `Software/v6/TinyRadTool/TinyRad-24.rtc` (5,787 bytes): Default radar GUI configuration file (contains a syntax typo on line 58: `PageRangeDopplerMeas_SetNrFrms(10ß000)` which must be corrected to `10000`).
  - `Software/v6/TinyRadTool/TinyRad-FW_R-2-6-1.img`, `TinyRad-FW_R-2-6-2.img`, `TinyRad-FW_R-3-0-1.img`, `TinyRad-FW_R-3-0-3.img` (~4.25 MB each): Pickled `FirmwareImage` objects containing 64 flash blocks × 16 sectors × 4,096 bytes/sector + SHA-256 integrity digest.
  - `Demo_Driver.zip` -> `Demo_Driver/WinUSB_adi.inf`: Confirms USB device identity is **VID `0x064B`, PID `0x7823`** ("ADI Vendor Specific USB Device", Blackfin BF707 Bulk Device, Interface GUID `{E63702F7-ADB0-4991-A6E3-A1AC0D274644}`). Note that `Docu/TinyRad_Python.pdf` contains an erroneous Cypress VID/PID (`04b4:00f1`) in its Linux `udev` example; the real hardware uses `064b:7823`.
  - `Software/v6/TinyRadTool/TinyRadTool-x32.exe` (20,240,597 bytes): A UPX-packed 7-Zip SFX archive (7z signature at file offset `109837`) containing a Python 3.4 `cx_Freeze` build (`dist32/`).

### 2.2 Native WinUSB Driver Wrapper (`usb.dll`)
- **REA Evidence IDs:**
  - Binary Overview: `ev_d58ff69169cc22e415cf59617ba9a5a6d61657f8a5856b98e95950ffb4470a6b` (PE32 x86, SHA-256 `b048454763fa88f029f32e081adb3643beb3372e3d759d88c9dce8e2388cb3c3`, 1,503 procedures, 787 strings)
  - Procedure Search: `ev_d36700603ce47ea5a98d997dbbc5c1ae60ea6fbe3fde58bb74658c471f1f4e08`, `ev_04b1a8f3b762f7d79d7ddd551b46fd958d4898398bb372c2b4f975d8532ad52e`
  - Function Dossiers:
    - `exp_UsbWriteCmd` (`0x100020e0`): `ev_742fd52c007a8b7795e283fd3977ebe8c3210c1eb262a17d3877fb31557e5dd2`
    - `exp_UsbWriteADICmd` (`0x100021d0`): `ev_41e473d74de86751ffaef3a829e799d22a31f6c1be2f4630ab7dcfb1fa3810c2`
    - `exp_UsbRead` (`0x100022b0`): `ev_eef1a5b9e48a5f15627ad45130ee649ae8d6e385e9dea2279238fd86199145cd`
- **USB Wire Protocol Verified via `exp_UsbWriteCmd` & `exp_UsbRead`:**
  - Commands are arrays of 32-bit unsigned integers (`uint32_t cmd[]`) where `cmd[0] = (Ack << 24) | (LenWords << 16) | CmdCode`.
  - `exp_UsbWriteCmd` allocates a fixed `0x800` (2,048-byte) buffer (`EMGUSBCB`), writes the 16-bit byte payload length (`LenWords * 4`) at offset `0..1` (`*(int16_t *)esi = edx`), serializes each 32-bit word in little-endian order starting at byte offset `2`, and sends all 2,048 bytes to the Bulk OUT pipe.
  - `exp_UsbRead` reads raw bytes from the Bulk IN pipe. Command responses begin with a 4-byte header `Header[0]` where `LenWords = Header[0] >> 16`, followed by `(LenWords - 1) * 4` payload bytes. For radar measurement frames (`0x9032` `Dsp_GetDat`), between `CmdSend` and `CmdRecv`, the device streams `Len * 2` bytes of signed 16-bit (`int16`) IF ADC samples across 4 channels on the Bulk IN pipe.

### 2.3 Linux RadServe Binary (`RadServeConsole`) & Decompiled `dist32/src/cmd_modules/UsbADI.pyc`
- **REA Evidence IDs:**
  - `RadServeConsole` Overview & Strings: `ev_5f506f4db201fb0d567a45655492f2d752d33bce61d1bab6ba1490e22bce735c`, `ev_7dc058e8ecfae69d8e962399f10ecdcf5b46f973e51323d83626d9ef9eca0da1` (ELF64 x86-64, SHA-256 `738940d90f3478a1a223119a6d48cf5c4e925840233d50c86620aaee7dd71582`).
- **Missing Firmware Upgrade Commands Recovered from `dist32/src/cmd_modules/UsbADI.pyc`:**
  - The GitHub repo's `src/ui/fwupgrd.py` references flash geometry constants and DSP command methods that were accidentally omitted when `src/cmd_modules/UsbADI.py` was rewritten in 2023:
    - `FrmwrFlshNrBlcks = 64`, `FrmwrFlshNrSctrs = 16`, `FrmwrFlshSzSctr = 1024`, `FrmwrFlshSzSctrByts = 4096`, `FrmwrRdSz = 128`
    - `Dsp_FmwrUpdtRmFlsh()`: Sends command `0x6009` with `[1, 0, 0, 0, 0, 0]`, sleeps 15s while flash erases, then calls `CmdRecv()`.
    - `Dsp_FmwrUpdtRdPt(Block, Sector, Addr)`: Sends command `0x6009` with `[1, 1, Block, Sector, Addr, FrmwrRdSz]` and receives 128 `uint32` words (512 bytes + 4-byte header = 516 bytes).
    - `Dsp_FmwrUpdtWrPt(Block, Sector, Addr, Data)`: Sends command `0x6009` with `[1, 2, Block, Sector, Addr, FrmwrRdSz, *Data]` and receives ACK.
  - Because `Dsp_FmwrUpdtRdPt` returns 516 bytes (> 128 bytes), the unfinished `# todo append data` in `Connection.py:508` (`if RecvLen > 0:`) must be completed to read the remaining `RecvLen` bytes from `usbRdEp`.

---

## 3. Goals, Non-Goals & Constraints

### Goals
- **Offline-Safe Startup & Reconnection:** Launching `TinyRadTool` without a physical EV-TINYRAD24G plugged in must open the GUI cleanly (logging that the board is offline) and allow reconnecting when `Initialize`, `Get Status`, or `Start Upgrade` is clicked.
- **Cross-Platform Resource & Config Resolution:** Replace all hardcoded `c:/Tools/TinyRadTool/` and relative `src/ressource/img/` paths with a unified `src/cmd_modules/PlatformPaths.py` resolver that works both from source and inside frozen PyInstaller bundles (`.app` on macOS, AppDir/binary on Linux).
- **Modern Python / NumPy 2.x / PyQt5 Compatibility:**
  - Replace all binary `fromstring(...)` calls with `np.frombuffer(...)` (and string-to-uint32 packing with `.encode('latin-1')` + `np.frombuffer`).
  - Replace all `.tostring()` calls with `.tobytes()`, `np.float` with `float`, and `complex_` with `np.complex128`.
  - Complete the PyQt4 -> PyQt5 migration (`ui_ModTarDet.py`, `ModTarDet.py`, `ModBpa.py`, `ModCal.py`, `ProgressBarDialog.py`, `ui_ProgressBarDialog.py`, `ui_setupBoard.py`, `Computation.py`), fix `QFileDialog.getSaveFileName` tuple unpacking, and replace `tkinter.filedialog` in `ModCal.py` with `QtWidgets.QFileDialog.getOpenFileName`.
  - Enable `h5py` imports across all measurement modules and `FileStore.py`.
- **Standalone App Packaging:**
  - **macOS:** PyInstaller `.app` bundle (`TinyRadTool.app`) and `.dmg` installer via `packaging/macos/build_macos.sh`, including automatic `libusb-1.0.dylib` bundling for both Apple Silicon (`/opt/homebrew`) and Intel (`/usr/local`).
  - **Linux:** Standalone PyInstaller bundle, `.tar.gz` archive, `.deb` package, `.desktop` launcher, and `99-tinyrad.rules` `udev` configuration via `packaging/linux/build_linux.sh`.
  - **CI/CD:** GitHub Actions workflow (`.github/workflows/build-releases.yml`) building macOS and Linux artifacts automatically.

### Non-Goals
- Rewriting the GUI in a web framework or changing the scientific radar signal processing algorithms (`RadarProc.py`, `DevAdf4159.py`, `DevAdf5901.py`, `DevAdf5904.py`).
- Requiring proprietary `RadServe` daemons when direct `pyusb` (`libusb-1.0`) communication is used.

---

## 4. Approaches Considered

1. **Approach A (Selected): Modernize the existing PyQt5 + PyUSB codebase and package with PyInstaller.**
   - *Pros:* Preserves 100% of Analog Devices / Inras GmbH's FMCW, Range-Doppler, DBF/MIMO Backprojection, Target Detection, Performance Estimation, Calibration, and Firmware Upgrade views; produces native `.app`/`.dmg` on macOS and standalone ELF bundle/`.deb` on Linux; zero external runtime dependencies for end users.
   - *Cons:* Requires fixing ~25 files with PyQt4/NumPy 1.x/Windows-path technical debt.
2. **Approach B: Use `cx_Freeze` (as in the 2019 32-bit Windows build).**
   - *Rejected:* `cx_Freeze` has weaker macOS `.app` bundle, `libusb` dylib relocation, and Qt5 plugin bundling support compared to modern `PyInstaller 6.x`.
3. **Approach C: Rewrite GUI in DearPyGui / Web UI.**
   - *Rejected:* Unnecessary rewrite risk and loss of exact feature parity with official ADI Application Notes.

---

## 5. Architecture of the Changes

- `src/cmd_modules/PlatformPaths.py`: Central path & USB backend resolver (`get_bundle_dir`, `get_resource_path`, `get_config_dirs`, `get_default_config_dir`, `get_firmware_dirs`, `find_usb_backend`, `center_window`).
- `src/cmd_modules/Connection.py` & `src/cmd_modules/UsbADI.py` & `src/cmd_modules/TinyRad.py`:
  - Non-fatal USB initialization (`UsbOpen()` catches `usb.core.USBError` / `IOError` / `NoBackendError` and sets `self.hCon = -1`, `self.usbDev = None`; automatically retries `UsbOpen()` on command send).
  - Complete multi-packet `CmdRecv()` for payloads > 128 bytes.
  - Consistent `(bool, ndarray)` return tuple in `UsbADI.CmdExec()` (returns `(False, np.array([], dtype=np.uint32))` when board is offline/unresponsive).
  - Restored `FrmwrFlsh*` constants and `Dsp_FmwrUpdtRmFlsh`, `Dsp_FmwrUpdtRdPt`, `Dsp_FmwrUpdtWrPt` methods in `UsbADI.py`.
- `src/ui/*` & `src/proc_modes/*`:
  - Cross-platform paths via `PlatformPaths`.
  - Complete PyQt5 widget/signal/dialog compatibility and NumPy 2.x buffer APIs.
- `TinyRadTool.spec`, `packaging/macos/build_macos.sh`, `packaging/linux/build_linux.sh`, `packaging/linux/99-tinyrad.rules`, `packaging/linux/tinyradtool.desktop`, `.github/workflows/build-releases.yml`:
  - Reproducible one-command builds for macOS and Linux.
