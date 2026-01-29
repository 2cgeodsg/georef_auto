# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'georef_cache_dialog_baseVhyLHf.ui'
##
## Created by: Qt User Interface Compiler version 5.15.13
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PyQt5.QtCore import *  # type: ignore
from PyQt5.QtGui import *  # type: ignore
from PyQt5.QtWidgets import *  # type: ignore

from qgscollapsiblegroupbox import QgsCollapsibleGroupBox
from qgsextentgroupbox import QgsExtentGroupBox
from qgsfilewidget import QgsFileWidget


class Ui_GeorefCacheDialog(object):
    def setupUi(self, GeorefCacheDialog):
        if not GeorefCacheDialog.objectName():
            GeorefCacheDialog.setObjectName(u"GeorefCacheDialog")
        GeorefCacheDialog.resize(496, 454)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(GeorefCacheDialog.sizePolicy().hasHeightForWidth())
        GeorefCacheDialog.setSizePolicy(sizePolicy)
        GeorefCacheDialog.setMinimumSize(QSize(496, 454))
        GeorefCacheDialog.setMaximumSize(QSize(496, 454))
        self.tabWidget = QTabWidget(GeorefCacheDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(10, 10, 481, 441))
        self.tabWidget.setTabPosition(QTabWidget.North)
        self.tabWidget.setTabShape(QTabWidget.Rounded)
        self.paramsTab = QWidget()
        self.paramsTab.setObjectName(u"paramsTab")
        self.layoutWidget = QWidget(self.paramsTab)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(0, 0, 471, 401))
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.widgetExtent = QgsExtentGroupBox(self.layoutWidget)
        self.widgetExtent.setObjectName(u"widgetExtent")
        self.widgetExtent.setFlat(False)
        self.widgetExtent.setCheckable(False)
        self.widgetExtent.setChecked(False)
        self.widgetExtent.setCollapsed(False)
        self.widgetExtent.setSaveCollapsedState(True)

        self.verticalLayout.addWidget(self.widgetExtent)

        self.groupBoxWMS = QGroupBox(self.layoutWidget)
        self.groupBoxWMS.setObjectName(u"groupBoxWMS")
        self.verticalLayout_30 = QVBoxLayout(self.groupBoxWMS)
        self.verticalLayout_30.setObjectName(u"verticalLayout_30")
        self.comboBoxWMS = QComboBox(self.groupBoxWMS)
        self.comboBoxWMS.addItem("")
        self.comboBoxWMS.setObjectName(u"comboBoxWMS")

        self.verticalLayout_30.addWidget(self.comboBoxWMS)


        self.verticalLayout.addWidget(self.groupBoxWMS)

        self.groupBoxScale = QGroupBox(self.layoutWidget)
        self.groupBoxScale.setObjectName(u"groupBoxScale")
        self.verticalLayout_31 = QVBoxLayout(self.groupBoxScale)
        self.verticalLayout_31.setObjectName(u"verticalLayout_31")
        self.scaleComboBox = QComboBox(self.groupBoxScale)
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.addItem("")
        self.scaleComboBox.setObjectName(u"scaleComboBox")

        self.verticalLayout_31.addWidget(self.scaleComboBox)


        self.verticalLayout.addWidget(self.groupBoxScale)

        self.groupBoxOutput = QGroupBox(self.layoutWidget)
        self.groupBoxOutput.setObjectName(u"groupBoxOutput")
        self.verticalLayout_32 = QVBoxLayout(self.groupBoxOutput)
        self.verticalLayout_32.setObjectName(u"verticalLayout_32")
        self.widgetOutputFile = QgsFileWidget(self.groupBoxOutput)
        self.widgetOutputFile.setObjectName(u"widgetOutputFile")
        self.widgetOutputFile.setStorageMode(QgsFileWidget.GetDirectory)

        self.verticalLayout_32.addWidget(self.widgetOutputFile)


        self.verticalLayout.addWidget(self.groupBoxOutput)

        self.line = QFrame(self.layoutWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.btnCreateCache = QPushButton(self.layoutWidget)
        self.btnCreateCache.setObjectName(u"btnCreateCache")

        self.verticalLayout.addWidget(self.btnCreateCache)

        self.tabWidget.addTab(self.paramsTab, "")
        self.logTab = QWidget()
        self.logTab.setObjectName(u"logTab")
        self.groupBoxFeedback = QGroupBox(self.logTab)
        self.groupBoxFeedback.setObjectName(u"groupBoxFeedback")
        self.groupBoxFeedback.setGeometry(QRect(0, 0, 471, 401))
        self.groupBoxFeedback.setAutoFillBackground(True)
        self.verticalLayout_2 = QVBoxLayout(self.groupBoxFeedback)
        self.verticalLayout_2.setSpacing(1)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.progressBar = QProgressBar(self.groupBoxFeedback)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setEnabled(True)
        self.progressBar.setTextVisible(False)

        self.verticalLayout_2.addWidget(self.progressBar)

        self.textBrowserLog = QTextBrowser(self.groupBoxFeedback)
        self.textBrowserLog.setObjectName(u"textBrowserLog")

        self.verticalLayout_2.addWidget(self.textBrowserLog)

        self.tabWidget.addTab(self.logTab, "")

        self.retranslateUi(GeorefCacheDialog)

        self.tabWidget.setCurrentIndex(0)
        self.scaleComboBox.setCurrentIndex(5)


        QMetaObject.connectSlotsByName(GeorefCacheDialog)
    # setupUi

    def retranslateUi(self, GeorefCacheDialog):
        GeorefCacheDialog.setWindowTitle(QCoreApplication.translate("GeorefCacheDialog", u"WMS Cache Manager", None))
        self.widgetExtent.setTitle(QCoreApplication.translate("GeorefCacheDialog", u"Extent", None))
        self.groupBoxWMS.setTitle(QCoreApplication.translate("GeorefCacheDialog", u"WMS", None))
        self.comboBoxWMS.setItemText(0, QCoreApplication.translate("GeorefCacheDialog", u"ERROR: WMS SOURCES", None))

        self.groupBoxScale.setTitle(QCoreApplication.translate("GeorefCacheDialog", u"Zoom Level", None))
        self.scaleComboBox.setItemText(0, QCoreApplication.translate("GeorefCacheDialog", u"8 (1:2.300.000 ~ 1:1.150.000) (611m/px)", None))
        self.scaleComboBox.setItemText(1, QCoreApplication.translate("GeorefCacheDialog", u"9 (1:1.150.000 ~ 1:580.000) (306m/px)", None))
        self.scaleComboBox.setItemText(2, QCoreApplication.translate("GeorefCacheDialog", u"10 (1:580.000 ~ 1:290.000) (153m/px)", None))
        self.scaleComboBox.setItemText(3, QCoreApplication.translate("GeorefCacheDialog", u"11 (1:290.000 ~ 1:145.000) (76,4m/px)", None))
        self.scaleComboBox.setItemText(4, QCoreApplication.translate("GeorefCacheDialog", u"12 (1:145.000 ~ 1:75.000) (38,2m/px)", None))
        self.scaleComboBox.setItemText(5, QCoreApplication.translate("GeorefCacheDialog", u"13 (1:75.000 ~ 1:40.000) (19,1m/px)", None))
        self.scaleComboBox.setItemText(6, QCoreApplication.translate("GeorefCacheDialog", u"14 (1:40.000 ~ 1:20.000) (9,55m/px)", None))
        self.scaleComboBox.setItemText(7, QCoreApplication.translate("GeorefCacheDialog", u"15 (1:20.000 ~ 1:10.000) (4,78m/px)", None))
        self.scaleComboBox.setItemText(8, QCoreApplication.translate("GeorefCacheDialog", u"16 (1:10.000 ~ 1:5.000) (2,39m/px)", None))
        self.scaleComboBox.setItemText(9, QCoreApplication.translate("GeorefCacheDialog", u"17 (1:5.000 ~ 1:2.500) (1,19m/px)", None))
        self.scaleComboBox.setItemText(10, QCoreApplication.translate("GeorefCacheDialog", u"18 (1:2.500 ~ 1:1.250) (59,7cm/px)", None))
        self.scaleComboBox.setItemText(11, QCoreApplication.translate("GeorefCacheDialog", u"19 (1:1.250 ~ 1:600) (29,9cm/px)", None))

        self.groupBoxOutput.setTitle(QCoreApplication.translate("GeorefCacheDialog", u"Output", None))
        self.btnCreateCache.setText(QCoreApplication.translate("GeorefCacheDialog", u"Create Cache", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.paramsTab), QCoreApplication.translate("GeorefCacheDialog", u"Paramaters", None))
        self.groupBoxFeedback.setTitle("")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.logTab), QCoreApplication.translate("GeorefCacheDialog", u"Log", None))
    # retranslateUi

