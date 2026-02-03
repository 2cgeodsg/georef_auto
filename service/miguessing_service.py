# service/mirguessing_service.py
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from math import pow, sqrt
import os
from typing import Callable

from qgis.core import QgsMapLayer, QgsGeometry, QgsRectangle, Qgis, QgsPointXY, QgsRasterLayer
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from ..service.webmapcache_service import WebMapCacheService
from ..core.config import GeoreferencingConfig
from ..core.miguessing import carregarImagem, divideWithMetricSuperposition, isPossibleLocation
from ..sources.wms_sources import WMSSource
from ..utils.progress_dialog import ProgressDialog


@dataclass(frozen=True)
class MIGuessingReferenceWMS:
    source: WMSSource
    cache_folder: str

@dataclass(frozen=True)
class MIGuessingReferenceLayer:
    reference_layer: QgsMapLayer

@dataclass(frozen=True)
class MIGuessingParams:
    image_path: str
    image_spatialres: float
    add_possible_mi_to_project: bool
    reference: MIGuessingReferenceWMS | MIGuessingReferenceLayer


class MIGuessingService(QObject):
    """Serviço de alto nível para encontrar o(s) MI(s) ao qual a imagem (pode) pertence(r)"""
    
    done = pyqtSignal()
    primary_label = pyqtSignal(str)
    secondary_label = pyqtSignal(str)
    tertiary_label = pyqtSignal(str)
    primary_total = pyqtSignal(int)
    secondary_total = pyqtSignal(int)
    tertiary_total = pyqtSignal(int)
    primary_progress = pyqtSignal(int)
    secondary_progress = pyqtSignal(int)
    tertiary_progress = pyqtSignal(int)
    primary_progress_pushed = pyqtSignal()
    secondary_progress_pushed = pyqtSignal()
    tertiary_progress_pushed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.EXTENSAO_BRASIL: QgsRectangle = QgsRectangle(
            -8237642.3187022441998124,
            -4028802.0261344080790877,
            -3172605.4876082967966795,
            613199.6633499705931172
        )
        self.wasCanceled = lambda: False
    
    def setCanceled(self, wasCanceled: Callable[[], bool]):
        self.wasCanceled = wasCanceled
    
    def connectProgressDialog(self, p_dlg: ProgressDialog):
        self.primary_label.connect(p_dlg.setPrimaryLabel)
        self.secondary_label.connect(p_dlg.setSecondaryLabel)
        self.tertiary_label.connect(p_dlg.setTertiaryLabel)
        self.primary_total.connect(p_dlg.setPrimaryTotal)
        self.secondary_total.connect(p_dlg.setSecondaryTotal)
        self.tertiary_total.connect(p_dlg.setTertiaryTotal)
        self.primary_progress.connect(p_dlg.setPrimaryProgress)
        self.secondary_progress.connect(p_dlg.setSecondaryProgress)
        self.tertiary_progress.connect(p_dlg.setTertiaryProgress)
        self.primary_progress_pushed.connect(p_dlg.pushPrimaryProgress)
        self.primary_progress_pushed.connect(p_dlg.pushSecondaryProgress)
        self.primary_progress_pushed.connect(p_dlg.pushTertiaryProgress)
        self.wasCanceled = p_dlg.wasCanceled
    
    def calculateImageDiameter(self):
        img = carregarImagem(self.params.image_path)
        shape = img.shape
        width = shape[0]
        height = shape[1]
        return sqrt(pow(width, 2) + pow(height, 2))
    
    def progressCallback(self, curr: int, msg: str):
        self.tertiary_label.emit(msg)
        self.tertiary_progress.emit(curr)
    
    def extentToGeom(self, extent: QgsRectangle):
        geom = QgsGeometry()
        xMin, yMin, xMax, yMax = extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()
        geom.addPointsXYV2([
            QgsPointXY(xMin, yMin),
            QgsPointXY(xMin, yMax),
            QgsPointXY(xMax, yMax),
            QgsPointXY(xMax, yMin),
            QgsPointXY(xMin, yMin)
        ], Qgis.WkbType.Polygon)
        return geom
    
    def cacheSource(self, source: WMSSource, cache_folder: str, extent: QgsRectangle, zoom: int):
        """Essa função deve ser chamada da WORKER THREAD, não chama ela direto do *_dialog.py"""
        self.secondary_label.emit("Setting up WMS Cache Service.")
        wmcs = WebMapCacheService()
        wmcs.message_logged.connect(self.tertiary_label.emit)
        wmcs.progress_started.connect(self.tertiary_total.emit)
        wmcs.progress_pushed.connect(self.tertiary_progress_pushed.emit)
        wmcs.setCanceled(wasCanceled=self.wasCanceled)
        wmcs.setParams(cache_folder, source, extent, zoom)
        self.secondary_label.emit("Cacheing WMS Layer...")
        wmcs.run()
        self.secondary_label.emit("Loading cached layer...")
        fp = os.path.normpath(os.path.realpath(os.path.join(cache_folder, f'{source.source_id}.mbtiles')))
        return QgsRasterLayer(fp, source.alias, "gdal")
    
    def setParams(self, params: MIGuessingParams):
        self.params = params

    def run(self):
        MIN_ZOOM = 8
        MAX_ZOOM = 12
        success = False
        try:
            config = GeoreferencingConfig()
            ext = self.EXTENSAO_BRASIL
            self.primary_total.emit(MAX_ZOOM - MIN_ZOOM + 1)
            
            img_diam = self.calculateImageDiameter()
            new_extents = [ext]
            zooms = (n for n in range(MIN_ZOOM, MAX_ZOOM + 1))

            for z in zooms: # Repetir para cada nível de zoom entre 8 e 12, no 13 dá para georeferenciar já.
                if self.wasCanceled():
                    return False
                extents = new_extents
                new_extents = []
                infinite_loop_guard = 999
                self.primary_label.emit(f"Running @ zoom {z}")
                self.secondary_total.emit(len(extents) * 3)
                while len(extents) > 0:
                    # Guard against infinite loops
                    infinite_loop_guard -= 1
                    if infinite_loop_guard == 0: raise RecursionError("Infinite loop.")
                    # Check canceled
                    if self.wasCanceled():
                        return False
                    # Cut up the region
                    self.secondary_label.emit("Dividing region into subregions...")
                    ext = extents.pop()
                    regions = divideWithMetricSuperposition(
                        bbox=ext,
                        superposition=(img_diam, img_diam),
                        progress_callback=self.progressCallback,
                        config=config
                    )
                    self.secondary_progress_pushed.emit()
                    # Cache the extent
                    if isinstance(self.params.reference, MIGuessingReferenceWMS):
                        ref_layer = self.cacheSource(
                            source=self.params.reference.source,
                            cache_folder=self.params.reference.cache_folder,
                            extent=ext,
                            zoom=z
                        )
                    elif isinstance(self.params.reference, MIGuessingReferenceLayer):
                        ref_layer = self.params.reference.reference_layer
                    else:
                        raise TypeError("params.reference must be of valid type!")
                    self.secondary_progress_pushed.emit()
                    # Check for each region if it's possible that the image is in there
                    self.secondary_label.emit("Checking whether each subregion is possible")
                    is_possible = [isPossibleLocation(
                        self.params.image_path,
                        polygon_geom=self.extentToGeom(ext),
                        reference_layer=ref_layer,
                        progress_callback=self.progressCallback,
                        config=config,
                        wasCanceled=self.wasCanceled
                    )]
                    self.secondary_progress_pushed.emit()
                    # Filter the possible extents
                    self.secondary_label.emit("Filtering possible subregions...")
                    new_extents.extend(regions[i] for i in range(len(regions)) if is_possible[i])
                # while/
                self.primary_progress_pushed.emit()
                extents = new_extents
                if len(extents) == 0:
                    self.primary_label.emit("Could not find any")
                success = True
                return success
            # for/
        except:
            pass
        finally:
            return success