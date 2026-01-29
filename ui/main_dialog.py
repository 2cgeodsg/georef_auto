
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem
from qgis.PyQt.QtWidgets import QListWidgetItem
from qgis.core import QgsProject, QgsCoordinateReferenceSystem, QgsMapLayerType, QgsMapSettings
from qgis.gui import QgsMapCanvas


from .georef_auto_dialog_base import Ui_GeorefAuto_refatoreDialog
from .report_dialog import GeorefReportDialog
from .image_selection_dialog import SelecaoImagensDialog
from .map_tools import MapToolPolygon
from ..utils.qgis_utils import get_qgis_layers, is_layer_suitable_for_reference, get_area_in_square_km, add_raster_layer_to_qgis
from ..service.georeferencing_service import GeoreferencingService
from ..utils.logger import logger
from .cache_dialog import GeorefCacheDialog


import os
import psutil

MAX_POLYGON_AREA = 5000.0  # km²

class GeorefAuto_refatoreDialog(QDialog, Ui_GeorefAuto_refatoreDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self.georeferencing_service = GeoreferencingService(self.iface)

        mem_bytes = psutil.virtual_memory().total
        self.mem_total_gb = mem_bytes / (1024 ** 3)
        
        self.btnLoadSingleImage.clicked.connect(self.load_single_image)
        self.btnLoadMultipleImages.clicked.connect(self.load_multiple_images)
        self.btnRemoveImage.clicked.connect(self.remove_selected_images)
        self.btnDrawPolygon.clicked.connect(self.draw_polygon)
        self.btnGeoreference.clicked.connect(self.execute_georeferencing)
        self.btnCancel.clicked.connect(self.close)
        self.btn_mosaico_nao_georef = QPushButton("Create non-georeference mosaic")
        self.btn_mosaico_nao_georef.clicked.connect(self.create_non_georeferenced_mosaic)
        self.verticalLayout.addWidget(self.btn_mosaico_nao_georef)
        self.btnClearImages.clicked.connect(self.clear_all_images)
        self.btnCreateCache.clicked.connect(self.create_cache)

        self.image_paths = []
        self.polygon_geometry = None
        self.reference_layer = None
        self.available_layers = []
        self.batch_output_dir = None
        self.polygon_tool = None

        self.update_polygon_area_display()

        self.comboReferenceLayer.currentIndexChanged.connect(self.set_reference_layer)

        self.cache_dlg = GeorefCacheDialog(self.iface)
        
        try:
            QgsProject.instance().layersAdded.disconnect(self.refresh_layers)
            QgsProject.instance().layersRemoved.disconnect(self.refresh_layers)
        except TypeError:
            pass

        # Use QTimer.singleShot to defer a refresh to the next event loop tick.
        QgsProject.instance().layersAdded.connect(lambda layers=None: QTimer.singleShot(0, lambda: self.refresh_layers(layers)))
        QgsProject.instance().layersRemoved.connect(lambda layers=None: QTimer.singleShot(0, lambda: self.refresh_layers(layers)))

    #função para Clear All
    def clear_all_images(self):
        self.listImages.clear()
        self.image_paths = []
        self.update_polygon_area_display()

    def showEvent(self, event):
        QTimer.singleShot(0, self.refresh_layers)
        super().showEvent(event)

    def update_polygon_area_display(self):
        area_km2 = 0.0
        is_area_valid = False
        
        if self.polygon_geometry and self.reference_layer:
            area_km2 = get_area_in_square_km(self.polygon_geometry, "EPSG:3857")
            area_text = f"Area: {area_km2:.2f} km² (max: {MAX_POLYGON_AREA:,.0f} km²)"
            
            if area_km2 > MAX_POLYGON_AREA:
                self.labelPolygonArea.setStyleSheet("color: red; font-weight: bold;")
                self.labelPolygonStatus.setText("Area exceeds maximum! Please redraw polygon.")
                self.labelPolygonStatus.setStyleSheet("color: red;")
                is_area_valid = False
            else:
                self.labelPolygonArea.setStyleSheet("color: green; font-weight: bold;")
                self.labelPolygonStatus.setText("Polygon drawn successfully")
                self.labelPolygonStatus.setStyleSheet("")
                is_area_valid = True
        else:
            area_text = f"Area: 0.00 km² (max: {MAX_POLYGON_AREA:,.0f} km²)"
            self.labelPolygonArea.setStyleSheet("font-weight: bold;")
            self.labelPolygonStatus.setText("No polygon drawn" if not self.polygon_geometry else "Select reference layer")
            self.labelPolygonStatus.setStyleSheet("")
            is_area_valid = False
            
        self.labelPolygonArea.setText(area_text)
        self.btnGeoreference.setEnabled(is_area_valid and bool(self.image_paths))

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

        self.update_polygon_area_display()

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
        self.update_polygon_area_display()

    def load_single_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Aerial Image", "", "Images (*.tif *.jpg *.png *.jpeg)")
        if file_path:
            self.add_image_to_list(file_path)
        self.update_polygon_area_display()

    def load_multiple_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Aerial Images", "", "Images (*.tif *.jpg *.png *.jpeg)")
        if file_paths:
            for file_path in file_paths:
                self.add_image_to_list(file_path)
        self.update_polygon_area_display()

    def add_image_to_list(self, file_path):
        if file_path not in self.image_paths:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setData(Qt.UserRole, file_path)
            self.listImages.addItem(item)
            self.image_paths.append(file_path)

    def remove_selected_images(self):
        selected_items = self.listImages.selectedItems()
        for item in selected_items:
            file_path = item.data(Qt.UserRole)
            self.listImages.takeItem(self.listImages.row(item))
            if file_path in self.image_paths:
                self.image_paths.remove(file_path)
        self.update_polygon_area_display()

    def draw_polygon(self):
        if not self.reference_layer:
            QMessageBox.warning(self, "Error", "You must select a reference layer first.")
            return

        self.hide()
        canvas = self.iface.mapCanvas()
        self.polygon_tool = MapToolPolygon(canvas, self.reference_layer.crs().authid())
        self.polygon_tool.polygon_finished.connect(self.finalize_polygon)
        canvas.setMapTool(self.polygon_tool)

    def finalize_polygon(self, geometry):
        self.polygon_geometry = geometry
        QTimer.singleShot(0, self.update_polygon_area_display)
        try:
            self.iface.mapCanvas().unsetMapTool(self.polygon_tool)
        except RuntimeError:
            pass
        # se precisar que o diálogo apareça só depois de tudo:
        QTimer.singleShot(0, lambda: (self.show(), self.activateWindow()))

    def execute_georeferencing(self):
        if not self.image_paths:
            QMessageBox.warning(self, "Error", "No images selected.")
            return
        #change scale to 1:60.000 and return to original after processing
        canvas = self.iface.mapCanvas()
        original_scale = canvas.scale()
        original_scale_locked = canvas.scaleLocked()

        # def scale_to_60000
        canvas.zoomScale(60000)
        canvas.setScaleLocked(True)
        
        try:
            if len(self.image_paths) == 1:
                output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
                if not output_dir:
                    return

                base_name   = os.path.splitext(os.path.basename(self.image_paths[0]))[0]
                output_path = os.path.join(output_dir, f"{base_name}_georef.tif")

                ok, msg, output_path = self.georeferencing_service.georeference_single_image(
                    self.image_paths[0],
                    self.polygon_geometry,
                    self.reference_layer,
                    output_dir
                )
                if ok:
                    layer_name = os.path.splitext(os.path.basename(output_path))[0]
                    add_raster_layer_to_qgis(output_path, layer_name)
                    QMessageBox.information(self, "Success", msg)
                else:
                    QMessageBox.critical(self, "Error", msg)


            else:
                output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
                if not output_dir:
                    return
                self.batch_output_dir = output_dir
                success, report = self.georeferencing_service.georeference_batch(
                    self.image_paths, self.polygon_geometry, self.reference_layer, self.batch_output_dir
                )
                report_dialog = GeorefReportDialog(report, self)
                report_dialog.exec_()
            
                
            ## Considerations:
            ##* The restoration of scale and lock state should be done in both the `if success:` and `else:` blocks to ensure the scale is restored regardless of the georeferencing outcome.
            ##* If georeferencing is a long-running asynchronous process, the scale restoration should be done in a callback or signal indicating the end of processing, not immediately after the service call.

        finally:
            # Allways restore, even if there's an error or the dialog is closed early
            canvas.setScaleLocked(original_scale_locked)
            canvas.zoomScale(original_scale)

    def create_non_georeferenced_mosaic(self):
        if not self.image_paths:
            QMessageBox.warning(self, "Error", "No images selected.")
            return
        
        output_path = QFileDialog.getExistingDirectory(self, "Select Output Directory for Mosaic")
        if not output_path:
            return

        success, message = self.georeferencing_service.create_non_georeferenced_mosaic(self.image_paths, output_path)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
    
    def create_cache(self):
        # show the dialog
        self.cache_dlg.show()


