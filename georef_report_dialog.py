# -*- coding: utf-8 -*-

from qgis.PyQt.QtWidgets import QDialog, QListWidgetItem
from .georef_report_dialog_base import Ui_GeorefReportDialog
import os

class GeorefReportDialog(QDialog, Ui_GeorefReportDialog):
    """Dialog to display the results of the batch georeferencing process."""
    def __init__(self, successful_outputs, failed_images, parent=None):
        """Constructor."""
        super(GeorefReportDialog, self).__init__(parent)
        self.setupUi(self)
        
        self.populate_lists(successful_outputs, failed_images)
        
        # Connect signals
        self.buttonBox.accepted.connect(self.accept)

    def populate_lists(self, successful_outputs, failed_images):
        """Populate the success and failure list widgets."""
        self.listSuccess.clear()
        self.listFailed.clear()
        
        if successful_outputs:
            for output_path in successful_outputs:
                item = QListWidgetItem(f"✅ {os.path.basename(output_path)}")
                self.listSuccess.addItem(item)
        else:
            self.listSuccess.addItem("No images were successfully georeferenced.")
            
        if failed_images:
            for img_name in failed_images:
                item = QListWidgetItem(f"❌ {img_name}")
                self.listFailed.addItem(item)
        else:
            self.listFailed.addItem("No images failed during the process.")
            self.labelFailedInfo.setVisible(False) # Hide info label if no failures

