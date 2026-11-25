# -*- coding: utf-8 -*-

from PyQt5 import QtCore, QtWidgets


def _translate(context, text, disambig):
    return QtWidgets.QApplication.translate(context, text, disambig)


class Ui_ProgressBarDialog(object):
    def setupUi(self, ProgressBarDialog):
        ProgressBarDialog.setObjectName("ProgressBarDialog")
        ProgressBarDialog.resize(197, 48)
        self.horizontalLayout = QtWidgets.QHBoxLayout(ProgressBarDialog)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.progressBar = QtWidgets.QProgressBar(ProgressBarDialog)
        self.progressBar.setMaximum(0)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName("progressBar")
        self.horizontalLayout.addWidget(self.progressBar)

        self.retranslateUi(ProgressBarDialog)
        QtCore.QMetaObject.connectSlotsByName(ProgressBarDialog)

    def retranslateUi(self, ProgressBarDialog):
        ProgressBarDialog.setWindowTitle(_translate("ProgressBarDialog", "Dialog", None))
