import ctypes.util
import os
import pathlib
import platform
import shutil
import sys


def get_bundle_dir() -> pathlib.Path:
    """Return the root directory of the application (PyInstaller _MEIPASS or repo root)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return pathlib.Path(sys._MEIPASS).resolve()
    return pathlib.Path(__file__).resolve().parents[2]


def get_executable_dir() -> pathlib.Path:
    """Return the directory containing the running executable or script."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(sys.executable).resolve().parent
    return get_bundle_dir()


def get_resource_path(*parts: str) -> str:
    """Resolve a bundled resource path across source and PyInstaller runs."""
    candidate = get_bundle_dir().joinpath(*parts)
    if candidate.exists():
        return str(candidate)
    cwd_candidate = pathlib.Path.cwd().joinpath(*parts)
    if cwd_candidate.exists():
        return str(cwd_candidate)
    return str(candidate)


def get_user_data_dir() -> pathlib.Path:
    """Return the per-user writable configuration/data directory."""
    sys_name = platform.system()
    if sys_name == "Darwin":
        base = pathlib.Path.home() / "Library" / "Application Support" / "TinyRadTool"
    elif sys_name == "Windows":
        win_legacy = pathlib.Path("C:/Tools/TinyRadTool")
        if win_legacy.exists():
            return win_legacy
        appdata = os.environ.get("APPDATA")
        base = (pathlib.Path(appdata) if appdata else pathlib.Path.home()) / "TinyRadTool"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = (pathlib.Path(xdg) if xdg else (pathlib.Path.home() / ".config")) / "TinyRadTool"
    return base


def ensure_user_config_seeded() -> pathlib.Path:
    """Ensure the user config directory exists and contains Default.rtc / TinyRad-24.rtc."""
    user_dir = get_user_data_dir()
    bundled_cfg_dir = get_bundle_dir() / "config"
    try:
        user_dir.mkdir(parents=True, exist_ok=True)
        if bundled_cfg_dir.is_dir():
            for rtc in bundled_cfg_dir.glob("*.rtc"):
                dest = user_dir / rtc.name
                if not dest.exists():
                    shutil.copy2(rtc, dest)
        return user_dir
    except OSError:
        return bundled_cfg_dir if bundled_cfg_dir.is_dir() else get_bundle_dir()


def get_default_config_dir() -> str:
    """Return the default configuration folder path with a trailing slash."""
    cfg_dir = ensure_user_config_seeded()
    path_str = str(cfg_dir)
    if not path_str.endswith(os.sep) and not path_str.endswith("/"):
        path_str += "/"
    return path_str


def get_default_config_file() -> str:
    """Return the path to the default .rtc configuration file."""
    cfg_dir = ensure_user_config_seeded()
    for name in ("Default.rtc", "TinyRad-24.rtc"):
        candidate = cfg_dir / name
        if candidate.is_file():
            return str(candidate)
    bundled_cfg_dir = get_bundle_dir() / "config"
    for name in ("Default.rtc", "TinyRad-24.rtc"):
        candidate = bundled_cfg_dir / name
        if candidate.is_file():
            return str(candidate)
    return str(cfg_dir / "Default.rtc")


def get_config_dirs() -> list[pathlib.Path]:
    """Return ordered list of directories to search for .rtc configuration files."""
    dirs: list[pathlib.Path] = []

    def _add(p: pathlib.Path) -> None:
        try:
            resolved = p.resolve()
        except OSError:
            resolved = p
        if resolved.is_dir() and resolved not in dirs:
            dirs.append(resolved)

    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        arg_path = pathlib.Path(sys.argv[2])
        _add(arg_path if arg_path.is_dir() else arg_path.parent)

    _add(get_bundle_dir() / "config")
    _add(ensure_user_config_seeded())
    _add(get_executable_dir())
    _add(get_executable_dir() / "config")
    win_legacy = pathlib.Path("C:/Tools/TinyRadTool")
    if win_legacy.is_dir():
        _add(win_legacy)
    return dirs


def get_firmware_dirs() -> list[pathlib.Path]:
    """Return ordered list of directories to search for .img firmware files."""
    dirs: list[pathlib.Path] = []

    def _add(p: pathlib.Path) -> None:
        try:
            resolved = p.resolve()
        except OSError:
            resolved = p
        if resolved.is_dir() and resolved not in dirs:
            dirs.append(resolved)

    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        arg_path = pathlib.Path(sys.argv[2])
        _add(arg_path if arg_path.is_dir() else arg_path.parent)

    _add(get_bundle_dir() / "firmware")
    _add(get_bundle_dir())
    _add(get_executable_dir() / "firmware")
    _add(get_executable_dir())
    _add(ensure_user_config_seeded())
    return dirs


def find_libusb_library() -> str | None:
    """Locate the native libusb-1.0 shared library on macOS, Linux, or Windows."""
    bundle_dir = get_bundle_dir()
    exe_dir = get_executable_dir()

    candidates = [
        bundle_dir / "libusb-1.0.dylib",
        bundle_dir / "libusb-1.0.0.dylib",
        bundle_dir / "libusb-1.0.so.0",
        bundle_dir / "libusb-1.0.so",
        bundle_dir / "libusb-1.0.dll",
        exe_dir / "libusb-1.0.dylib",
        exe_dir / "libusb-1.0.0.dylib",
        exe_dir / "../Frameworks/libusb-1.0.dylib",
        exe_dir / "../Frameworks/libusb-1.0.0.dylib",
        pathlib.Path("/opt/homebrew/lib/libusb-1.0.dylib"),
        pathlib.Path("/opt/homebrew/opt/libusb/lib/libusb-1.0.dylib"),
        pathlib.Path("/usr/local/lib/libusb-1.0.dylib"),
        pathlib.Path("/usr/local/opt/libusb/lib/libusb-1.0.dylib"),
        pathlib.Path("/opt/local/lib/libusb-1.0.dylib"),
        pathlib.Path("/lib/x86_64-linux-gnu/libusb-1.0.so.0"),
        pathlib.Path("/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0"),
        pathlib.Path("/lib/aarch64-linux-gnu/libusb-1.0.so.0"),
        pathlib.Path("/usr/lib/aarch64-linux-gnu/libusb-1.0.so.0"),
        pathlib.Path("/usr/lib64/libusb-1.0.so.0"),
        pathlib.Path("/usr/lib/libusb-1.0.so.0"),
    ]
    for cand in candidates:
        try:
            if cand.is_file():
                return str(cand.resolve())
        except OSError:
            continue

    for name in ("usb-1.0", "libusb-1.0"):
        found = ctypes.util.find_library(name)
        if found:
            return found
    return None


def find_usb_backend():
    """Return a configured PyUSB libusb1 backend (or None if unavailable)."""
    try:
        import usb.backend.libusb1 as libusb1
    except ImportError:
        return None

    lib_path = find_libusb_library()
    if lib_path:
        backend = libusb1.get_backend(find_library=lambda _name: lib_path)
        if backend is not None:
            return backend
    return libusb1.get_backend()


def center_window(widget) -> None:
    """Center a QWidget/QMainWindow/QDialog on the active screen."""
    try:
        from PyQt5 import QtGui, QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        screen = None
        if hasattr(app, "screenAt"):
            screen = app.screenAt(QtGui.QCursor.pos())
        if screen is None and hasattr(app, "primaryScreen"):
            screen = app.primaryScreen()
        if screen is not None:
            center_point = screen.availableGeometry().center()
            widget.move(
                int(center_point.x() - widget.width() * 0.5),
                int(center_point.y() - widget.height() * 0.5),
            )
    except Exception:
        pass
