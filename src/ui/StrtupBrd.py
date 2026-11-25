from PyQt5 import QtCore, QtGui, QtWidgets
import  pyqtgraph as pg
import  src.ui.ui_Strtup as ui_Strtup
import  re
import  os
from    os import listdir
import  src.cmd_modules.StrConv as StrConv
import  src.cmd_modules.PlatformPaths as PlatformPaths
import  sys


class StrtupBrd(QtWidgets.QDialog, ui_Strtup.Ui_Strtup):

    def __init__(self, patre):
        super(StrtupBrd, self).__init__()
        self.patre  = patre
        self.setupUi(self)
        #self.initLabels()
        self.assignWidgets()
        self.CenterWindow()
        self.lFile              =   list()
        self.FilesAvailable     =   False

        self.ListFiles()
        
    def ListFiles(self):
        AnaFiles = False
        seen_paths = set()
        RegExp = re.compile(r"(?P<Name>([a-zA-Z0-9\-_]+))[.]{1,1}(?P<Ext>(rtc))")

        for cfg_dir in PlatformPaths.get_config_dirs():
            try:
                lDir = sorted(listdir(str(cfg_dir)))
            except OSError:
                continue
            for Elem in lDir:
                Match = RegExp.search(Elem)
                if Match:
                    full_path = str(cfg_dir / Elem)
                    if full_path in seen_paths or Elem in seen_paths:
                        continue
                    seen_paths.add(full_path)
                    seen_paths.add(Elem)
                    self.FilesAvailable = True
                    stName = Match.group("Name")
                    stFileDesc = self.ParseForDescription(full_path)
                    self.ComboBox_Select.addItem("Tools: " + stName + " : " + str(stFileDesc))
                    self.lFile.append(full_path)

        self.label.setText(f"Available configuration files in {self.patre.stFolderCfg}")
        if len(self.lFile) > 0:
            AnaFiles = True

        if not AnaFiles:
            palette     = QtGui.QPalette()
            palette.setColor(QtGui.QPalette.Foreground, QtCore.Qt.darkRed)
            self.label.setPalette(palette)             
            self.label.setText(f"No configuration files found in {self.patre.stFolderCfg}!")
            self.ComboBox_Select.setDisabled(True)
            
    def ParseForDescription(self, stFile):
        if len(stFile) > 1:
            File        =   open(stFile, "r", encoding="utf-8", errors="ignore")
            
            lCmd        =   list()
            self.Title  =   "No Title"

            lCmd.append((r"Gui_SetTitle\((?P<Val>('[a-zA-Z0-9 \-]+'))\)", "self.Title", "Var"))
            lCmd.append((r"Gui_SetIPAddr\((?P<Val>('[0-9]{1,3}[.]{1,1}[0-9]{1,3}[.]{1,1}[0-9]{1,3}[.]{1,1}[0-9]{1,3}'))\)", "self.IpAddr", "Var"))
            for stLine in File:
                Ret     =   StrConv.ConvStrToCmd(stLine, lCmd)
                if Ret[0]:
                    exec(Ret[1])          

            return self.Title

    def assignWidgets(self):
        self.Button_Ok.clicked.connect(self.ActionButtonOkay)
        self.Button_Cancel.clicked.connect(self.ActionButtonCancel)

        #self.setStyleSheet("background-color: white;")
        path = PlatformPaths.get_resource_path("src", "ressource", "img", "adi.png")
        self.Image_Logo     = QtGui.QImage(path)
        self.Label_Logo     = QtWidgets.QLabel()
        self.Logo_Layout    = QtWidgets.QHBoxLayout()
        # self.Label_Logo.setMaximumSize(400,200)
        # self.Image_Logo.scaledToWidth(200)
        self.pixmap = QtGui.QPixmap(self.Image_Logo)
        self.pixmap.scaled(400,200)
        self.Label_Logo.setPixmap(self.pixmap)
        self.Logo_Layout.addWidget(self.Label_Logo)
        self.WidgetPic.setLayout(self.Logo_Layout)

    def CenterWindow(self):
        PlatformPaths.center_window(self)

    def ActionButtonOkay(self):
        if self.FilesAvailable:
            Idx                     =   self.ComboBox_Select.currentIndex()
            self.patre.GuiSelIni    =   True
            self.patre.stFileCfg    =   self.lFile[Idx] 
        else:
            self.patre.GuiSelIni    =   False
        self.patre.GuiAgree         =   self.ChkBox_Agree.isChecked() 
        self.accept()
    


    def ActionButtonCancel(self):
        self.patre.GuiSelIni        =   False
        self.patre.GuiAgree         =   False
        self.reject()


