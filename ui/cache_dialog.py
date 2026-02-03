from math import floor

from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QThread
from qgis.core import QgsRectangle

from ..utils import logger
from .georef_cache_dialog_base import Ui_GeorefCacheDialog
from ..service.webmapcache_service import WebMapCacheService
from ..sources.wms_sources import WMSSource, WMSSources


class GeorefCacheDialog(QDialog, Ui_GeorefCacheDialog):

    FEEDBACK_LINE_TEMPLATE = """<p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" color:{};">{}</span></p><br>"""
    FEEDBACK_DEBUG_COLOR = "#6e6e6e"
    FEEDBACK_INFO_COLOR = "#000000"
    FEEDBACK_WARNING_COLOR = "#c79200"
    FEEDBACK_ERROR_COLOR = "#a30000"
    FEEDBACK_COLORS = [FEEDBACK_DEBUG_COLOR, FEEDBACK_INFO_COLOR, FEEDBACK_WARNING_COLOR, FEEDBACK_ERROR_COLOR]
        

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface

        self.btnCreateCache.clicked.connect(self.create_cache)

        if self.comboBoxWMS.count() == 1:
            self.comboBoxWMS.removeItem(0)
            sources = WMSSources.list_sources()
            for i, sid in enumerate(sources):
                src = WMSSource(sid)
                if not src.metadata:
                    self.comboBoxWMS.insertItem(i, f"ERROR: Failed to read metadata for {sid} (do not select this option)")
                    continue
                if not src.icon:
                    self.comboBoxWMS.insertItem(i, src.alias)
                    continue
                self.comboBoxWMS.insertItem(i, src.icon, src.alias)
            if len(sources) == 0:
                self.comboBoxWMS.insertItem(0, f"ERROR: No wms sources found in {WMSSources.get_wms_dir()}")
    
    def show(self):
        super().show()
        self.textBrowserLog.clear()

    def log(self, message, level: int = 1):
        color = self.FEEDBACK_COLORS[level]
        line = self.FEEDBACK_LINE_TEMPLATE.format(color, message)
        self.textBrowserLog.insertHtml(line)
        # self.textBrowserLog.insertPlainText(message)
        logger.logger.info(message)
    
    def progress(self):
        self.current += 1
        self.progressBar.setValue(self.current)
    
    def startProgress(self, total: int):
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(total)
        self.current = 0
    
    def getExtent(self) -> QgsRectangle:
        return self.widgetExtent.outputExtent()
    
    def getZoomLevel(self) -> int:
        return self.scaleComboBox.currentIndex() + 8

    def getOutputPath(self) -> str:
        return self.widgetOutputFile.filePath()

    def getSource(self) -> WMSSource:
        return WMSSource(WMSSources.list_sources()[self.comboBoxWMS.currentIndex()])

    def create_cache(self):
        self.log("--------", 1)
        self.btnCreateCache.setEnabled(False)
        self.tabWidget.setCurrentIndex(1)

        self.thread = QThread()
        self.wmcs = WebMapCacheService()
        self.wmcs.setParams(
            mbtiles_realpath=self.getOutputPath(), 
            source=self.getSource(), 
            bounding_box=self.getExtent(), 
            zoom_level=self.getZoomLevel()
        )
        self.wmcs.message_logged.connect(self.log)
        self.wmcs.progress_pushed.connect(self.progress)
        self.wmcs.progress_started.connect(self.startProgress)

        self.wmcs.moveToThread(self.thread)
        self.wmcs.done.connect(self.cache_done)
        self.thread.started.connect(self.wmcs.run)
        self.thread.start()
    
    def cache_done(self):
        self.btnCreateCache.setEnabled(True)