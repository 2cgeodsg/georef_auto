from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .georef_auto_dialog import GeorefAutoDialog
import os

class GeorefAuto:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None

    def initGui(self):
        """Inicializa o ícone e adiciona o plugin ao menu e à barra de ferramentas do QGIS."""
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        
        self.action = QAction(icon, "Georreferenciamento Automático", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        
        self.iface.addPluginToMenu("Georreferenciamento Automático", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        """Remove o plugin do menu e da barra de ferramentas ao ser desativado."""
        self.iface.removePluginMenu("Georreferenciamento Automático", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        if not hasattr(self, "dialog") or self.dialog is None:
            self.dialog = GeorefAutoDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()