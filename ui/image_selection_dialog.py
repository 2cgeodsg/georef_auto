from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QDialogButtonBox

class SelecaoImagensDialog(QDialog):
    def __init__(self, lista_imagens, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar imagens para o mosaico")
        self.setMinimumSize(400, 300)

        self.layout = QVBoxLayout(self)

        self.listaWidget = QListWidget()
        self.listaWidget.setSelectionMode(QListWidget.MultiSelection)
        for caminho in lista_imagens:
            item = QListWidgetItem(caminho)
            self.listaWidget.addItem(item)

        self.layout.addWidget(self.listaWidget)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def obter_imagens_selecionadas(self):
        return [item.text() for item in self.listaWidget.selectedItems()]