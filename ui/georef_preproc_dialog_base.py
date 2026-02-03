# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'georef_preproc_dialog_baseAlmGhi.ui'
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
        GeorefPreprocDialog.resize(465, 450)
        GeorefPreprocDialog.setMinimumSize(QSize(465, 450))
        GeorefPreprocDialog.setMaximumSize(QSize(465, 450))
        self.verticalLayout = QVBoxLayout(GeorefPreprocDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBoxImages = QGroupBox(GeorefPreprocDialog)
        self.groupBoxImages.setObjectName(u"groupBoxImages")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBoxImages.sizePolicy().hasHeightForWidth())
        self.groupBoxImages.setSizePolicy(sizePolicy)
        self.verticalLayout_3 = QVBoxLayout(self.groupBoxImages)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.fileImage = QgsFileWidget(self.groupBoxImages)
        self.fileImage.setObjectName(u"fileImage")
        sizePolicy.setHeightForWidth(self.fileImage.sizePolicy().hasHeightForWidth())
        self.fileImage.setSizePolicy(sizePolicy)

        self.verticalLayout_3.addWidget(self.fileImage)

        self.formImage = QFormLayout()
        self.formImage.setObjectName(u"formImage")
        self.spatialResolutionLabel = QLabel(self.groupBoxImages)
        self.spatialResolutionLabel.setObjectName(u"spatialResolutionLabel")

        self.formImage.setWidget(0, QFormLayout.LabelRole, self.spatialResolutionLabel)

        self.spatialResolutionDoubleSpinBox = QDoubleSpinBox(self.groupBoxImages)
        self.spatialResolutionDoubleSpinBox.setObjectName(u"spatialResolutionDoubleSpinBox")
        self.spatialResolutionDoubleSpinBox.setDecimals(2)
        self.spatialResolutionDoubleSpinBox.setMaximum(1000.000000000000000)
        self.spatialResolutionDoubleSpinBox.setSingleStep(1.000000000000000)
        self.spatialResolutionDoubleSpinBox.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.spatialResolutionDoubleSpinBox.setValue(2.400000000000000)

        self.formImage.setWidget(0, QFormLayout.FieldRole, self.spatialResolutionDoubleSpinBox)


        self.verticalLayout_3.addLayout(self.formImage)


        self.verticalLayout.addWidget(self.groupBoxImages)

        self.groupBoxReference = QGroupBox(GeorefPreprocDialog)
        self.groupBoxReference.setObjectName(u"groupBoxReference")
        sizePolicy.setHeightForWidth(self.groupBoxReference.sizePolicy().hasHeightForWidth())
        self.groupBoxReference.setSizePolicy(sizePolicy)
        self.verticalLayout_4 = QVBoxLayout(self.groupBoxReference)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.tabWidget = QTabWidget(self.groupBoxReference)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        sizePolicy1 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.tabWidget.sizePolicy().hasHeightForWidth())
        self.tabWidget.setSizePolicy(sizePolicy1)
        self.tabWidget.setMinimumSize(QSize(427, 28))
        self.tabWidget.setTabShape(QTabWidget.Rounded)
        self.tabWidget.setTabBarAutoHide(False)
        self.tab1 = QWidget()
        self.tab1.setObjectName(u"tab1")
        self.verticalLayout_9 = QVBoxLayout(self.tab1)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.verticalLayout_9.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.frameAnotherLayer = QFrame(self.tab1)
        self.frameAnotherLayer.setObjectName(u"frameAnotherLayer")
        self.frameAnotherLayer.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.frameAnotherLayer.setAutoFillBackground(True)
        self.verticalLayout_2 = QVBoxLayout(self.frameAnotherLayer)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)

        self.verticalLayout_9.addWidget(self.frameAnotherLayer)

        self.frameWMS = QFrame(self.tab1)
        self.frameWMS.setObjectName(u"frameWMS")
        self.frameWMS.setEnabled(True)
        sizePolicy1.setHeightForWidth(self.frameWMS.sizePolicy().hasHeightForWidth())
        self.frameWMS.setSizePolicy(sizePolicy1)
        self.verticalLayout_6 = QVBoxLayout(self.frameWMS)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.groupBoxWMS = QGroupBox(self.frameWMS)
        self.groupBoxWMS.setObjectName(u"groupBoxWMS")
        self.verticalLayout_7 = QVBoxLayout(self.groupBoxWMS)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.comboWMSLayer = QComboBox(self.groupBoxWMS)
        self.comboWMSLayer.addItem("")
        self.comboWMSLayer.setObjectName(u"comboWMSLayer")

        self.verticalLayout_7.addWidget(self.comboWMSLayer)


        self.verticalLayout_6.addWidget(self.groupBoxWMS)

        self.groupBoxOutput = QGroupBox(self.frameWMS)
        self.groupBoxOutput.setObjectName(u"groupBoxOutput")
        self.verticalLayout_32 = QVBoxLayout(self.groupBoxOutput)
        self.verticalLayout_32.setObjectName(u"verticalLayout_32")
        self.widgetCache = QgsFileWidget(self.groupBoxOutput)
        self.widgetCache.setObjectName(u"widgetCache")
        self.widgetCache.setStorageMode(QgsFileWidget.GetDirectory)

        self.verticalLayout_32.addWidget(self.widgetCache)


        self.verticalLayout_6.addWidget(self.groupBoxOutput)


        self.verticalLayout_9.addWidget(self.frameWMS)

        self.tabWidget.addTab(self.tab1, "")
        self.tab2 = QWidget()
        self.tab2.setObjectName(u"tab2")
        self.verticalLayout_10 = QVBoxLayout(self.tab2)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.groupBoxAnother = QGroupBox(self.tab2)
        self.groupBoxAnother.setObjectName(u"groupBoxAnother")
        sizePolicy.setHeightForWidth(self.groupBoxAnother.sizePolicy().hasHeightForWidth())
        self.groupBoxAnother.setSizePolicy(sizePolicy)
        self.verticalLayout_8 = QVBoxLayout(self.groupBoxAnother)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.comboReferenceLayer = QComboBox(self.groupBoxAnother)
        self.comboReferenceLayer.setObjectName(u"comboReferenceLayer")
        sizePolicy.setHeightForWidth(self.comboReferenceLayer.sizePolicy().hasHeightForWidth())
        self.comboReferenceLayer.setSizePolicy(sizePolicy)

        self.verticalLayout_8.addWidget(self.comboReferenceLayer)


        self.verticalLayout_10.addWidget(self.groupBoxAnother)

        self.tabWidget.addTab(self.tab2, "")

        self.verticalLayout_4.addWidget(self.tabWidget)


        self.verticalLayout.addWidget(self.groupBoxReference)

        self.groupBoxOptions = QGroupBox(GeorefPreprocDialog)
        self.groupBoxOptions.setObjectName(u"groupBoxOptions")
        sizePolicy.setHeightForWidth(self.groupBoxOptions.sizePolicy().hasHeightForWidth())
        self.groupBoxOptions.setSizePolicy(sizePolicy)
        self.verticalLayout_5 = QVBoxLayout(self.groupBoxOptions)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.checkBoxAddToProject = QCheckBox(self.groupBoxOptions)
        self.checkBoxAddToProject.setObjectName(u"checkBoxAddToProject")
        self.checkBoxAddToProject.setChecked(True)

        self.verticalLayout_5.addWidget(self.checkBoxAddToProject)


        self.verticalLayout.addWidget(self.groupBoxOptions)

        self.btnsFrame = QFrame(GeorefPreprocDialog)
        self.btnsFrame.setObjectName(u"btnsFrame")
        sizePolicy.setHeightForWidth(self.btnsFrame.sizePolicy().hasHeightForWidth())
        self.btnsFrame.setSizePolicy(sizePolicy)
        self.horizontalLayout = QHBoxLayout(self.btnsFrame)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.btnLocate = QPushButton(self.btnsFrame)
        self.btnLocate.setObjectName(u"btnLocate")

        self.horizontalLayout.addWidget(self.btnLocate)

        self.btnCancel = QPushButton(self.btnsFrame)
        self.btnCancel.setObjectName(u"btnCancel")

        self.horizontalLayout.addWidget(self.btnCancel)


        self.verticalLayout.addWidget(self.btnsFrame)


        self.retranslateUi(GeorefPreprocDialog)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(GeorefPreprocDialog)
    # setupUi

    def retranslateUi(self, GeorefPreprocDialog):
        GeorefPreprocDialog.setWindowTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Preprocessing: Aproximate Image Location", None))
        self.groupBoxImages.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Image", None))
        self.fileImage.setDialogTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Select Aerial Image Non-georeferrenced Mosaic", None))
        self.fileImage.setFilter(QCoreApplication.translate("GeorefPreprocDialog", u"Images (*.tif *.jpg *.png *.jpeg)", None))
        self.spatialResolutionLabel.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Spatial resolution", None))
        self.spatialResolutionDoubleSpinBox.setSuffix(QCoreApplication.translate("GeorefPreprocDialog", u" meters / pixel", None))
        self.groupBoxReference.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Reference", None))
        self.groupBoxWMS.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Source", None))
        self.comboWMSLayer.setItemText(0, QCoreApplication.translate("GeorefPreprocDialog", u"WMSSources go here", None))

        self.groupBoxOutput.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Cache folder", None))
        self.widgetCache.setDialogTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Select cache folder", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab1), QCoreApplication.translate("GeorefPreprocDialog", u"Cache and use WMS", None))
        self.groupBoxAnother.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Layer", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab2), QCoreApplication.translate("GeorefPreprocDialog", u"Use another layer", None))
        self.groupBoxOptions.setTitle(QCoreApplication.translate("GeorefPreprocDialog", u"Options", None))
        self.checkBoxAddToProject.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Add possible MIs to project", None))
        self.btnLocate.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Aproximate Location", None))
        self.btnCancel.setText(QCoreApplication.translate("GeorefPreprocDialog", u"Cancel", None))
    # retranslateUi

