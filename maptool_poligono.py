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

class MapToolPoligono(QgsMapTool):
    poligono_finalizado = pyqtSignal(QgsGeometry)

    def __init__(self, canvas, epsg=None):
        super().__init__(canvas)
        self.canvas = canvas
        self.epsg = epsg  # Ex: 4674, 31983 etc
        self.vertices = []

        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(255, 0, 0, 100))
        self.rubber_band.setWidth(2)
        self.rubber_band.show()

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            ponto = self.toMapCoordinates(event.pos())
            self.vertices.append(ponto)
            self.rubber_band.addPoint(ponto, True)

        elif event.button() == Qt.RightButton and len(self.vertices) >= 3:
            self.finalizar_poligono()

    def finalizar_poligono(self):
        if len(self.vertices) < 3:
            return

        # Fecha o polígono
        self.rubber_band.addPoint(self.vertices[0], True)
        geom = QgsGeometry.fromPolygonXY([self.vertices])

        # Cria a camada vetorial temporária com CRS correto
        self._criar_camadas_temporarias(geom)

        # Emite o sinal COM a geometria — só depois disso limpamos
        self.poligono_finalizado.emit(geom)

        # Deixa o polígono visível — não reseta rubber band aqui!
        self.canvas.unsetMapTool(self)  # Libera o controle do mouse

    def _criar_camadas_temporarias(self, geometria):
        camada_temp = QgsVectorLayer("Polygon", "Polígono Desenhado", "memory")
        if self.epsg:
            from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransformContext
            crs = QgsCoordinateReferenceSystem()
            crs = QgsCoordinateReferenceSystem(self.epsg)
            camada_temp.setCrs(crs)
        
        pr = camada_temp.dataProvider()

        # Campos mínimos, pode expandir depois
        campos = QgsFields()
        campos.append(QgsField("id", QVariant.Int))
        pr.addAttributes(campos)
        camada_temp.updateFields()

        feat = QgsFeature()
        feat.setGeometry(geometria)
        feat.setAttributes([1])
        pr.addFeatures([feat])
        camada_temp.updateExtents()

        QgsProject.instance().addMapLayer(camada_temp)

    def limpar(self):
        self.vertices.clear()
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self):
        self.limpar()
        super().deactivate()
