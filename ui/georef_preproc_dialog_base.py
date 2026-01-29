# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'georef_preproc_dialog_baseLkwqxX.ui'
##
## Created by: Qt User Interface Compiler version 5.15.13
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PyQt5.QtCore import *  # type: ignore
from PyQt5.QtGui import *  # type: ignore
from PyQt5.QtWidgets import *  # type: ignore

from qgsfilewidget import QgsFileWidget


class Ui_GeorefPreprocDialog(object):
    def setupUi(self, GeorefPreprocDialog):
        if not GeorefPreprocDialog.objectName():
            GeorefPreprocDialog.setObjectName(u"GeorefPreprocDialog")
        GeorefPreprocDialog.resize(457, 216)
        self.verticalLayout = QVBoxLayout(GeorefPreprocDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBoxImages = QGroupBox(GeorefPreprocDialog)
        self.groupBoxImages.setObjectName(u"groupBoxImages")
        self.verticalLayout_3 = QVBoxLayout(self.groupBoxImages)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.fileImage = QgsFileWidget(self.groupBoxImages)
        self.fileImage.setObjectName(u"fileImage")

        self.verticalLayout_3.addWidget(self.fileImage)


        self.verticalLayout.addWidget(self.groupBoxImages)

        self.groupBoxReference = QGroupBox(GeorefPreprocDialog)
        self.groupBoxReference.setObjectName(u"groupBoxReference")
        self.verticalLayout_4 = QVBoxLayout(self.groupBoxReference)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.comboReferenceLayer = QComboBox(self.groupBoxReference)
        self.comboReferenceLayer.setObjectName(u"comboReferenceLayer")

        self.verticalLayout_4.addWidget(self.comboReferenceLayer)


        self.verticalLayout.addWidget(self.groupBoxReference)

        self.groupBoxOptions = QGroupBox(GeorefPreprocDialog)
        self.groupBoxOptions.setObjectName(u"groupBoxOptions")
        self.verticalLayout_5 = QVBoxLayout(self.groupBoxOptions)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.checkBoxAddToProject = QCheckBox(self.groupBoxOptions)
        self.checkBoxAddToProject.setObjectName(u"checkBoxAddToProject")
        self.checkBoxAddToProject.setChecked(True)

        self.verticalLayout_5.addWidget(self.checkBoxAddToProject)


        self.verticalLayout.addWidget(self.groupBoxOptions)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnLocate = QPushButton(GeorefPreprocDialog)
        self.btnLocate.setObjectName(u"btnLocate")

        self.horizontalLayout.addWidget(self.btnLocate)

        self.btnCancel = QPushButton(GeorefPreprocDialog)
        self.btnCancel.setObjectName(u"btnCancel")

        self.horizontalLayout.addWidget(self.btnCancel)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(GeorefPreprocDialog)

        QMetaObject.connectSlotsByName(GeorefPreprocDialog)
    # setupUi

    def retranslateUi(self, GeorefPreprocDialog):
        GeorefPreprocDialog.setWindowTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Preprocessing: Aproximate Image Location", None))
        self.groupBoxImages.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Image", None))
        self.groupBoxReference.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Reference Layer", None))
        self.groupBoxOptions.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Options", None))
        self.checkBoxAddToProject.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Add possible MIs to project", None))
        self.btnLocate.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Aproximate Location", None))
        self.btnCancel.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Cancel", None))
    # retranslateUi

