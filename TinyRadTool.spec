# -*- mode: python ; coding: utf-8 -*-
import ctypes.util
import pathlib
import sys

project_root = pathlib.Path(SPECPATH).resolve()

datas = [
    (str(project_root / "src" / "ressource" / "img"), "src/ressource/img"),
    (str(project_root / "config"), "config"),
    (str(project_root / "firmware"), "firmware"),
]

binaries = []
libusb_candidates = [
    pathlib.Path("/opt/homebrew/lib/libusb-1.0.dylib"),
    pathlib.Path("/opt/homebrew/opt/libusb/lib/libusb-1.0.dylib"),
    pathlib.Path("/usr/local/lib/libusb-1.0.dylib"),
    pathlib.Path("/usr/local/opt/libusb/lib/libusb-1.0.dylib"),
    pathlib.Path("/opt/local/lib/libusb-1.0.dylib"),
    pathlib.Path("/lib/x86_64-linux-gnu/libusb-1.0.so.0"),
    pathlib.Path("/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0"),
    pathlib.Path("/lib/aarch64-linux-gnu/libusb-1.0.so.0"),
    pathlib.Path("/usr/lib/aarch64-linux-gnu/libusb-1.0.so.0"),
]
for cand in libusb_candidates:
    if cand.is_file():
        binaries.append((str(cand.resolve()), "."))
        break

hiddenimports = [
    "usb",
    "usb.core",
    "usb.util",
    "usb.backend.libusb1",
    "numpy.core",
    "numpy.core.multiarray",
    "numpy.core.numeric",
    "numpy._core.multiarray",
    "h5py",
    "pyqtgraph",
    "PyQt5.QtSvg",
    "PyQt5.QtPrintSupport",
    "src.cmd_modules.FrmwImg",
    "src.cmd_modules.PlatformPaths",
]

a = Analysis(
    [str(project_root / "TinyRadTool.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TinyRadTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TinyRadTool",
)

if sys.platform == "darwin":
    icns_path = project_root / "build" / "TinyRadTool.icns"
    app = BUNDLE(
        coll,
        name="TinyRadTool.app",
        icon=str(icns_path) if icns_path.is_file() else None,
        bundle_identifier="com.analog.tinyradtool",
        info_plist={
            "CFBundleName": "TinyRadTool",
            "CFBundleDisplayName": "TinyRadTool",
            "CFBundleShortVersionString": "1.1.2",
            "CFBundleVersion": "1.1.2",
            "CFBundleIconFile": "TinyRadTool.icns",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        },
    )
