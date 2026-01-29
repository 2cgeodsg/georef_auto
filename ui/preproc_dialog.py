from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import QTimer
from qgis.core import QgsProject, QgsMapLayerType

from ..utils.qgis_utils import get_qgis_layers, is_layer_suitable_for_reference
from .georef_preproc_dialog_base import Ui_GeorefPreprocDialog


class GeorefPreprocDialog(QDialog, Ui_GeorefPreprocDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface


        self.reference_layer = None
        self.available_layers = []
        self.comboReferenceLayer.currentIndexChanged.connect(self.set_reference_layer)

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