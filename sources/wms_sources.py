import os
import configparser
from typing import ClassVar
from PyQt5.QtGui import QIcon

from ..utils import logger

class WMSSources:
    __WMS_DIR : ClassVar[str] = os.path.realpath(os.path.join(__file__, "../wms_metadata"))

    @classmethod
    def list_sources(cls):
        return [name for name in os.listdir(cls.__WMS_DIR) if os.path.isdir(os.path.join(cls.__WMS_DIR, name))]
    
    @classmethod
    def get_wms_dir(cls):
        return cls.__WMS_DIR
    
    @classmethod
    def get_source_metadata(cls, source_id: str):
        try:
            __configparser = configparser.ConfigParser()
            src_path = os.path.join(cls.__WMS_DIR, source_id)
            ok = __configparser.read(os.path.join(src_path, "metadata.ini"))
            if len(ok) == 0:
                logger.logger.error("Falhou em ler as configurações de fonte de WMS: %s", source_id)
                return "", None
            return src_path, __configparser
        except configparser.Error:
            logger.logger.error("Falhou em ler as configurações de fonte de WMS: %s", source_id)
        return "", None


class WMSSource:
    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self.source_path, self.metadata = WMSSources.get_source_metadata(source_id)
        if not self.metadata:
            return
        self.alias = self.metadata.get("ui", "alias", fallback=None)
        self.icon_filename = self.metadata.get("ui", "icon")
        self.icon = QIcon(os.path.join(self.source_path, self.icon_filename)) if self.icon_filename else None
        self.template_url = self.metadata.get("tms", "url", fallback=None)
        if not self.template_url: # No url -> invalid source.
            self.metadata = None
            return
        self.min_zoom = self.metadata.get("tms", "zmin", fallback=0)
        self.max_zoom = self.metadata.get("tms", "zmax", fallback=20)

class WMSSourceThreadsafe:
    def __init__(self, source: WMSSource) -> None:
        self.source_id = source.source_id
        self.source_path = source.source_path
        self.alias = source.alias
        self.icon_filename = source.icon_filename
        self.template_url = source.template_url
        self.min_zoom = source.min_zoom
        self.max_zoom = source.max_zoom