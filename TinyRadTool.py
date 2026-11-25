#!/usr/bin/env python3
import sys
from PyQt5 import QtGui, QtWidgets

import src.cmd_modules.FrmwImg as FrmwImg
from src.cmd_modules.FrmwImg import FirmwareImage
import src.cmd_modules.PlatformPaths as PlatformPaths
import src.ui.StackGui as StackGui
import src.ui.StrtupBrd as StrtupBrd
import src.ui.fwupgrd as fwupgrd
import src.ui.about as about


def main():
    setattr(sys.modules["__main__"], "FirmwareImage", FirmwareImage)
    self_test = "--self-test" in sys.argv
    qt_args = [arg for arg in sys.argv if arg != "--self-test"]

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(qt_args)
    app.setApplicationName("TinyRadTool")
    app.setOrganizationName("Analog Devices")
    icon_path = PlatformPaths.get_resource_path("src", "ressource", "img", "adi.png")
    if icon_path:
        app.setWindowIcon(QtGui.QIcon(icon_path))

    if self_test:
        orig_exec = StrtupBrd.StrtupBrd.exec_

        def _auto_exec(self):
            if not self.FilesAvailable or len(self.lFile) < 1:
                raise RuntimeError("No .rtc configuration files found in bundle")
            self.ChkBox_Agree.setChecked(True)
            self.ActionButtonOkay()
            return QtWidgets.QDialog.Accepted

        setattr(StrtupBrd.StrtupBrd, "exec_", _auto_exec)
        try:
            win = StackGui.StackGui()
            win.show()
            fw_dlg = fwupgrd.FwUpgrdDialog(win)
            if not fw_dlg.FilesAvailable or len(fw_dlg.lFile) < 4:
                raise RuntimeError("Bundled firmware .img files missing")
            abt_dlg = about.AboutDialog()
            QtWidgets.QApplication.processEvents()
            abt_dlg.close()
            fw_dlg.close()
            win.cleanUp()
            win.close()
        finally:
            setattr(StrtupBrd.StrtupBrd, "exec_", orig_exec)
        print("SELF_TEST_OK")
        return 0

    Win = StackGui.StackGui()
    Win.show()
    app.aboutToQuit.connect(Win.cleanUp)
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
