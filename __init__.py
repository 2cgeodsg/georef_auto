# -*- coding: utf-8 -*-
"""
Arquivo de inicialização do plugin Georreferenciamento Automático.
"""

from .georef_auto import GeorefAuto

def classFactory(iface):
    """
    Cria e retorna uma instância do plugin.

    :param iface: Interface do QGIS fornecida no carregamento do plugin.
    :type iface: QgisInterface
    """
    return GeorefAuto(iface)
