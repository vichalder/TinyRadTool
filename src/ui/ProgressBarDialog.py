from PyQt5 import QtWidgets
import src.ui.ui_ProgressBarDialog as ui_progressbardialog
import src.cmd_modules.PlatformPaths as PlatformPaths


class ProgressBarDialog(QtWidgets.QDialog, ui_progressbardialog.Ui_ProgressBarDialog):

    def __init__(self):
        super(ProgressBarDialog, self).__init__()
        self.setupUi(self)
        self.center()

    def center(self):
        PlatformPaths.center_window(self)
