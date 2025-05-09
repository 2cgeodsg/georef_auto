# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'georef_report_dialog_base.ui'
#
# Created by: PyQt5 UI code generator 5.15.11
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_GeorefReportDialog(object):
    def setupUi(self, GeorefReportDialog):
        GeorefReportDialog.setObjectName("GeorefReportDialog")
        GeorefReportDialog.resize(600, 400)
        self.verticalLayout = QtWidgets.QVBoxLayout(GeorefReportDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.labelTitle = QtWidgets.QLabel(GeorefReportDialog)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.labelTitle.setFont(font)
        self.labelTitle.setAlignment(QtCore.Qt.AlignCenter)
        self.labelTitle.setObjectName("labelTitle")
        self.verticalLayout.addWidget(self.labelTitle)
        self.labelSuccess = QtWidgets.QLabel(GeorefReportDialog)
        self.labelSuccess.setObjectName("labelSuccess")
        self.verticalLayout.addWidget(self.labelSuccess)
        self.listSuccess = QtWidgets.QListWidget(GeorefReportDialog)
        self.listSuccess.setObjectName("listSuccess")
        self.verticalLayout.addWidget(self.listSuccess)
        self.labelFailed = QtWidgets.QLabel(GeorefReportDialog)
        self.labelFailed.setObjectName("labelFailed")
        self.verticalLayout.addWidget(self.labelFailed)
        self.listFailed = QtWidgets.QListWidget(GeorefReportDialog)
        self.listFailed.setObjectName("listFailed")
        self.verticalLayout.addWidget(self.listFailed)
        self.labelFailedInfo = QtWidgets.QLabel(GeorefReportDialog)
        self.labelFailedInfo.setWordWrap(True)
        self.labelFailedInfo.setObjectName("labelFailedInfo")
        self.verticalLayout.addWidget(self.labelFailedInfo)
        self.buttonBox = QtWidgets.QDialogButtonBox(GeorefReportDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(GeorefReportDialog)
        self.buttonBox.accepted.connect(GeorefReportDialog.accept) # type: ignore
        self.buttonBox.rejected.connect(GeorefReportDialog.reject) # type: ignore
        QtCore.QMetaObject.connectSlotsByName(GeorefReportDialog)

    def retranslateUi(self, GeorefReportDialog):
        _translate = QtCore.QCoreApplication.translate
        GeorefReportDialog.setWindowTitle(_translate("GeorefReportDialog", "Georeferencing Report"))
        self.labelTitle.setText(_translate("GeorefReportDialog", "Georeferencing Process Report"))
        self.labelSuccess.setText(_translate("GeorefReportDialog", "Successfully Georeferenced Images:"))
        self.labelFailed.setText(_translate("GeorefReportDialog", "Failed Images:"))
        self.labelFailedInfo.setText(_translate("GeorefReportDialog", "For failed images, please review the bounding polygon and reference layer."))
