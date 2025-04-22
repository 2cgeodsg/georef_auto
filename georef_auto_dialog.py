from qgis.gui import QgsMapToolCapture
from PyQt5.QtCore import Qt
from .maptool_poligono import MapToolPoligono
from qgis.core import QgsProject, QgsRasterLayer, QgsGeometry
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from .georef_auto_dialog_base import Ui_GeorefAutoDialog

class GeorefAutoDialog(QDialog, Ui_GeorefAutoDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface  # Agora 'iface' está disponível

        # Conectando os botões às funções
        self.btnCarregarImagem.clicked.connect(self.carregar_imagem)
        self.btnDesenharPoligono.clicked.connect(self.desenhar_poligono)
        self.btnGeorreferenciar.clicked.connect(self.executar_georreferenciamento)
        self.btnCancelar.clicked.connect(self.close)

        self.caminho_imagem = None
        self.caminho_poligono = None  # Aqui armazenamos a geometria do polígono
        self.layer_referencia = None
        self.layers_disponiveis = []

        self.carregar_layers()
        self.comboLayerReferencia.currentIndexChanged.connect(self.definir_layer_referencia)

    def carregar_imagem(self):
        arquivo, _ = QFileDialog.getOpenFileName(
            self, "Selecione a imagem aérea", "", "Imagens (*.tif *.jpg *.png)"
        )
        if arquivo:
            self.caminho_imagem = arquivo
            print(f"Imagem carregada: {arquivo}")

    def desenhar_poligono(self):
        if not self.layer_referencia:
            QMessageBox.warning(self, "Erro", "Você deve selecionar uma camada de referência antes.")
            return

        self.hide()  # Minimiza a janela do plugin

        canvas = self.iface.mapCanvas()
        crs_referencia = self.layer_referencia.crs()

        self.tool_poligono = MapToolPoligono(canvas, crs_referencia)
        self.tool_poligono.poligono_finalizado.connect(self.finalizar_poligono)
        canvas.setMapTool(self.tool_poligono)

    def finalizar_poligono(self, geometria):
        print("Sinal recebido no dialog.")
        self.caminho_poligono = geometria
        print("Polígono desenhado com sucesso.")
        self.iface.mapCanvas().unsetMapTool(self.tool_poligono)  # Importante!
        self.show()
        self.activateWindow()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

    def carregar_layers(self):
        """Preenche a combobox com as camadas raster abertas no QGIS."""
        self.comboLayerReferencia.clear()
        self.comboLayerReferencia.addItem("Selecionar imagem de referência")
        self.layers_disponiveis = []

        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsRasterLayer):
                self.comboLayerReferencia.addItem(layer.name())
                self.layers_disponiveis.append(layer)

    def definir_layer_referencia(self, index):
        if index == 0:
            self.layer_referencia = None
            print("Nenhuma camada selecionada.")
        elif 1 <= index <= len(self.layers_disponiveis):
            self.layer_referencia = self.layers_disponiveis[index - 1]
            print(f"Layer de referência selecionada: {self.layer_referencia.name()}")
            print(f"Layer de referência selecionada: {self.layer_referencia.name()}")
        else:
            self.layer_referencia = None

    def executar_georreferenciamento(self):
        from .georreferenciar import georreferenciar
        from qgis.PyQt.QtWidgets import QFileDialog

        if not self.caminho_imagem:
            QMessageBox.warning(self, "Erro", "Você deve carregar a imagem antes.")
            return

        if not self.caminho_poligono:
            QMessageBox.warning(self, "Erro", "Você deve desenhar o polígono primeiro.")
            return

        if not self.layer_referencia:
            QMessageBox.warning(self, "Erro", "Você deve selecionar uma camada de referência.")
            return

        caminho_saida, _ = QFileDialog.getSaveFileName(
            self, "Salvar imagem georreferenciada", "", "GeoTIFF (*.tif)"
        )
        if not caminho_saida:
            return

        georreferenciar(
            imagem_nao_geo_path=self.caminho_imagem,
            poligono_geom=self.caminho_poligono,
            layer_referencia=self.layer_referencia,
            saida_path=caminho_saida
        )