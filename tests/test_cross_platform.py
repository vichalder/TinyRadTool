import hashlib
import os
import pathlib
import pickle
import sys
import numpy as np
import pytest

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


def test_offline_tinyrad_and_multipacket_cmdrecv():
    from src.cmd_modules import TinyRad

    rad = TinyRad.TinyRad()
    assert rad.hCon == -1
    uid_ok, uid_data = rad.BrdGetUID()
    assert uid_ok is False
    assert len(uid_data) == 0

    vers = rad.BrdGetSwVers()
    assert vers["SwMaj"] == -1
    assert vers["SUid"] == -1

    assert rad.FrmwrFlshNrBlcks == 64
    assert rad.FrmwrFlshNrSctrs == 16
    assert rad.FrmwrFlshSzSctrByts == 4096
    assert rad.FrmwrRdSz == 128
    assert hasattr(rad, "Dsp_FmwrUpdtRmFlsh")
    assert hasattr(rad, "Dsp_FmwrUpdtRdPt")
    assert hasattr(rad, "Dsp_FmwrUpdtWrPt")

    expected_words = np.arange(128, dtype=np.uint32)
    header_word = np.array([(129 << 16) | 0x6009], dtype=np.uint32)
    wire_bytes = header_word.tobytes() + expected_words.tobytes()

    chunks = [
        np.frombuffer(wire_bytes[:128], dtype=np.uint8),
        np.frombuffer(wire_bytes[128:], dtype=np.uint8),
    ]

    class DummyEp:
        def write(self, data):
            return len(data)

        def read(self, length):
            return chunks.pop(0)

    rad.hCon = 1
    rad.usbDev = object()
    rad.usbWrEp = DummyEp()
    rad.usbRdEp = DummyEp()

    ok, payload = rad.Dsp_FmwrUpdtRdPt(0, 0, 0)
    assert ok is True
    assert len(payload) == 128
    np.testing.assert_array_equal(payload, expected_words)
    rad.hCon = -1
    rad.usbDev = None


def test_radarproc_numpy2():
    from src.cmd_modules import RadarProc

    proc = RadarProc.RadarProc()
    proc.CfgRangeProfile({"fs": 1e6, "kf": 1e12, "FFT": 256, "NIni": 1})
    data = np.ones((128, 4), dtype=np.float64)
    rp = proc.RangeProfile(data)
    assert rp.shape == (128, 4)

    proc.CfgRangeDoppler({"fs": 1e6, "kf": 1e12, "RangeFFT": 256, "VelFFT": 64, "N": 128, "Frms": 16, "fc": 24.125e9, "Tp": 256e-6})
    rd_in = np.ones((16 * 128,), dtype=np.float64)
    rd = proc.RangeDoppler(rd_in)
    assert rd.shape == (128, 64)

    proc.CfgBeamformingUla({"fs": 1e6, "kf": 1e12, "RangeFFT": 256, "AngFFT": 64, "NIni": 1})
    bf = proc.BeamformingUla(data)
    assert bf.shape == (128, 64)


def test_firmware_images_sha256_integrity():
    from src.cmd_modules.FrmwImg import FirmwareImage

    setattr(sys.modules["__main__"], "FirmwareImage", FirmwareImage)
    fw_dirs = PlatformPaths.get_firmware_dirs()
    img_files = []
    for d in fw_dirs:
        img_files.extend(sorted(d.glob("*.img")))
    assert len(img_files) >= 4
    for img_path in img_files:
        with open(img_path, "rb") as f:
            fw = pickle.load(f)
        h = hashlib.sha256()
        for block in fw.ImageData:
            for sector in block:
                h.update(sector)
        assert h.hexdigest() == fw.ImageSha256


def test_gui_and_dialogs_headless(monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5 import QtWidgets
    import src.ui.StackGui as StackGui
    import src.ui.StrtupBrd as StrtupBrd
    import src.ui.fwupgrd as fwupgrd
    import src.ui.about as about
    import src.proc_modes.ModTarDet as ModTarDet
    import src.proc_modes.ModCal as ModCal

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _auto_accept_startup(self):
        assert self.FilesAvailable is True
        assert len(self.lFile) >= 1
        self.ChkBox_Agree.setChecked(True)
        self.ActionButtonOkay()
        return QtWidgets.QDialog.Accepted

    monkeypatch.setattr(StrtupBrd.StrtupBrd, "exec_", _auto_accept_startup)

    win = StackGui.StackGui()
    assert win.GuiAgree is True
    assert win.GuiSelIni is True
    assert len(win.lView) == 6

    # Exercise all active mode views and offline Initialize buttons
    win.setFmcwWindow()
    win.PageFmcw.Button_Ini_StartThread()
    assert win.PageFmcw.InitFailed is True

    win.setRangeDopplerWindow()
    win.PageRangeDoppler.Button_Ini_StartThread()
    assert win.PageRangeDoppler.InitFailed is True

    win.setDBFWindow()
    win.PageBpa.Button_Ini_StartThread()
    assert win.PageBpa.InitFailed is True

    win.SetPerfWindow()
    win.PagePerf.Button_Meas_Est_Clicked()

    win.setStatusWindow()
    win.PageStatus.Action_BoardSts_Get()

    # Also instantiate optional Target Detection and Calibration views
    tar_det = ModTarDet.ModTarDet(win)
    assert tar_det.TabContWidget.count() >= 2
    cal_view = ModCal.ModCal(win)
    assert cal_view.TabContWidget.count() >= 1

    # Exercise Firmware Upgrade and About dialogs
    fw_dlg = fwupgrd.FwUpgrdDialog(win)
    assert fw_dlg.FilesAvailable is True
    assert len(fw_dlg.lFile) >= 4
    fw_dlg.comboBox_select_image.setCurrentIndex(len(fw_dlg.lFile) - 1)
    assert "3.0.3" in fw_dlg.textBrowser_ReleaseNotes.toPlainText()

    abt_dlg = about.AboutDialog()
    assert "TinyRadTool" in abt_dlg.label_version.text()

    win.cleanUp()


def test_connected_board_simulation_and_h5_export(monkeypatch, tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5 import QtWidgets
    import src.ui.StackGui as StackGui
    import src.ui.StrtupBrd as StrtupBrd
    import src.cmd_modules.FileStore as FileStore

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    monkeypatch.setattr(
        StrtupBrd.StrtupBrd,
        "exec_",
        lambda self: (self.ChkBox_Agree.setChecked(True), self.ActionButtonOkay(), QtWidgets.QDialog.Accepted)[-1],
    )

    win = StackGui.StackGui()
    win.stFolderCfg = str(tmp_path) + "/"
    brd = win.hTinyRad

    # Simulate an attached and responsive EV-TINYRAD24G board
    monkeypatch.setattr(brd, "BrdGetUID", lambda: (True, np.array([0x12345678, 0x9ABCDEF0], dtype=np.uint32)))
    monkeypatch.setattr(
        brd,
        "Dsp_GetSwVers",
        lambda: {"SwPatch": 3, "SwMin": 0, "SwMaj": 3, "SUid": 14, "HUid": 1},
    )
    monkeypatch.setattr(brd, "CmdSend", lambda *a, **kw: 0)
    monkeypatch.setattr(brd, "CmdRecv", lambda *a, **kw: np.array([1], dtype=np.uint32))
    monkeypatch.setattr(
        brd,
        "ConGetUsbData",
        lambda byte_len: np.random.randint(-500, 500, size=int(byte_len // 2), dtype=np.int16),
    )

    # 1. FMCW Initialize + 1 frame measurement + HDF5 Store("fmcw_out.h5")
    win.setFmcwWindow()
    win.PageFmcw.Button_Ini_StartThread()
    assert win.PageFmcw.InitFailed is False
    win.PageFmcw.Edit_Meas_NrFrms.setText("2")
    win.PageFmcw.NrFrmsInit = "2"
    win.PageFmcw.MeasNrFrmsIni = 2
    win.PageFmcw.Timer = QtCore_DummyTimer()
    win.PageFmcw.MeasUpdate()
    win.PageFmcw.Edit_Meas_Cmd.setText('Store("fmcw_out.h5")')
    win.PageFmcw.CmdExec()
    assert (tmp_path / "fmcw_out.h5").is_file()

    # 2. Range-Doppler Initialize + 1 frame measurement + HDF5 Store("rd_out.h5")
    win.setRangeDopplerWindow()
    win.PageRangeDoppler.Button_Ini_StartThread()
    assert win.PageRangeDoppler.InitFailed is False
    win.PageRangeDoppler.Edit_Meas_NrFrms.setText("2")
    win.PageRangeDoppler.NrFrmsInit = "2"
    win.PageRangeDoppler.MeasNrFrmsIni = 2
    win.PageRangeDoppler.Timer = QtCore_DummyTimer()
    win.PageRangeDoppler.MeasUpdate()
    win.PageRangeDoppler.Edit_Meas_Cmd.setText('Store("rd_out.h5")')
    win.PageRangeDoppler.CmdExec()
    assert (tmp_path / "rd_out.h5").is_file()

    # 3. DBF/BPA Initialize + 1 frame measurement + HDF5 Store("dbf_out.h5")
    win.setDBFWindow()
    win.PageBpa.Button_Ini_StartThread()
    assert win.PageBpa.InitFailed is False
    win.PageBpa.Edit_Meas_NrFrms.setText("2")
    win.PageBpa.NrFrmsInit = "2"
    win.PageBpa.MeasNrFrmsIni = 2
    win.PageBpa.Timer = QtCore_DummyTimer()
    win.PageBpa.MeasUpdate()
    win.PageBpa.Edit_Meas_Cmd.setText('Store("dbf_out.h5")')
    win.PageBpa.CmdExec()
    assert (tmp_path / "dbf_out.h5").is_file()

    # 4. FileStore round-trip test
    cal_file = str(tmp_path / "cal_test.h5")
    fs = FileStore.FileStore(cal_file)
    fs.Store("dCal", {"Type": 1, "Date": 20261125, "R": 2.5, "RCS": 1.0, "Dat": np.ones(8, dtype=np.complex128)})
    loaded = fs.ReadDict("dCal")
    assert loaded["Type"] == 1.0
    assert len(loaded["Dat"]) == 8

    win.cleanUp()


class QtCore_DummyTimer:
    def start(self):
        pass

    def stop(self):
        pass


def test_frozen_linux_binary_self_test(tmp_path):
    import subprocess

    binary = PlatformPaths.get_bundle_dir() / "dist" / "TinyRadTool" / "TinyRadTool"
    if not binary.is_file():
        pytest.skip("Standalone binary not built yet")
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    res = subprocess.run(
        [str(binary), "--self-test"],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 0, f"stdout: {res.stdout}\nstderr: {res.stderr}"
    assert "SELF_TEST_OK" in res.stdout
