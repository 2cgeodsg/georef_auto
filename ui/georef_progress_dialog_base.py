# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'georef_progress_dialog_baseRiuRmh.ui'
##
## Created by: Qt User Interface Compiler version 5.15.13
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PyQt5.QtCore import *  # type: ignore
from PyQt5.QtGui import *  # type: ignore
from PyQt5.QtWidgets import *  # type: ignore


class Ui_GeorefProgressDialog(object):
    def setupUi(self, GeorefProgressDialog):
        if not GeorefProgressDialog.objectName():
            GeorefProgressDialog.setObjectName(u"GeorefProgressDialog")
        GeorefProgressDialog.resize(241, 150)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(GeorefProgressDialog.sizePolicy().hasHeightForWidth())
        GeorefProgressDialog.setSizePolicy(sizePolicy)
        GeorefProgressDialog.setMinimumSize(QSize(241, 150))
        GeorefProgressDialog.setMaximumSize(QSize(241, 150))
        self.verticalLayout = QVBoxLayout(GeorefProgressDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.labelDescription = QLabel(GeorefProgressDialog)
        self.labelDescription.setObjectName(u"labelDescription")
        sizePolicy1 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.labelDescription.sizePolicy().hasHeightForWidth())
        self.labelDescription.setSizePolicy(sizePolicy1)
        self.labelDescription.setLayoutDirection(Qt.LeftToRight)
        self.labelDescription.setTextFormat(Qt.MarkdownText)
        self.labelDescription.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.labelDescription)

        self.widgetProgress = QWidget(GeorefProgressDialog)
        self.widgetProgress.setObjectName(u"widgetProgress")
        sizePolicy.setHeightForWidth(self.widgetProgress.sizePolicy().hasHeightForWidth())
        self.widgetProgress.setSizePolicy(sizePolicy)
        self.widgetProgress.setMinimumSize(QSize(223, 23))
        self.widgetProgress.setMaximumSize(QSize(16777215, 23))
        self.labelPrimary = QLabel(self.widgetProgress)
        self.labelPrimary.setObjectName(u"labelPrimary")
        self.labelPrimary.setGeometry(QRect(0, 0, 221, 21))
        self.labelPrimary.setAlignment(Qt.AlignCenter)
        self.progressBarPrimary = QProgressBar(self.widgetProgress)
        self.progressBarPrimary.setObjectName(u"progressBarPrimary")
        self.progressBarPrimary.setGeometry(QRect(0, 0, 221, 23))
        sizePolicy2 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.progressBarPrimary.sizePolicy().hasHeightForWidth())
        self.progressBarPrimary.setSizePolicy(sizePolicy2)
        self.progressBarPrimary.setValue(24)
        self.progressBarPrimary.setTextVisible(False)
        self.progressBarPrimary.raise_()
        self.labelPrimary.raise_()

        self.verticalLayout.addWidget(self.widgetProgress)

        self.widgetProgressSecondary = QWidget(GeorefProgressDialog)
        self.widgetProgressSecondary.setObjectName(u"widgetProgressSecondary")
        self.widgetProgressSecondary.setMinimumSize(QSize(223, 23))
        self.widgetProgressSecondary.setMaximumSize(QSize(16777215, 23))
        self.labelSecondary = QLabel(self.widgetProgressSecondary)
        self.labelSecondary.setObjectName(u"labelSecondary")
        self.labelSecondary.setGeometry(QRect(0, 0, 221, 21))
        sizePolicy1.setHeightForWidth(self.labelSecondary.sizePolicy().hasHeightForWidth())
        self.labelSecondary.setSizePolicy(sizePolicy1)
        self.labelSecondary.setSizeIncrement(QSize(1, 1))
        self.labelSecondary.setFrameShape(QFrame.NoFrame)
        self.labelSecondary.setMidLineWidth(0)
        self.labelSecondary.setAlignment(Qt.AlignCenter)
        self.progressBarSecondary = QProgressBar(self.widgetProgressSecondary)
        self.progressBarSecondary.setObjectName(u"progressBarSecondary")
        self.progressBarSecondary.setGeometry(QRect(0, 0, 221, 23))
        self.progressBarSecondary.setValue(40)
        self.progressBarSecondary.setTextVisible(False)
        self.progressBarSecondary.raise_()
        self.labelSecondary.raise_()

        self.verticalLayout.addWidget(self.widgetProgressSecondary)

        self.widgetProgressTertiary = QWidget(GeorefProgressDialog)
        self.widgetProgressTertiary.setObjectName(u"widgetProgressTertiary")
        self.widgetProgressTertiary.setMinimumSize(QSize(223, 23))
        self.widgetProgressTertiary.setMaximumSize(QSize(16777215, 23))
        self.labelTertiary = QLabel(self.widgetProgressTertiary)
        self.labelTertiary.setObjectName(u"labelTertiary")
        self.labelTertiary.setGeometry(QRect(0, 0, 221, 21))
        sizePolicy1.setHeightForWidth(self.labelTertiary.sizePolicy().hasHeightForWidth())
        self.labelTertiary.setSizePolicy(sizePolicy1)
        self.labelTertiary.setSizeIncrement(QSize(1, 1))
        self.labelTertiary.setFrameShape(QFrame.NoFrame)
        self.labelTertiary.setMidLineWidth(0)
        self.labelTertiary.setAlignment(Qt.AlignCenter)
        self.progressBarTertiary = QProgressBar(self.widgetProgressTertiary)
        self.progressBarTertiary.setObjectName(u"progressBarTertiary")
        self.progressBarTertiary.setGeometry(QRect(0, 0, 221, 23))
        self.progressBarTertiary.setValue(40)
        self.progressBarTertiary.setTextVisible(False)
        self.progressBarTertiary.raise_()
        self.labelTertiary.raise_()

        self.verticalLayout.addWidget(self.widgetProgressTertiary)

        self.btnCancel = QPushButton(GeorefProgressDialog)
        self.btnCancel.setObjectName(u"btnCancel")

        self.verticalLayout.addWidget(self.btnCancel)


        self.retranslateUi(GeorefProgressDialog)

        QMetaObject.connectSlotsByName(GeorefProgressDialog)
    # setupUi

    def retranslateUi(self, GeorefProgressDialog):
        GeorefProgressDialog.setWindowTitle(QCoreApplication.translate("GeorefProgressDialog", u"SET TITLE HERE", None))
        self.labelDescription.setText(QCoreApplication.translate("GeorefProgressDialog", u"### TextLabel Label", None))
        self.labelPrimary.setText(QCoreApplication.translate("GeorefProgressDialog", u"TextLabel", None))
        self.labelSecondary.setText(QCoreApplication.translate("GeorefProgressDialog", u"TextLabel", None))
        self.labelTertiary.setText(QCoreApplication.translate("GeorefProgressDialog", u"TextLabel", None))
        self.btnCancel.setText(QCoreApplication.translate("GeorefProgressDialog", u"Cancelar", None))
    # retranslateUi

