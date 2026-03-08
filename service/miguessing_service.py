# service/mirguessing_service.py
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from math import pow, sqrt
import os
from typing import Callable

from cv2 import DMatch

from qgis.core import QgsMapLayer, QgsGeometry, QgsRectangle, Qgis, QgsPointXY, QgsRasterLayer
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from ..service.webmapcache_service import WebMapCacheService
from ..core.config import GeoreferencingConfig
from ..core.estimators.homography_base import ResultadoHomografia
from ..core.miguessing import carregarImagem, divideWithMetricSuperposition, checkRegion
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
    canceled = pyqtSignal()
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
        self.result = None
    
    def setParams(self, params: MIGuessingParams):
        self.params = params

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
        p_dlg.canceled().connect(self.canceled.emit)

    def start(self):
        self.minz = 10
        self.maxz = 12
        self.curz = self.minz - 1
        self.img_diam = self.__calculateImageDiameter()
        self.config = GeoreferencingConfig()
        self.open_extents: list[QgsRectangle] = [] 
        self.possible_extents = [self.EXTENSAO_BRASIL]
        self.primary_total.emit(self.maxz - self.minz + 1)
        self.__run_next_zoom_level()

    def __run_next_zoom_level(self):
        self.curz += 1
        if self.wasCanceled():
            return False
        self.primary_label.emit(f"Running @ zoom {self.curz}")
        self.open_extents = self.possible_extents
        self.possible_extents = []
        self.secondary_total.emit(len(self.open_extents) * 3)
        self.__start_next_open_extent()
    
    def __start_next_open_extent(self):
        if self.wasCanceled():
            return False
        # Cut up the region
        self.secondary_label.emit("Dividing region into subregions...")
        ext = self.open_extents.pop()
        self.regions = self.__divideExtentInRegions(ext)
        
        self.tertiary_label.emit("")
        self.secondary_progress_pushed.emit()
        # Cache the extent
        if isinstance(self.params.reference, MIGuessingReferenceWMS):
             return self.__cacheSource(
                source=self.params.reference.source,
                cache_folder=self.params.reference.cache_folder,
                extent=ext,
                zoom=self.curz
            )
        elif isinstance(self.params.reference, MIGuessingReferenceLayer):
            self.layer = self.params.reference.reference_layer
            self.__findAndAddPossibleRegions()
            self.secondary_progress_pushed.emit()
            return True
        else:
            raise TypeError("params.reference must be of valid type!")
    
    def __divideExtentInRegions(self, ext):
        regions = divideWithMetricSuperposition(
            bbox=ext,
            superposition=(self.img_diam, self.img_diam),
            progress_callback=self.__progressCallback,
            config=self.config
        )
        return regions
    
    def __cacheSource(
        self, 
        source: WMSSource, 
        cache_folder: str, 
        extent: QgsRectangle, 
        zoom: int
    ):
        """Essa função dá inicio ao processo de cache"""
        self.secondary_label.emit("Setting up WMS Cache Service.")
        self.wmcs = WebMapCacheService()
        self.wmcs.setParams(cache_folder, source, extent, zoom)
        self.wmcs.message.connect(self.tertiary_label.emit)
        self.wmcs.started.connect(self.tertiary_total.emit)
        self.wmcs.progressed.connect(self.tertiary_progress_pushed.emit)
        self.wmcs.done.connect(self.__onCacheDone)
        self.canceled.connect(self.wmcs.cancel)
        self.secondary_label.emit("Cacheing WMS Layer...")
        return self.wmcs.start()
    
    def __onCacheDone(self):
        assert self.wmcs
        self.secondary_label.emit("Loading cached layer...")
        assert isinstance(self.params.reference, MIGuessingReferenceWMS)
        source = self.params.reference.source
        fp = os.path.normpath(os.path.realpath(os.path.join(self.params.reference.cache_folder, f'{source.source_id}.mbtiles')))
        self.layer = QgsRasterLayer(fp, source.alias, "gdal")
        self.__findAndAddPossibleRegions()
    
    def __findAndAddPossibleRegions(self):
        assert self.layer 
        assert self.config
        assert self.params
        # Check for each region if it's possible that the image is in there
        self.secondary_label.emit("Checking whether each subregion is possible")
        self.tertiary_total.emit(100)
        resultados: list[ResultadoHomografia | None] = []
        for reg in self.regions:
            resultados.append(checkRegion(
                self.params.image_path,
                polygon_geom=self.__extentToGeom(reg),
                reference_layer=self.layer,
                zoom=self.curz,
                progress_callback=self.__progressCallback,
                config=self.config,
                wasCanceled=self.wasCanceled
            ))
            self.secondary_progress_pushed.emit()
        # Filter the possible extents
        self.secondary_label.emit("Filtering possible subregions...")
        self.possible_extents.extend(self.regions[i] for i in range(len(self.regions)) if len(resultados) > self.config.min_features)
        with open(f"C:/logsgeoref/preprocessing/possible_extents_{self.curz}.txt", "a") as f:
            for i, ext in enumerate(self.possible_extents):
                r = resultados[i]
                f.write(f"{ext.toString(2)} with {f'inliners=({r.n_inliers}/{r.n_corresp}), thr={r.reproj_thresh}px, conf={r.confidence}' if r else 'NOTHING'}\n")

    def __calculateImageDiameter(self):
        img = carregarImagem(self.params.image_path)
        shape = img.shape
        width = shape[0]
        height = shape[1]
        return sqrt(pow(width, 2) + pow(height, 2))
    
    def __progressCallback(self, curr: int, msg: str):
        self.tertiary_label.emit(msg)
        self.tertiary_progress.emit(curr)
    
    def __extentToGeom(self, extent: QgsRectangle):
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