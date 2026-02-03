# service/webmapcache_service.py
# -*- coding: utf-8 -*-
from dataclasses import dataclass
import os
from math import floor, pow, pi
import sqlite3
import threading
from typing import Callable
import requests
from osgeo import gdal
from qgis.core import QgsRectangle
import base64
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal
import asyncio

from ..sources.wms_sources import WMSSource, WMSSourceThreadsafe, WMSSources


class WebMapCacheService(QObject):
    """
    Serviço de alto nível para download e cache de WMS.
    
    Uso:
    ```python
    wmcs = WebMapCacheService() # Instancia
    wmcs.setMBTilesPath(filepath) # Determina onde o .mbtiles vai ser armazenado
    wmcs.setReference(source) # Determina qual das camadas definidas em WMSSources é usada como referência
    wmcs.ensureCache(extent, res_espacial) # Constrói persistentemente o cache da camada (tenta muitas vezes)
    ```
    """
    

    max_simultaneous_requests = 8
    mbtiles_driver = gdal.GetDriverByName("MBTiles")
    source = WMSSource(WMSSources.list_sources()[0])
    __mbtiles_cache_path = os.path.realpath("../cache")
    message_logged = pyqtSignal(str, int)
    progress_pushed = pyqtSignal()
    progress_started = pyqtSignal(int)
    done = pyqtSignal()
    
    def __init__(self) -> None:
        super().__init__()
        self.wasCanceled = lambda: False
    
    def getMBTilesPath(self):
        return os.path.realpath(os.path.join(self.__mbtiles_cache_path, f"{self.source.source_id}.mbtiles"))
    
    def setParams(self, mbtiles_realpath, source: WMSSource, bounding_box: QgsRectangle, zoom_level: int):
        self.__mbtiles_cache_path = mbtiles_realpath
        self.source = source
        self.bbox = bounding_box
        self.z = zoom_level
    
    def setCanceled(self, wasCanceled: Callable[[], bool]):
        self.wasCanceled = wasCanceled

    @staticmethod
    def degToRad(deg: float): return deg * pi / 180

    @staticmethod
    def metersEastToTileX(m: float, z: int): return floor(pow(2, z-1) * (1 + m / 20037508))
    
    @staticmethod
    def metersSouthToTileY(m: float, z: int): return floor(pow(2, z-1) * (1 - m / 20037508)) # TMS inverts the Y axis...


    def calculateTileCoverage(self, boundingBox: QgsRectangle, zoom_level: int):
        """
        Calcula quais tiles precisam ser obtidos para cobrir totalmente a bounding box desejada
        no zoom desejado.

        Retorna ( X mínimo , Y mínimo , X máximo , Y máximo )
        """

        minX = WebMapCacheService.metersEastToTileX(boundingBox.xMinimum(), zoom_level)
        maxX = WebMapCacheService.metersEastToTileX(boundingBox.xMaximum(), zoom_level)
        maxY = WebMapCacheService.metersSouthToTileY(boundingBox.yMinimum(), zoom_level)
        minY = WebMapCacheService.metersSouthToTileY(boundingBox.yMaximum(), zoom_level)

        return (minX, minY, maxX, maxY)
    
    @staticmethod
    def queryFromZYX(z:int,y:int,x:int):
        q = ""
        center_x = pow(2, z-1)
        center_y = pow(2, z-1)
        for k in range(z-1, -1, -1):
            quarter = pow(2, k-1)
            rightside = x >= center_x
            bottomside = y >= center_y
            q = f"{q}{(1 if rightside else 0) + (2 if bottomside else 0)}"
            center_x += quarter if rightside else -quarter
            center_y += quarter if bottomside else -quarter
        return q
    
    @staticmethod
    def buildRequestUrl(templateUrl: str, Z: int, X: int, Y: int):
        return templateUrl.format(z=Z, x=X, y=Y, q=WebMapCacheService.queryFromZYX(Z,Y,X))

    def run(self):
        # Calcula os tiles necessários
        self.message_logged.emit(f"Calculando cobertura para {self.bbox.xMinimum()} {self.bbox.yMinimum()} ; {self.bbox.xMaximum()} {self.bbox.yMaximum()}", 1)
        minX, minY, maxX, maxY = self.calculateTileCoverage(self.bbox, self.z)
        
        self.message_logged.emit(f"--Calculado: {self.z}/[{minX}, {maxX}]/[{minY}, {maxY}].", 1)
        tiles = [(self.z,x,y) for x in range(minX, maxX+1) for y in range(minY, maxY+1)]
        total = len(tiles)

        # Cria o cache se não existir
        self.message_logged.emit("Verificando existencia do arquivo de cache.", 1)
        if self.mbtiles_driver is None:
            self.message_logged.emit("Driver de MBTiles indisponível. Garanta que o GDAL foi buildado com suporte SQLite.", 3)
            self.done.emit()
            return
        if not os.path.exists(self.getMBTilesPath()):
            self.message_logged.emit("Arquivo de cache não encontrado. Criando um...", 1)
            if not self.createMBTilesSkeleton(self.source.alias, f"cache of {self.source}"):
                self.message_logged.emit(f"--Não pode criar MBTiles em {self.getMBTilesPath()}", 3)
                self.done.emit()
                return
            self.message_logged.emit("--Criado com sucesso.", 1)
    
        # Prepara para preencher o cache
        self.message_logged.emit("Preparando para preencher o cache.", 1)
        todos_tiles_prontos = False
        event_loop = asyncio.new_event_loop()
        def start_loop(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()
        t = threading.Thread(target=start_loop, args=(event_loop,), daemon=True)
        t.start()

        # Preenche
        self.message_logged.emit("Preenchendo tiles paralelamente.", 1)
        while not todos_tiles_prontos:
            self.progress_started.emit(total)
            params = [WebMapCacheService.TileParams(
                tile=t, 
                tilepath=self.getMBTilesPath(),
                source=WMSSourceThreadsafe(self.source),
                requestBuilder=self.buildRequestUrl,
                tileChecker=self.isValidTile
            ) for t in tiles]
            
            futuros_resultados = asyncio.run_coroutine_threadsafe(
                WebMapCacheService.ensureTilesInParallel(
                    params, 
                    self.max_simultaneous_requests, 
                    self.wasCanceled,
                    self.message_logged.emit, 
                    self.progress_pushed.emit
                ), 
                event_loop
            )
            #logger.info("Verificando que todos os tiles baixaram.")
            while not futuros_resultados.done():
                pass
            resultados = futuros_resultados.result()
            if self.wasCanceled():
                break
            self.message_logged.emit("Verificando que todos os tiles baixaram.", 1)
            todos_tiles_prontos = all(resultados)
            if not todos_tiles_prontos:
                self.message_logged.emit(f"Há {resultados.count(False)} tiles que falharam. Tentando novamente.", 1)
        self.message_logged.emit("Cache do WMS concluído com êxito.", 1)
        self.done.emit()
        return
    
    @dataclass
    class TileParams:
        tile: tuple[int, int, int]
        tilepath: str
        source: WMSSourceThreadsafe
        requestBuilder: Callable[[str, int, int, int], str]
        tileChecker: Callable[[requests.Response|None], tuple[bool, str]]

    @staticmethod
    async def ensureTilesInParallel(
        paramList: list[TileParams], 
        request_max_rate: int, 
        wasCanceled: Callable[[],bool],
        pushLog: Callable[[str,int],None], 
        pushProgress: Callable[[],None]
    ):
        req_sem = asyncio.Semaphore(request_max_rate)
        tasks = [asyncio.create_task(WebMapCacheService.ensureTile(p, req_sem, wasCanceled, pushLog, pushProgress)) for p in paramList]
        result = await asyncio.gather(*tasks)
        return result

    @staticmethod
    async def ensureTile(
        params: TileParams, 
        request_semaphore, 
        wasCanceled: Callable[[],bool],
        pushLog: Callable[[str,int],None], 
        pushProgress: Callable[[],None]
    ) -> bool:
        tile = params.tile
        if wasCanceled():
            pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} cancelado", 1)
            return False
        tilepath = params.tilepath
        source = params.source
        requestBuilder = params.requestBuilder
        tileChecker = params.tileChecker
        # Abre conexão com o MBtiles e preprara a saida
        conn = sqlite3.connect(tilepath)
        cursor = conn.cursor()
        def _exit(t: bool):
            pushProgress()
            conn.close()
            return t
        # Se não há template_url, some daqui.
        if not source.template_url:
            return _exit(False)

        try:
            query = "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?"
            cursor.execute(query, (tile[0], tile[1], (1 << tile[0]) - 1 - tile[2]))
            # cursor.execute(query, (tile[0], tile[1], tile[2]))
            # Fetch one result. If a row is found, the tile exists.
            result = cursor.fetchone()
            if result is not None:
                # Já tem o tile
                return _exit(True)
        except Exception as e:
            pushLog("--Não pode ler/escrever no MBTiles", 3)
            return _exit(False)

        
        # Request do tile
        # QApplication.processEvents()
        response = None
        # 3 tentativas de baixar o tile
        url = requestBuilder(source.template_url, tile[0], tile[1], tile[2])
        pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} sendo pedido de: {url}", 1)
        async with request_semaphore:
            for _ in range(3):
                if wasCanceled():
                    pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} download cancelado", 1)
                    return _exit(False)
                # QApplication.processEvents()
                try:
                    response = requests.get(url, allow_redirects=True)
                except:
                    response = None
                valid = tileChecker(response)
                if valid[0]:
                    #logger.info(f"Tile {tile[0]}/{tile[1]}/{tile[2]} baixado com sucesso.")
                    pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} baixado com sucesso.", 1)
                    break
                response = None
                #logger.warning(f"Tile {tile[0]}/{tile[1]}/{tile[2]} falhou: {valid[1]}. Tentando denovo...")
                pushLog(f"----Tile {tile[0]}/{tile[1]}/{tile[2]} falhou: {valid[1]}. Tentando denovo...", 2)
        if not response:
            #logger.error(f"Tile {tile[0]}/{tile[1]}/{tile[2]} não pode ser baixado!")
            pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} não pode ser baixado!", 3)
            return _exit(False)
        # Se conseguir, tá aí.
        tile_data = response.content
        tile_inserted = False
        # Insere tile
        # QApplication.processEvents()
        for _ in range(3):
            if wasCanceled():
                pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} escrita cancelada", 1)
                return _exit(False)
            try:
                cursor.execute(
                    "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?, ?, ?, ?)",
                    (tile[0], tile[1], (1 << tile[0]) - 1 - tile[2], sqlite3.Binary(tile_data)) # y do TMS não ZYX
                    # (tile[0], tile[1], tile[2], sqlite3.Binary(tile_data))
                )
                conn.commit()
                tile_inserted = True
            except sqlite3.Error as e:
                #logger.exception(e)
                pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} não pode ser armazenado! {e}.", 3)
            except Exception as e:
                pushLog(f"--Tile {tile[0]}/{tile[1]}/{tile[2]} gerou um erro ao inserir: {e}.", 3)
            if tile_inserted:
                #logger.info(f"Tile {tile[0]}/{tile[1]}/{tile[2]} armazenado no MBTiles.")
                pushLog(f"Tile {tile[0]}/{tile[1]}/{tile[2]} armazenado no MBTiles.", 1)
                break
            # QApplication.processEvents()
        return _exit(tile_inserted)
    
    @staticmethod
    def isValidTile(response: requests.Response|None) -> tuple[bool, str]:
        if not response: return False, "Sem resposta"
        if response.status_code != 200: return False, "Request não OK"
        if not response.headers["content-type"].startswith("image"): return False, "Não imagem"
        if not isinstance(response.content, bytes): return False, "Vazio"
        try:
            isXml = base64.b64decode(response.content).decode().startswith("<xml")
            if isXml: return False, "XML disfarçado de imagem"
        except:
            return True, ""
        return True, ""
    
    def createMBTilesSkeleton(self, name, description):
        """Creates the basic structure and metadata for an MBTiles file using GDAL."""
        mbtiles_path = self.getMBTilesPath()
        # GDAL will create the file and the necessary tables/metadata
        driver = gdal.GetDriverByName("MBTiles")
        # Using 'w' mode for creation/overwrite
        ds = driver.Create(
            mbtiles_path, 
            256, 256, 3, 
            gdal.GDT_Byte, 
            options=[
                'NAME=' + name, 
                'DESCRIPTION=' + description,
                'TILE_FORMAT=JPEG',
                'QUALITY=100',
            ]
        )
        if ds is None:
            return False
        # Flush and close to ensure metadata is written
        ds = None 
        return True