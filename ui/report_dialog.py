# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QDialog, QListWidgetItem
from .georef_report_dialog_base import Ui_GeorefReportDialog
import os

class GeorefReportDialog(QDialog, Ui_GeorefReportDialog):
    """Dialog to display the results of the batch georeferencing process."""
    def __init__(self, report, parent=None):
        """Constructor."""
        super(GeorefReportDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.populate_lists(report)
        
        # Connect signals
        self.buttonBox.accepted.connect(self.accept)

    def populate_lists(self, report):
        """Populate the success and failure list widgets."""
        self.listSuccess.clear()
        self.listFailed.clear()
        
        successful_results = [r for r in report.get("results", []) if r.get("success")]
        failed_results = [r for r in report.get("results", []) if not r.get("success")]
        
        if successful_results:
            for result in successful_results:
                item = QListWidgetItem(f"✅ {result['image']}")
                self.listSuccess.addItem(item)
        else:
            self.listSuccess.addItem("No images were successfully georeferenced.")
            
        if failed_results:
            for result in failed_results:
                item = QListWidgetItem(f"❌ {result['image']} - {result['message']}")
                self.listFailed.addItem(item)
        else:
            self.listFailed.addItem("No images failed during the process.")
            self.labelFailedInfo.setVisible(False)  # Hide info label if no failures

