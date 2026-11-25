# Plan & Arkitektur: TinyRadTool til macOS og Linux

Dette dokument indeholder resultaterne af REA-analysen af Analog Devices' `TinyRadTool` samt den komplette plan og byggevejledning til at distribuere færdige standalone-applikationer til **macOS** (`.app` / `.dmg`) og **Linux** (standalone bundle, `.tar.gz` og `.deb`).

Alt, hvad der skal bruges for at bygge og køre programmerne (opdateret kildekode, genskabte firmware-funktioner, `.rtc`-konfigurationsfiler, `.img`-firmwarefiler, `udev`-regler, PyInstaller-spec, byggescripts, GitHub Actions workflow og automatiserede tests), ligger klar i denne mappe.

---

## 1. Hvad REA-analysen afslørede

Ved hjælp af REA (`reverse-engineer-anything`) blev både kildekoden i git-repoet og den officielle Windows-release `TinyRadToolAndDriver.zip` (`ev_022d950ce319f10c2885a16cd2494d540206b43d6683853ac6b196a83f7a28bc`) analyseret:

1. **USB-protokol og `usb.dll` (`ev_d58ff69169cc22e415cf59617ba9a5a6d61657f8a5856b98e95950ffb4470a6b`):**
   - Den oprindelige 32-bit Windows-driver `usb.dll` kommunikerer via WinUSB med **Analog Devices Blackfin BF707 Bulk Device** (`idVendor = 0x064B`, `idProduct = 0x7823`, interface-GUID `{E63702F7-ADB0-4991-A6E3-A1AC0D274644}`).
   - Decompilerede funktioner i `usb.dll`:
     - `exp_UsbWriteCmd` (`0x100020e0`, `ev_742fd52c007a8b7795e283fd3977ebe8c3210c1eb262a17d3877fb31557e5dd2`): Allokerer en 2048-byte kommandoblok (`0x800` bytes), lægger antallet af payload-bytes som `uint16` i byte `0..1` og kopierer 32-bit kommando-ord i little-endian fra byte `2` og frem, hvorefter hele blokken skrives til Bulk OUT-pipen.
     - `exp_UsbRead` (`0x100022b0`, `ev_eef1a5b9e48a5f15627ad45130ee649ae8d6e385e9dea2279238fd86199145cd`): Læser rå bytes fra Bulk IN-pipen.
   - I git-repoets `src/cmd_modules/Connection.py` er `usb.dll` allerede erstattet med `pyusb` (`libusb-1.0`), som opbygger præcis samme 2048-byte `Data2048`-pakke og sender den til første `ENDPOINT_OUT`.

2. **Kritiske fejl og mangler i git-repoet (genskabt fra `TinyRadTool-x32.exe`):**
   - `TinyRadTool-x32.exe` viste sig at være et UPX-pakket 7-Zip SFX-arkiv (7z-header ved offset `109837`), der indeholdt en Python 3.4 `cx_Freeze`-mappe (`dist32/`).
   - Decompilering af `dist32/src/cmd_modules/UsbADI.pyc` afslørede, at firmware-opdateringskommandoerne (`0x6009`: `Dsp_FmwrUpdtRmFlsh`, `Dsp_FmwrUpdtRdPt`, `Dsp_FmwrUpdtWrPt`) og flash-konstanterne (`FrmwrFlshNrBlcks = 64`, `FrmwrFlshNrSctrs = 16`, `FrmwrFlshSzSctrByts = 4096`, `FrmwrRdSz = 128`) var gået tabt i git-repoets `UsbADI.py`.
   - I `Connection.py` var `CmdRecv()` ufuldstændig for USB-svar større end 128 bytes (`if RecvLen > 0: print("TODO read moe .. "); pass`), hvilket fejler ved firmware-readback (`Dsp_FmwrUpdtRdPt` læser 516 bytes ad gangen).
   - Konfigurationsfilen `TinyRad-24.rtc` og de 4 firmware-images (`TinyRad-FW_R-2-6-1.img` til `R-3-0-3.img`) manglede helt i git-repoet og lå kun i `TinyRadToolAndDriver.zip`. Desuden havde `TinyRad-24.rtc` en tastefejl på linje 58 (`10ß000` i stedet for `10000`).
   - Appen crashede ved opstart med `IOError('Device not found.')`, hvis radar-boardet ikke var sat i USB, fordi `StackGui.__init__()` initialiserer USB-forbindelsen før GUI-vinduet vises.
   - Dokumentationen `TinyRad_Python.pdf` angav et forkert VID/PID (`04b4:00f1`) i `udev`-reglen til Linux; det rigtige board bruger `064b:7823`.

---

## 2. Oversigt over arkitektur- og kodeændringer i denne mappe

1. **Tværplatforms sti-, ressource- og `libusb`-håndtering (`src/cmd_modules/PlatformPaths.py`):**
   - Finder automatisk ressources (`src/ressource/img/`), konfigurationsfiler (`config/*.rtc`) og firmwarefiler (`firmware/*.img`) både ved kørsel fra kildekode og inde fra frosne PyInstaller-bundles (`sys._MEIPASS`).
   - Finder automatisk `libusb-1.0` på macOS (Apple Silicon `/opt/homebrew/lib`, Intel `/usr/local/lib`, MacPorts `/opt/local/lib` samt indlejret i `TinyRadTool.app/Contents/Frameworks`) og Linux.

2. **Robust USB-håndtering & Offline-mode (`Connection.py`, `UsbADI.py`, `TinyRad.py`):**
   - Appen starter nu uden fejl, selvom EV-TINYRAD24G ikke er tilsluttet USB. Når brugeren trykker `Initialize`, `Get Status` eller `Start Upgrade`, forsøger `Connection` automatisk at åbne USB-forbindelsen igen (`UsbOpen()`).
   - Fuldt implementeret multi-packet `CmdRecv()` (> 128 bytes) og genskabte `Dsp_FmwrUpdt*`-metoder i `UsbADI.py`.

3. **Modernisering til Python 3.10–3.13+, NumPy 2.x og PyQt5 (`src/`):**
   - Alle binære `numpy.fromstring(...)` er erstattet med `np.frombuffer(...)`, `.tostring()` med `.tobytes()`, `np.float` med `float` og `complex_` med `np.complex128`.
   - Alle tilbageværende PyQt4-kald (`QtGui.QApplication`, `QtGui.QWidget`, `QtGui.QFileDialog`, `QtCore.SIGNAL`, samt `tkinter.filedialog` i `ModCal.py`) er konverteret til ren PyQt5 (`QtWidgets.*`).
   - `h5py` er aktiveret til HDF5 data-eksport/import (`Store("fil.h5")`).

4. **Bundling og Distribution (`TinyRadTool.spec`, `packaging/`, `.github/workflows/`):**
   - `TinyRadTool.spec`: PyInstaller-specifikation til både macOS (`.app`) og Linux.
   - `packaging/macos/build_macos.sh`: Bygger `dist/TinyRadTool.app` (inkl. indlejret `libusb-1.0.dylib`, `config/` og `firmware/`), ad-hoc codesigner bundlen og pakker `dist/TinyRadTool-macOS.dmg`.
   - `packaging/linux/build_linux.sh`: Bygger `dist/TinyRadTool/`, pakker `dist/TinyRadTool-linux-<arch>.tar.gz` og genererer `dist/tinyradtool_1.1.2_<arch>.deb` inkl. `/lib/udev/rules.d/99-tinyrad.rules` og `.desktop`-genvej.
   - `.github/workflows/build-releases.yml`: GitHub Actions CI-pipeline, der bygger både macOS `.dmg` og Linux `.tar.gz`/`.deb` automatisk.

---

## 3. Sådan bygger du appsene

### På Linux (Ubuntu / Debian / Fedora m.fl.)
```bash
# 1. Installer systemafhængighed (libusb) og udev-regel
sudo apt-get install -y libusb-1.0-0
sudo cp packaging/linux/99-tinyrad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 2. Byg standalone Linux-app (.tar.gz og .deb)
bash packaging/linux/build_linux.sh
```
Output lægges i `dist/`:
- `dist/TinyRadTool/TinyRadTool` (kørbar standalone applikationsmappe)
- `dist/TinyRadTool-linux-x86_64.tar.gz` (distributerbart arkiv)
- `dist/tinyradtool_1.1.2_amd64.deb` (Debian/Ubuntu installationspakke)

### På macOS (Apple Silicon & Intel)
```bash
# 1. Installer libusb via Homebrew (bliver automatisk bundlet ind i .app)
brew install libusb

# 2. Byg TinyRadTool.app og TinyRadTool-macOS.dmg
bash packaging/macos/build_macos.sh
```
Output lægges i `dist/`:
- `dist/TinyRadTool.app` (selvstændig macOS-applikation med indlejret `libusb-1.0.dylib`, configs og firmware)
- `dist/TinyRadTool-macOS.dmg` (færdig macOS disk-image til distribution)

### Automatisk byg til både macOS og Linux via GitHub Actions
Push repoet til GitHub — workflowet i `.github/workflows/build-releases.yml` bygger automatisk både `TinyRadTool-macOS.dmg` på `macos-latest` og Linux-pakkerne på `ubuntu-latest`.
