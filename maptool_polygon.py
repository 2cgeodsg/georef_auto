from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsGeometry,
    QgsWkbTypes,
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsFields,
    QgsField,
)

class MapToolPolygon(QgsMapTool):
    """
    Map tool for drawing a polygon on the QGIS canvas.
    Emits a signal with the polygon geometry when finished.
    """
    polygon_finished = pyqtSignal(QgsGeometry)

    def __init__(self, canvas, epsg=None):
        """
        Initialize the map tool.
        
        Args:
            canvas: QGIS map canvas
            epsg: EPSG code for the CRS (e.g., 4326, 3857)
        """
        super().__init__(canvas)
        self.canvas = canvas
        self.epsg = epsg
        self.vertices = []

        # Create rubber band for visual feedback
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(255, 0, 0, 100))
        self.rubber_band.setWidth(2)
        self.rubber_band.show()

    def canvasPressEvent(self, event):
        """
        Handle canvas press events.
        Left click adds a vertex, right click finalizes the polygon.
        """
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.vertices.append(point)
            self.rubber_band.addPoint(point, True)

        elif event.button() == Qt.RightButton and len(self.vertices) >= 3:
            self.finalize_polygon()

    def finalize_polygon(self):
        """
        Finalize the polygon drawing and emit the geometry.
        """
        if len(self.vertices) < 3:
            return

        # Close the polygon
        self.rubber_band.addPoint(self.vertices[0], True)
        geom = QgsGeometry.fromPolygonXY([self.vertices])

        # Create temporary vector layer with correct CRS
        self._create_temporary_layer(geom)

        # Emit signal with the geometry
        self.polygon_finished.emit(geom)

        # Release mouse control
        self.canvas.unsetMapTool(self)

    def _create_temporary_layer(self, geometry):
        """
        Create a temporary vector layer to display the drawn polygon.
        
        Args:
            geometry: Polygon geometry
        """
        temp_layer = QgsVectorLayer("Polygon", "Drawn Polygon", "memory")
        if self.epsg:
            from qgis.core import QgsCoordinateReferenceSystem
            crs = QgsCoordinateReferenceSystem(self.epsg)
            temp_layer.setCrs(crs)
        
        provider = temp_layer.dataProvider()

        # Add minimal fields
        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        provider.addAttributes(fields)
        temp_layer.updateFields()

        # Add feature with geometry
        feature = QgsFeature()
        feature.setGeometry(geometry)
        feature.setAttributes([1])
        provider.addFeatures([feature])
        temp_layer.updateExtents()

        # Add layer to project
        QgsProject.instance().addMapLayer(temp_layer)

    def clear(self):
        """
        Clear the rubber band and vertices.
        """
        self.vertices.clear()
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        """
        Clean up when the tool is deactivated.
        """
        self.clear()
        super().deactivate()
