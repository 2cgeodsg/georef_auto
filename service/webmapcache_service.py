# service/webmapcache_service.py
# -*- coding: utf-8 -*-
from dataclasses import dataclass
import os
from math import floor, pow, pi
import sqlite3
from time import sleep
from typing import Callable, Tuple
import requests
from osgeo import gdal
from qgis.core import QgsRectangle
import base64
from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable, pyqtSlot

from ..sources.wms_sources import WMSSource, WMSSourceThreadsafe, WMSSources


@dataclass(frozen=True)
class TileParams:
    """Parâmetros do tile. Quem, onde, como."""
    tile: tuple[int, int, int]
    tilepath: str
    source: WMSSourceThreadsafe
    requestBuilder: Callable[[str, int, int, int], str]


@dataclass(frozen=True)
class TileResults:
    tile: tuple[int, int, int]
    success: bool


class TileWorkerLogs(list[Tuple[str, int]]): 
    """Essa classe existe por quê e somente por quê o QGIS reclamou do pyqtSignal com genérico."""
    pass


class TileWorkerSignals(QObject):
    """
    QRunnable não suporta pyqtSignal. Sim, isso é intencional. Sim, essa é a forma normal de utilizar isso.
    Foi planejado e feito dessa forma. Reclamações com o povo do PyQt, não comigo.
    """
    result = pyqtSignal(TileResults)
    logs = pyqtSignal(TileParams,TileWorkerLogs)


class TileWorkerContext:
    """
    O propósito dessa classe é garantir que independente do que acontecer, a conexão com o banco vai ser fechada (por
    que se não for pode ser problema pro operador) e que os logs vão ser escritos (por que se não forem eu não tenho
    como saber o que deu errado)
    """
    conn: sqlite3.Connection|None = None
    logs: TileWorkerLogs
    ok: bool = False

    def __init__(self, params: TileParams, signals: TileWorkerSignals):
        self.params = params
        self.logs = TileWorkerLogs()
        self.signals = signals
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.log("Encerrado.", 1)
        self.log(f"- Exc type  : {str(exc_type)}", 1)
        self.log(f"- Exc value : {str(exc_value)}", 1)
        self.log(f"- Traceback : {str(traceback)}", 1)
        try:
            if self.conn:
                self.log("Fechando conexão com MBTiles", 1)
                self.conn.close()
                self.log("- Conexão com MBTiles fechada", 1)
        except:
            self.log("- Falhou ao fechar a conexão MBTiles", 2)
        try:
            self.log("Emitindo resultados", 1)
            self.signals.result.emit(TileResults(tile=self.params.tile, success=self.ok))
            self.log("- Resultados emitidos", 1)
        except:
            self.log("- Falhou em emitir os resultados", 3)
        self.signals.logs.emit(self.params, self.logs)
        return True
    
    def log(self, msg:str, level:int):
        self.logs.append((msg,level))


class TileWorker(QRunnable):
    def __init__(self, params: TileParams):
        super().__init__()
        self.signals = TileWorkerSignals()
        self.params = params
        self.canceled = False

    @pyqtSlot()
    def run(self):
        with TileWorkerContext(self.params, self.signals) as context:
            tile = self.params.tile
            source = self.params.source
            requestBuilder = self.params.requestBuilder
            # Verifica se cancelado
            if self.canceled:
                context.log(f"Cancelado, encerrando.", 1)
                return
            # Se não há template_url, some daqui.
            if not source.template_url:
                context.log(f"Nenhum URL informado, encerrando.", 1)
                return
            
            # Abre conexão com o MBtiles
            context.log("Tentando abrir conexão com MBTiles", 1)
            context.log("- Conexão aberta com sucesso", 1)
            context.conn = sqlite3.connect(self.params.tilepath)
            cursor = context.conn.cursor()
            # Verifica existência
            context.log("Verificando se o tile já existe", 1)
            try:
                query = "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?"
                cursor.execute(query, (tile[0], tile[1], (1 << tile[0]) - 1 - tile[2]))
                # cursor.execute(query, (tile[0], tile[1], tile[2]))
                # Fetch one result. If a row is found, the tile exists.
                result = cursor.fetchone()
                if result is not None:
                    # Já tem o tile
                    context.log("- Tile encontrado, encerrando.", 1)
                    context.ok = True
                    return
            except Exception as e:
                context.log("Não pode ler/escrever no MBTiles", 3)
                return

                
            # Request do tile
            response = None
            url = requestBuilder(source.template_url, tile[0], tile[1], tile[2])
            context.log(f"Fazendo pedido de: {url}", 1)
            # 3 tentativas de baixar o tile
            for _ in range(3):
                if self.canceled:
                    context.log("Cancelado", 1)
                    return
                try:
                    response = requests.get(url, allow_redirects=True)
                except:
                    response = None
                valid = TileWorker.isValidTile(response)
                if valid[0]:
                    context.log(f"- Baixado com sucesso.", 1)
                    break
                response = None
                #logger.warning(f"Tile {tile[0]}/{tile[1]}/{tile[2]} falhou: {valid[1]}. Tentando denovo...")
                context.log(f"- Falhou: {valid[1]}. Tentando denovo...", 2)
            if not response:
                #logger.error(f"Tile {tile[0]}/{tile[1]}/{tile[2]} não pode ser baixado!")
                context.log("- Não pode ser baixado!", 3)
                return
            # Se conseguir, tá aí.
            tile_data = response.content
            # Insere tile
            total_storage_attempts = 3
            for attempt in range(total_storage_attempts):
                if self.canceled:
                    context.log("Cancelado", 1)
                    return
                try:
                    cursor.execute(
                        "INSERT INTO tiles (zoom_level, tile_column, tile_row, tile_data) VALUES (?, ?, ?, ?)",
                        (tile[0], tile[1], (1 << tile[0]) - 1 - tile[2], sqlite3.Binary(tile_data)) # y do TMS não ZYX
                        # (tile[0], tile[1], tile[2], sqlite3.Binary(tile_data))
                    )
                    context.conn.commit()
                    context.ok = True
                    context.log("Tile armazenado no MBTiles.", 1)
                    break
                except Exception as e:
                    context.log(f"- {attempt+1}/{total_storage_attempts} Erro ao armazenar: {e}.", 3)
            return
    
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




class WebMapCacheService(QObject): 
    """
    Serviço de alto nível para download e cache de WMS.
    
    Uso:
    ```python
        # Cria uma thread (se for o caso)
        self.thread = QThread()
        # Instancia
        self.wmcs = WebMapCacheService() 
        # Manda para thread
        self.wmcs.moveToThread(self.thread)
        # Definir os parâmetros
        # Pasta do cache é um caminho, Fonte é uma WMSSource (ver WMSSources)
        # Bounding box é um QgsRectangle, Zoom é um int geralmente entre 0 e 20
        self.wmcs.setParams(<pasta_do_cache>, <fonte>, <bounding_box>, <zoom> [, caminho_pro_log])
        # Conecta os sinais se for o caso
        # message é para emitir mensagens (p/ progresso com msgs) (opcional)
        self.wmcs.message.connect(self.tertiary_label.emit)
        # started é para o total (p/ barra de progresso tbm) (opcional)
        self.wmcs.started.connect(self.tertiary_total.emit)
        # progressed é para barra de progresso tbm (aumenta o progresso em 1) (opcional)
        self.wmcs.progressed.connect(self.tertiary_progress_pushed.emit)
        # done é para chamar essa função na thread que você está agora quando terminar. 
        # (necessário se não for fire and forget)
        self.wmcs.done.connect(self.onCacheDone)
        # Por fim, dá início ao processo
        self.thread.started.connect(self.wmcs.start)
        self.thread.start()
        # A esse ponto o processo inicia em outra thread
        # vai chamar a função passada ao self.wmcs.done quando terminar
    ```

    Slots:
        `start` : Inicia os processamentos
        `cancel` : Chamado para cancelar o processamento e sair com segurança, escrevendo logs, liberando threads e etc.

    Observações:
        É obrigatório mover o QObject (Essa classe herda dele) para a QThread ANTES de conectar os sinais

    """
    message = pyqtSignal(str, int)
    progressed = pyqtSignal()
    started = pyqtSignal(int)
    done = pyqtSignal()

    max_simultaneous_requests = 8
    mbtiles_driver = gdal.GetDriverByName("MBTiles")
    source = WMSSource(WMSSources.list_sources()[0])
    __mbtiles_cache_path = os.path.realpath("../cache")
    
    def __init__(self) -> None:
        super().__init__()
        self.threadpool: QThreadPool|None = None
        self.results: list[TileResults] = []
        self.active_workers: list[TileWorker] = []
        self.canceled = False
        self.busy = False
    
    def getMBTilesPath(self):
        return os.path.realpath(os.path.join(self.__mbtiles_cache_path, f"{self.source.source_id}.mbtiles"))
    
    def setParams(self, mbtiles_realpath, source: WMSSource, bounding_box: QgsRectangle, zoom_level: int, log_path: str|None = None):
        self.__mbtiles_cache_path = mbtiles_realpath
        self.source = source
        self.bbox = bounding_box
        self.z = zoom_level
        self.log_path = log_path

    @pyqtSlot()
    def start(self):
        """Dá inicio a execução dos processos, retorna True se teve sucesos e False caso contrário"""
        # Isso aqui não é para proteger o Service de threads é pra proteger o Service dele mesmo.
        # O abaixo não impede condições de corrida
        if self.busy: return False
        self.busy = True
        if not self.__setup_processes():
            return False
        self.__start_processes()
        return True
    
    @pyqtSlot()
    def cancel(self):
        self.canceled = True
        if not self.threadpool: return
        self.threadpool.clear()
        if not self.active_workers: return
        for worker in self.active_workers:
            if not worker: continue
            worker.canceled = True
    

    def __setup_processes(self):
        # Calcula os tiles necessários
        self.message.emit(f"Calculando cobertura para {self.bbox.xMinimum()} {self.bbox.yMinimum()} ; {self.bbox.xMaximum()} {self.bbox.yMaximum()}", 1)
        minX, minY, maxX, maxY = WebMapCacheService.calculateTileCoverage(self.bbox, self.z)
        self.message.emit(f"- Calculado: {self.z}/[{minX}, {maxX}]/[{minY}, {maxY}].", 1)
        self.tiles = [(self.z,x,y) for x in range(minX, maxX+1) for y in range(minY, maxY+1)]
        self.total = len(self.tiles)
        # Cria o cache se não existir
        self.message.emit("Verificando existencia do arquivo de cache.", 1)
        if self.mbtiles_driver is None:
            self.message.emit("Driver de MBTiles indisponível. Garanta que o GDAL foi buildado com suporte SQLite.", 3)
            return False
        if not os.path.exists(self.getMBTilesPath()):
            self.message.emit("Arquivo de cache não encontrado. Criando um...", 1)
            if not self.createMBTilesSkeleton(self.source.alias, f"cache of {self.source}", self.getMBTilesPath()):
                self.message.emit(f"- Não pode criar MBTiles em {self.getMBTilesPath()}", 3)
                return False
            self.message.emit("- Criado com sucesso.", 1)
        # Prepara threadpool
        self.message.emit("Criando threadpool.", 1)
        self.threadpool = QThreadPool()
        if self.threadpool: 
            self.message.emit("- Limitando requests simultâneos.", 1)
            self.threadpool.setMaxThreadCount(self.max_simultaneous_requests)
        else:
            self.message.emit("- Falhou ao criar threadpool.", 3)
        # Prepara os logs
        if self.log_path:
            header_lines = []
            header_lines.append("============ WEBMAPCACHE SERVICE LOGS ============")
            header_lines.append(f"BOUNDING BOX : {self.bbox.toString(6)}")
            header_lines.append(f"TILE RANGE : {self.z} | {minX} to {maxX} | {minY} to {maxY}")
            header_lines.append(f"CACHE PATH : {self.getMBTilesPath()}")
            header_lines.append("SOURCE : ")
            for l in self.source.toStrings():
                header_lines.append(f"        {l}")
            header_lines.append("=================== TILE LOGS ===================")
            header_lines.append("")
            self.__write_log(header_lines)
        return True
    

    def __start_processes(self):
        self.active_workers.clear()
        self.results.clear()
        assert self.threadpool
        self.message.emit("Preenchendo tiles paralelamente.", 1)
        if self.canceled:
            return
        # Lista de parâmetros
        self.started.emit(self.total)
        self.message.emit("--Construindo lista de parâmetros.", 1)
        try:
            list_of_params = [TileParams(
                tile=t, 
                tilepath=self.getMBTilesPath(),
                source=WMSSourceThreadsafe(self.source),
                requestBuilder=self.buildRequestUrl
            ) for t in self.tiles]
        except Exception as e:
            self.message.emit(f"{e}", 3)
            return
        # Cria workers e inicia
        idx = 0
        for params in list_of_params:
            if self.canceled:
                return
            idx+=1
            self.message.emit(f"- Delegando tarefas a worker threads... ({idx}/{len(list_of_params)})", 1)
            worker = TileWorker(params=params)
            worker.signals.result.connect(self.__gather_results)
            worker.signals.logs.connect(self.__write_tile_logs)
            self.active_workers.append(worker)
            self.threadpool.start(worker)
        self.message.emit("- Tarefas delegadas", 1)
    
    def __check_results(self):
        self.message.emit("Verificando que todos os tiles baixaram.", 1)
        todos_ok = all([r.success for r in self.results])
        if not todos_ok:
            nao_ok = [r.tile for r in self.results if not r.success]
            self.message.emit(f"Há {len(nao_ok)} tiles que falharam. Tentando novamente.", 1)
            self.__start_processes()
            return
        self.message.emit("Cache do WMS concluído com êxito.", 1)
        self.threadpool = None
        self.busy = False
        self.done.emit()

    @pyqtSlot(TileResults)
    def __gather_results(self, result: TileResults):
        if self.results is None: return
        self.results.append(result)
        self.progressed.emit()
        if len(self.results) == self.total:
            self.__check_results()
    
    @pyqtSlot(TileParams, TileWorkerLogs)
    def __write_tile_logs(self, params: TileParams, logs: TileWorkerLogs):
        self.__write_log([f"TILE : {params.tile}"] + [f"{        l[0]}" for l in logs])
    
    def __write_log(self, log: list[str]):
        if not self.log_path: return
        with open(self.log_path, "a") as f:
            for l in log:
                f.write(l)
                f.write("\n") # If lines skipping, remove

    @staticmethod
    def createMBTilesSkeleton(name, description, filepath):
        """Creates the basic structure and metadata for an MBTiles file using GDAL."""
        # GDAL will create the file and the necessary tables/metadata
        driver = gdal.GetDriverByName("MBTiles")
        # Using 'w' mode for creation/overwrite
        ds = driver.Create(
            filepath, 
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
    
    @staticmethod
    def degToRad(deg: float): return deg * pi / 180

    @staticmethod
    def metersEastToTileX(m: float, z: int): return floor(pow(2, z-1) * (1 + m / 20037508))
    
    @staticmethod
    def metersSouthToTileY(m: float, z: int): return floor(pow(2, z-1) * (1 - m / 20037508)) # TMS inverts the Y axis...

    @staticmethod
    def calculateTileCoverage(boundingBox: QgsRectangle, zoom_level: int):
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