from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QCoreApplication

from .georef_progress_dialog_base import Ui_GeorefProgressDialog


class GeorefProgressDialog(QDialog, Ui_GeorefProgressDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.btnCancel.clicked.connect(self.cancel)
    
    def setTitle(self, title: str):
        self.setWindowTitle(QCoreApplication.translate("GeorefProgressDialog", u"{s}".format(s=title), None))
    
    def setDescription(self, description: str):
        self.labelDescription.setText(QCoreApplication.translate("GeorefProgressDialog", u"### {s}".format(s=description), None))

    def setPrimaryLabel(self, label: str):
        self.labelPrimary.setText(QCoreApplication.translate("GeorefProgressDialog", u"{s}".format(s=label), None))

    def setPrimaryProgress(self, curr: int):
        self.primaryCurr = curr
        self.progressBarPrimary.setValue(round(100.0 * self.primaryCurr / self.primaryTotal) if self.primaryTotal != 0 else -1)
    
    def setPrimaryTotal(self, total: int):
        self.primaryTotal = total
        self.setPrimaryProgress(0)
    
    def pushPrimaryProgress(self):
        self.setPrimaryProgress(self.primaryCurr + 1)

    def setSecondaryLabel(self, label: str):
        self.labelSecondary.setText(QCoreApplication.translate("GeorefProgressDialog", u"{s}".format(s=label), None))

    def setSecondaryProgress(self, curr: int):
        self.secondaryCurr = curr
        self.progressBarSecondary.setValue(round(100.0 * self.secondaryCurr / self.secondaryTotal) if self.secondaryTotal != 0 else -1)
    
    def setSecondaryTotal(self, total: int):
        self.secondaryTotal = total
        self.setSecondaryProgress(0)
    
    def pushSecondaryProgress(self):
        self.setSecondaryProgress(self.secondaryCurr + 1)

    def setTertiaryLabel(self, label: str):
        self.labelTertiary.setText(QCoreApplication.translate("GeorefProgressDialog", u"{s}".format(s=label), None))

    def setTertiaryProgress(self, curr: int):
        self.tertiaryCurr = curr
        self.progressBarTertiary.setValue(round(100.0 * self.tertiaryCurr / self.tertiaryTotal) if self.tertiaryTotal != 0 else -1)
    
    def setTertiaryTotal(self, total: int):
        self.tertiaryTotal = total
        self.setTertiaryProgress(0)
    
    def pushTertiaryProgress(self):
        self.setTertiaryProgress(self.tertiaryCurr + 1)
    
    def setBarsVisible(self, visible: bool):
        self.progressBarPrimary.setVisible(visible)
        self.progressBarSecondary.setVisible(visible)
        self.progressBarTertiary.setVisible(visible)
        self.labelPrimary.setVisible(visible)
        self.labelSecondary.setVisible(visible)
        self.labelTertiary.setVisible(visible)
    
    def cancel(self):
        self.__canceled = True
        self.setBarsVisible(False)
        self.setDescription(QCoreApplication.translate("GeorefProgressDialog", u"Canceling...", None))
    
    def wasCanceled(self):
        return self.__canceled
    
    def show(self):
        self.primaryCurr = 0
        self.secondaryCurr = 0
        self.tertiaryCurr = 0
        self.progressBarPrimary.setMinimum(0)
        self.progressBarSecondary.setMinimum(0)
        self.progressBarTertiary.setMinimum(0)
        self.setBarsVisible(True)
        self.__canceled = False
        super().show()
    