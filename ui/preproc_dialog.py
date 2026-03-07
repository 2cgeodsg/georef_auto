import asyncio
import threading
from time import sleep
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QTimer, QCoreApplication, QThread
from qgis.core import QgsProject, QgsMapLayerType

from ..utils.qgis_utils import get_qgis_layers, is_layer_suitable_for_reference
from .georef_preproc_dialog_base import Ui_GeorefPreprocDialog
from ..service.miguessing_service import MIGuessingParams, MIGuessingReferenceLayer, MIGuessingReferenceWMS, MIGuessingService
from .progress_dialog import GeorefProgressDialog
from ..sources.wms_sources import WMSSource, WMSSources


class GeorefPreprocDialog(QDialog, Ui_GeorefPreprocDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface

        self.btnLocate.clicked.connect(self.execute_image_search)
        self.btnCancel.clicked.connect(self.close)

        self.reference_layer = None
        self.available_layers = []
        self.comboReferenceLayer.currentIndexChanged.connect(self.set_reference_layer)

        project = QgsProject.instance()
        assert project # Expected to run this in QGIS

        try:
            project.layersAdded.disconnect(self.refresh_layers)
            project.layersRemoved.disconnect(self.refresh_layers)
        except TypeError:
            pass

        # Use QTimer.singleShot to defer a refresh to the next event loop tick.
        project.layersAdded.connect(lambda layers=None: QTimer.singleShot(0, lambda: self.refresh_layers(layers)))
        project.layersRemoved.connect(lambda layers=None: QTimer.singleShot(0, lambda: self.refresh_layers(layers)))

        if self.comboWMSLayer.count() == 1:
            self.comboWMSLayer.removeItem(0)
            sources = WMSSources.list_sources()
            for i, sid in enumerate(sources):
                src = WMSSource(sid)
                if not src.metadata:
                    self.comboWMSLayer.insertItem(i, f"ERROR: Failed to read metadata for {sid} (do not select this option)")
                    continue
                if not src.icon:
                    self.comboWMSLayer.insertItem(i, src.alias)
                    continue
                self.comboWMSLayer.insertItem(i, src.icon, src.alias)
            if len(sources) == 0:
                self.comboWMSLayer.insertItem(0, f"ERROR: No wms sources found in {WMSSources.get_wms_dir()}")

        project = QgsProject.instance()
        assert project

        try:
            project.layersAdded.disconnect(self.refresh_layers)
            project.layersRemoved.disconnect(self.refresh_layers)
        except TypeError:
            pass

        # Use QTimer.singleShot to defer a refresh to the next event loop tick.
        project.layersAdded.connect(lambda layers=None: QTimer.singleShot(0, lambda: self.refresh_layers(layers)))
        project.layersRemoved.connect(lambda layers=None: QTimer.singleShot(0, lambda: self.refresh_layers(layers)))

        self.progress_dlg = GeorefProgressDialog(iface)
        self.progress_dlg.setTitle("Buscando...")
        self.progress_dlg.setDescription("Procurando locais possíveis")
    
    def showEvent(self, event):
        QTimer.singleShot(0, self.refresh_layers)
        super().showEvent(event)
    
    def refresh_layers(self, layers=None):
        current_layer_id = None
        layer_obj = getattr(self, "reference_layer", None)

        # Proteção total contra objetos destruídos
        if layer_obj is not None:
            try:
                if layer_obj.isValid():
                    current_layer_id = layer_obj.id()
                else:
                    self.reference_layer = None
            except RuntimeError:
                # O objeto C++ foi destruído — limpar a referência
                self.reference_layer = None
                current_layer_id = None
        else:
            self.reference_layer = None

        self.load_layers()

        if current_layer_id:
            found_current = False
            for i, layer in enumerate(self.available_layers):
                try:
                    if layer and layer.isValid() and layer.id() == current_layer_id:
                        self.comboReferenceLayer.setCurrentIndex(i + 1)
                        self.reference_layer = layer
                        found_current = True
                        break
                except RuntimeError:
                    continue

            if not found_current:
                self.comboReferenceLayer.setCurrentIndex(0)
                self.reference_layer = None
        else:
            self.comboReferenceLayer.setCurrentIndex(0)
            self.reference_layer = None

    def load_layers(self):
        self.comboReferenceLayer.clear()
        self.comboReferenceLayer.addItem("Select reference layer")
        self.available_layers = []

        all_layers = get_qgis_layers()
        for layer in all_layers:
            if is_layer_suitable_for_reference(layer):
                label = layer.name()
                provider_name = layer.dataProvider().name() if layer.dataProvider() else ""
                if provider_name.lower() in ["wms", "wmts", "xyz"]:
                    label += f" ({provider_name.upper()})"
                elif layer.type() == QgsMapLayerType.VectorLayer:
                    label += f" (Vector)"
                self.comboReferenceLayer.addItem(label)
                self.available_layers.append(layer)

    def set_reference_layer(self, index):
        if index > 0:
            selected_layer = self.available_layers[index - 1]
            if selected_layer and selected_layer.isValid():
                self.reference_layer = selected_layer
            else:
                self.reference_layer = None
        else:
            self.reference_layer = None
    
    def getImagePath(self):
        return self.fileImage.filePath()
    
    def getImageSpatialRes(self):
        return self.spatialResolutionDoubleSpinBox.value()

    def getAddMiToProject(self):
        return self.checkBoxAddToProject.isChecked()
    
    def getSource(self) -> WMSSource:
        return WMSSource(WMSSources.list_sources()[self.comboWMSLayer.currentIndex()])

    def getReference(self):
        match self.tabWidget.currentIndex():
            case 0:
                return MIGuessingReferenceWMS(
                    source=self.getSource(),
                    cache_folder=self.widgetCache.filePath()
                )
            case 1:
                return MIGuessingReferenceLayer(
                    reference_layer=self.reference_layer
                )
            case _:
                raise IndexError("Invalid tab")

    def execute_image_search(self):
        self.btnLocate.setEnabled(False)
        # Setup thread
        self.thread = QThread()
        # Setup service
        self.mgs = MIGuessingService()
        params = MIGuessingParams(
            image_path=self.getImagePath(),
            image_spatialres=self.getImageSpatialRes(),
            add_possible_mi_to_project=self.getAddMiToProject(),
            reference=self.getReference()
        )
        self.mgs.moveToThread(self.thread)
        # Setup progress dialog
        self.progress_dlg.setPrimaryLabel("")
        self.progress_dlg.setSecondaryLabel("")
        self.progress_dlg.setTertiaryLabel("")
        self.progress_dlg.setPrimaryTotal(0)
        self.progress_dlg.setSecondaryTotal(0)
        self.progress_dlg.setTertiaryTotal(0)
        QCoreApplication.processEvents()
        # Set params
        self.mgs.setParams(params)
        # Connect signals and cancelations
        self.mgs.setCanceled(self.progress_dlg.wasCanceled)
        self.mgs.connectProgressDialog(self.progress_dlg)
        self.mgs.done.connect(self.on_image_search_done)
        # Execute
        self.thread.started.connect(self.mgs.start)
        self.thread.start()
        # Show progres
        self.progress_dlg.show()
        
    
    def on_image_search_done(self):
        result = self.mgs.result
        self.progress_dlg.setDescription("SUCESSO" if result else "BARRO")
        QCoreApplication.processEvents()
        for n in range(30):
            sleep(0.1)
            QCoreApplication.processEvents()
        self.progress_dlg.hide()
        self.btnLocate.setEnabled(True)
