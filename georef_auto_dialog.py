from qgis.gui import QgsMapToolCapture
from PyQt5.QtCore import Qt
from .maptool_polygon import MapToolPolygon
from qgis.core import (
    QgsProject, QgsRasterLayer, QgsGeometry, QgsMapLayer, QgsLayerTree,
    QgsVectorLayer, QgsCoordinateReferenceSystem, QgsMapLayerType
)
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, QListWidgetItem
from .georef_auto_dialog_base import Ui_GeorefAutoDialog
from .georeferencing import georeference_image, batch_georeference, get_area_in_square_km, MAX_POLYGON_AREA
from .georef_report_dialog import GeorefReportDialog # Import the report dialog
import os
import logging # Use logging

# Setup logginlogging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeorefAutoDialog(QDialog, Ui_GeorefAutoDialog):
    def __init__(self, iface, parent=None):
        """
        Initialize the dialog.
        
        Args:
            iface: QGIS interface
            parent: Parent widget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface
        
        # Connect buttons to functions
        self.btnLoadSingleImage.clicked.connect(self.load_single_image)
        self.btnLoadMultipleImages.clicked.connect(self.load_multiple_images)
        self.btnRemoveImage.clicked.connect(self.remove_selected_images)
        self.btnClearImages.clicked.connect(self.clear_all_images)
        self.btnDrawPolygon.clicked.connect(self.draw_polygon)
        self.btnGeoreference.clicked.connect(self.execute_georeferencing)
        self.btnCancel.clicked.connect(self.close)

        # Initialize variables
        self.image_paths = []
        self.polygon_geometry = None
        self.reference_layer = None
        self.available_layers = []
        self.batch_output_dir = None  # Initialize batch output directory
        self.polygon_tool = None  # Initialize polygon tool

        # Initialize polygon area display and button state
        self.update_polygon_area_display()

        # Load available layers initially
        # self.load_layers() # Moved to showEvent to ensure freshness
        self.comboReferenceLayer.currentIndexChanged.connect(self.set_reference_layer)
        
        # Connect to layer registry signals to update layers when added/removed
        # Ensure signals are connected only once if __init__ could be called multiple times
        try:
            QgsProject.instance().layersAdded.disconnect(self.refresh_layers)
            QgsProject.instance().layersRemoved.disconnect(self.refresh_layers)
            logging.info("Disconnected existing project signals before reconnecting.")
        except TypeError:
            logging.info("Project signals not previously connected or already disconnected.")
            pass # Ignore if not connected
        except Exception as e:
             logging.warning(f"Error disconnecting project signals: {e}")
             
        try:
            QgsProject.instance().layersAdded.connect(self.refresh_layers)
            QgsProject.instance().layersRemoved.connect(self.refresh_layers)
            logging.info("Connected project signals (layersAdded, layersRemoved).")
        except Exception as e:
            logging.error(f"Error connecting project signals: {e}")

    def showEvent(self, event):
        """
        Called when the dialog is shown. Refresh the layer list.
        """
        logging.info("GeorefAutoDialog showEvent called. Refreshing layers.")
        self.refresh_layers() # Ensure layers are up-to-date when shown
        super().showEvent(event) # Call base class implementation

    def update_polygon_area_display(self):
        """
        Update the polygon area display and georeference button state in the UI.
        """
        area_km2 = 0.0
        is_area_valid = False
        
        if self.polygon_geometry and self.reference_layer:
            # Calculate area in square kilometers
            area_km2 = get_area_in_square_km(self.polygon_geometry, self.reference_layer.crs().authid())
            
            # Format area with 2 decimal places
            area_text = f"Area: {area_km2:.2f} km² (max: {MAX_POLYGON_AREA:,.0f} km²)"
            
            # Set color and status based on area size
            if area_km2 > MAX_POLYGON_AREA:
                # Red for exceeding maximum
                self.labelPolygonArea.setStyleSheet("color: red; font-weight: bold;")
                self.labelPolygonStatus.setText("Area exceeds maximum! Please redraw polygon.")
                self.labelPolygonStatus.setStyleSheet("color: red;")
                is_area_valid = False
            elif area_km2 > MAX_POLYGON_AREA * 0.8:
                # Orange for approaching maximum
                self.labelPolygonArea.setStyleSheet("color: orange; font-weight: bold;")
                self.labelPolygonStatus.setText("Polygon drawn successfully")
                self.labelPolygonStatus.setStyleSheet("")
                is_area_valid = True
            else:
                # Green for acceptable area
                self.labelPolygonArea.setStyleSheet("color: green; font-weight: bold;")
                self.labelPolygonStatus.setText("Polygon drawn successfully")
                self.labelPolygonStatus.setStyleSheet("")
                is_area_valid = True
        else:
            # No polygon drawn yet or no reference layer
            area_text = f"Area: 0.00 km² (max: {MAX_POLYGON_AREA:,.0f} km²)"
            self.labelPolygonArea.setStyleSheet("font-weight: bold;")
            if self.polygon_geometry:
                self.labelPolygonStatus.setText("Select reference layer to calculate area")
                self.labelPolygonStatus.setStyleSheet("")
            else:
                self.labelPolygonStatus.setText("No polygon drawn")
                self.labelPolygonStatus.setStyleSheet("")
            is_area_valid = False
            
        self.labelPolygonArea.setText(area_text)
        
        # Enable/disable georeference button based on area validity
        # Also check if images are loaded
        self.btnGeoreference.setEnabled(is_area_valid and bool(self.image_paths))

    def refresh_layers(self, layers=None):
        """
        Refresh the layers list when layers are added or removed, or when dialog is shown.
        
        Args:
            layers: List of layers (not used, but required for signal connection)
        """
        logging.info("Refreshing layer list...")
        # Store current selection ID if a valid layer is selected
        current_layer_id = None
        if self.reference_layer and self.reference_layer.isValid():
            current_layer_id = self.reference_layer.id()
            logging.info(f"Current reference layer ID: {current_layer_id}")
        else:
            logging.info("No valid reference layer currently selected.")
            self.reference_layer = None # Ensure it\'s None if invalid
        
        # Reload layers
        self.load_layers()
        
        # Try to restore previous selection by ID
        restored = False
        if current_layer_id:
            # Find the layer in the new list by ID
            for i, layer in enumerate(self.available_layers):
                if layer and layer.isValid() and layer.id() == current_layer_id:
                    new_index = i + 1 # +1 for "Select reference layer" placeholder
                    self.comboReferenceLayer.setCurrentIndex(new_index)
                    # Explicitly set self.reference_layer as currentIndexChanged might not fire if index is same
                    self.reference_layer = layer 
                    logging.info(f"Restored selection to layer ID: {current_layer_id} at index {new_index}")
                    restored = True
                    break
        
        # If we couldn\'t find the previous layer or none was selected, reset to index 0
        if not restored:
            logging.info("Could not restore previous selection or none existed. Setting index to 0.")
            self.comboReferenceLayer.setCurrentIndex(0)
            self.reference_layer = None
            
        # Update UI elements that depend on the reference layer
        self.update_polygon_area_display()

    def load_single_image(self):
        """
        Load a single image file.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Aerial Image", "", "Images (*.tif *.jpg *.png *.jpeg)"
        )
        if file_path:
            self.add_image_to_list(file_path)
        # Update button state after loading image
        self.update_polygon_area_display()

    def load_multiple_images(self):
        """
        Load multiple image files.
        """
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Aerial Images", "", "Images (*.tif *.jpg *.png *.jpeg)"
        )
        if file_paths:
            for file_path in file_paths:
                self.add_image_to_list(file_path)
        # Update button state after loading images
        self.update_polygon_area_display()

    def add_image_to_list(self, file_path):
        """
        Add an image path to the list widget.
        
        Args:
            file_path: Path to the image file
        """
        # Check if image is already in the list
        for i in range(self.listImages.count()):
            if self.listImages.item(i).data(Qt.UserRole) == file_path:
                logging.warning(f"Image already in list: {file_path}")
                return
                
        # Add to list widget
        item = QListWidgetItem(os.path.basename(file_path))
        item.setData(Qt.UserRole, file_path)
        self.listImages.addItem(item)
        self.image_paths.append(file_path)
        logging.info(f"Added image to list: {file_path}")

    def remove_selected_images(self):
        """
        Remove selected images from the list.
        """
        selected_items = self.listImages.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            file_path = item.data(Qt.UserRole)
            row = self.listImages.row(item)
            self.listImages.takeItem(row)
            if file_path in self.image_paths:
                self.image_paths.remove(file_path)
                logging.info(f"Removed image from list: {file_path}")
        # Update button state after removing images
        self.update_polygon_area_display()

    def clear_all_images(self):
        """
        Clear all images from the list.
        """
        self.listImages.clear()
        self.image_paths = []
        logging.info("Cleared all images from list.")
        # Update button state after clearing images
        self.update_polygon_area_display()

    def draw_polygon(self):
        """
        Activate the polygon drawing tool.
        """
        if not self.reference_layer:
            QMessageBox.warning(self, "Error", "You must select a reference layer first.")
            return

        self.hide()  # Minimize the plugin window

        canvas = self.iface.mapCanvas()
        crs_reference = self.reference_layer.crs()

        self.polygon_tool = MapToolPolygon(canvas, crs_reference.authid())
        self.polygon_tool.polygon_finished.connect(self.finalize_polygon)
        canvas.setMapTool(self.polygon_tool)
        logging.info("Polygon drawing tool activated.")

    def finalize_polygon(self, geometry):
        """
        Handle the polygon drawing completion.
        
        Args:
            geometry: The drawn polygon geometry
        """
        self.polygon_geometry = geometry
        logging.info("Polygon drawing finished.")
        
        # Calculate and display polygon area, update button state
        self.update_polygon_area_display()
        
        # Deactivate the tool
        if self.iface.mapCanvas().mapTool() == self.polygon_tool:
            self.iface.mapCanvas().unsetMapTool(self.polygon_tool)
            logging.info("Polygon drawing tool deactivated.")
            
        # Clean up tool reference and signal connection
        try:
            self.polygon_tool.polygon_finished.disconnect(self.finalize_polygon)
        except TypeError:
            pass # Signal not connected or already disconnected
        self.polygon_tool = None
            
        self.show()
        self.activateWindow()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

    def is_layer_suitable_for_reference(self, layer):
        """
        Check if a layer is suitable to be used as a reference layer.
        
        Args:
            layer: The layer to check
            
        Returns:
            bool: True if the layer is suitable, False otherwise
        """
        if not layer or not layer.isValid():
            # logging.debug(f"Layer invalid or None: {layer.name() if layer else \'None\'}")
            return False
            
        # Check layer type
        layer_type = layer.type()
        # logging.debug(f"Checking layer: {layer.name()}, Type: {layer_type}")
        
        if layer_type == QgsMapLayer.RasterLayer:
            # logging.debug(f"Layer {layer.name()} is a suitable RasterLayer.")
            return True
            
        # Allow Vector layers (e.g., from WFS, PostGIS, or even shapefiles if styled)
        if layer_type == QgsMapLayer.VectorLayer:
            # Only include vector layers with valid CRS
            if layer.crs().isValid():
                # logging.debug(f"Layer {layer.name()} is a suitable VectorLayer with valid CRS.")
                return True
            else:
                # logging.debug(f"Layer {layer.name()} is VectorLayer but has invalid CRS.")
                return False
                
        # Allow WMS/WMTS layers (often identified as RasterLayer, but check provider)
        # This check might be redundant if they are already caught as RasterLayer
        # provider = layer.dataProvider()
        # if provider and provider.name().lower() in ["wms", "wmts", "xyz"]:
        #     logging.debug(f"Layer {layer.name()} is a suitable WMS/WMTS/XYZ layer.")
        #     return True
            
        # logging.debug(f"Layer {layer.name()} is not a suitable reference type.")
        return False

    def load_layers(self):
        """
        Load available layers into the combo box.
        """
        self.comboReferenceLayer.clear()
        self.comboReferenceLayer.addItem("Select reference layer")
        self.available_layers = []
        found_layers_count = 0

        try:
            # Get all map layers from the project registry
            all_layers = list(QgsProject.instance().mapLayers().values())
            logging.info(f"Found {len(all_layers)} layers in project registry.")
            
            # Process layers from registry
            processed_ids = set()
            for layer in all_layers:
                try:
                    if layer.id() in processed_ids:
                        continue # Skip duplicates if any
                    
                    # Check if layer is suitable for reference
                    if self.is_layer_suitable_for_reference(layer):
                        # Add layer to combo box with appropriate label
                        label = layer.name()
                        provider_name = layer.dataProvider().name() if layer.dataProvider() else "Unknown"
                        if provider_name.lower() in ["wms", "wmts", "xyz"]:
                            label += f" ({provider_name.upper()})"
                        elif layer.type() == QgsMapLayer.VectorLayer:
                             label += f" (Vector)"
                             
                        self.comboReferenceLayer.addItem(label)
                        self.available_layers.append(layer)
                        processed_ids.add(layer.id())
                        found_layers_count += 1
                    # else:
                        # logging.debug(f"Skipping unsuitable layer: {layer.name()}")
                except Exception as inner_e:
                    logging.warning(f"Error processing layer {layer.name() if layer else 'Unknown'}: {inner_e}")
            
            logging.info(f"Added {found_layers_count} suitable layers to the combo box.")

        except Exception as e:
            logging.error(f"Error loading layers: {e}")
            # Optionally show a message to the user
            # QMessageBox.critical(self, "Error", "Could not load layers.")

    def set_reference_layer(self, index):
        """
        Set the reference layer based on combo box selection.
        
        Args:
            index: Selected index in the combo box
        """
        try:
            if index == 0:
                if self.reference_layer is not None:
                    logging.info("Reference layer deselected.")
                    self.reference_layer = None
            elif 1 <= index <= len(self.available_layers):
                # Get the layer from available_layers
                layer = self.available_layers[index - 1]
                
                # Check if the layer is still valid
                if layer and layer.isValid():
                    if self.reference_layer is None or self.reference_layer.id() != layer.id():
                        self.reference_layer = layer
                        logging.info(f"Selected reference layer: {self.reference_layer.name()} (ID: {self.reference_layer.id()})")
                        # Update polygon area display and button state if polygon exists
                        self.update_polygon_area_display()
                    # else: layer already selected, do nothing
                else:
                    logging.warning(f"Selected layer at index {index} is no longer valid.")
                    self.reference_layer = None
                    # Reset combo box to index 0 and show warning
                    self.comboReferenceLayer.setCurrentIndex(0)
                    QMessageBox.warning(self, "Error", "The selected layer is no longer valid. Please select another layer.")
            else:
                logging.warning(f"Invalid index selected: {index}")
                self.reference_layer = None
                # Reset combo box to index 0 if index is out of bounds
                if self.comboReferenceLayer.currentIndex() != 0:
                    self.comboReferenceLayer.setCurrentIndex(0)
                    
        except Exception as e:
            logging.error(f"Error setting reference layer: {str(e)}")
            self.reference_layer = None
            # Reset combo box to index 0
            if self.comboReferenceLayer.currentIndex() != 0:
                self.comboReferenceLayer.setCurrentIndex(0)
            
        # Update button state even if layer selection fails or changes to None
        self.update_polygon_area_display()

    def execute_georeferencing(self):
        """
        Execute the georeferencing process for all loaded images.
        """
        # Validate inputs
        if not self.image_paths:
            QMessageBox.warning(self, "Error", "You must load at least one image.")
            return

        if not self.polygon_geometry:
            QMessageBox.warning(self, "Error", "You must draw a bounding polygon first.")
            return

        if not self.reference_layer:
            QMessageBox.warning(self, "Error", "You must select a reference layer.")
            return
            
        # Check polygon area again before proceeding
        area_km2 = get_area_in_square_km(self.polygon_geometry, self.reference_layer.crs().authid())
        if area_km2 > MAX_POLYGON_AREA:
             QMessageBox.critical(self, "Error", f"Polygon area ({area_km2:.2f} km²) exceeds the maximum allowed ({MAX_POLYGON_AREA:,.0f} km²). Please redraw the polygon.")
             return

        # Get output directory
        if len(self.image_paths) > 1:
            # Batch mode: Ask for output directory
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory for Georeferenced Images")
            if not output_dir:
                return # User cancelled
            self.batch_output_dir = output_dir
        else:
            # Single image mode: Ask for output file path
            input_filename = os.path.basename(self.image_paths[0])
            default_output_name = os.path.splitext(input_filename)[0] + "_georef.tif"
            output_path, _ = QFileDialog.getSaveFileName(
                self, "Save Georeferenced Image", default_output_name, "GeoTIFF (*.tif)"
            )
            if not output_path:
                return # User cancelled
            # For single image, use the directory of the output path for batch_output_dir logic
            # Ensure the output path from QFileDialog is used directly for the single image
            self.batch_output_dir = os.path.dirname(output_path)
            # Overwrite image_paths for single file case to ensure correct output path is used
            self.image_paths = [self.image_paths[0]] # Keep original path for input
            # Store the specific output path for the single image
            single_output_path = output_path 

        logging.info(f"Starting georeferencing. Images: {len(self.image_paths)}, Output Dir/Path: {self.batch_output_dir if len(self.image_paths) > 1 else single_output_path}")
        
        # Execute georeferencing
        try:
            successful_outputs, failed_images = batch_georeference(
                self.image_paths,
                self.polygon_geometry,
                self.reference_layer,
                self # Pass the dialog instance
            )
            
            logging.info(f"Georeferencing finished. Success: {len(successful_outputs)}, Failed: {len(failed_images)}")
            
            # Show report dialog
            report_dialog = GeorefReportDialog(successful_outputs, failed_images, self)
            report_dialog.exec_()
            
            # --- ADD LAYER TO PROJECT --- 
            # Check if the option is enabled
            if self.checkBoxAddToProject.isChecked():
                logging.info("Adding successful outputs to the project.")
                added_count = 0
                for output_path in successful_outputs:
                    try:
                        layer_name = os.path.basename(output_path)
                        # Use iface.addRasterLayer to add the layer
                        rlayer = self.iface.addRasterLayer(output_path, layer_name)
                        if rlayer and rlayer.isValid():
                            logging.info(f"Successfully added layer: {layer_name}")
                            added_count += 1
                        else:
                            logging.warning(f"Failed to add layer: {layer_name} from path: {output_path}")
                            # Optionally inform user via message box or keep in report
                            # QMessageBox.warning(self, "Layer Loading Error", f"Could not load the georeferenced layer: {layer_name}")
                    except Exception as add_e:
                        logging.error(f"Error adding layer {output_path} to project: {add_e}")
                        # Optionally inform user
                        # QMessageBox.critical(self, "Layer Loading Error", f"An error occurred while adding {os.path.basename(output_path)}: {add_e}")
                if added_count > 0:
                     self.iface.messageBar().pushMessage("Success", f"{added_count} georeferenced image(s) added to the project.", level=1, duration=5) # Qgis.Success = 1
            else:
                logging.info("Option to add layers to project is disabled.")
            # --- END ADD LAYER TO PROJECT ---
            
        except Exception as e:
            logging.error(f"An unexpected error occurred during batch georeferencing: {e}")
            logging.error(traceback.format_exc())
            QMessageBox.critical(self, "Georeferencing Error", f"An unexpected error occurred: {str(e)}")

        # Reset state after processing (optional, maybe keep polygon/layer?)
        # Consider clearing only images if user might want to reuse polygon/layer
        # self.clear_all_images() # Clear images after processing?
        # self.polygon_geometry = None # Clear polygon?
        # self.update_polygon_area_display() # Update UI

    def closeEvent(self, event):
        """
        Handle the dialog closing event.
        Clean up map tool and reset state, but keep project signal connections.
        """
        logging.info("GeorefAutoDialog closeEvent called.")
        
        # Clean up map tool if it exists and is active
        if self.polygon_tool:
            try:
                # Ensure the tool is unset from the canvas
                if self.iface.mapCanvas().mapTool() == self.polygon_tool:
                    self.iface.mapCanvas().unsetMapTool(self.polygon_tool)
                    logging.info("Unset active polygon tool.")
                # Disconnect signals associated with the tool
                try:
                    self.polygon_tool.polygon_finished.disconnect(self.finalize_polygon)
                except TypeError:
                    pass # Signal not connected or already disconnected
            except Exception as e:
                logging.warning(f"Error cleaning up polygon tool: {e}")
            self.polygon_tool = None # Clear reference
            
        # DO NOT Disconnect project signals here. Let the main plugin class handle them.

        # Reset internal state variables for the next run
        self.image_paths = []
        self.polygon_geometry = None
        self.reference_layer = None 
        self.available_layers = [] # Will be reloaded by refresh_layers on show
        self.batch_output_dir = None
        
        # Clear UI elements
        self.listImages.clear()
        # comboReferenceLayer will be repopulated by refresh_layers on show
        self.comboReferenceLayer.clear() 
        self.comboReferenceLayer.addItem("Select reference layer") 
        self.update_polygon_area_display() # Reset area display and button states

        logging.info("GeorefAutoDialog state reset.")
        
        # Accept the close event (hides the dialog)
        event.accept()

