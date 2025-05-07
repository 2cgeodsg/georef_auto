# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeorefAuto
                                 A QGIS plugin
 Automatic georeferencing of aerial images
                             -------------------
        begin                : 2025-04-26
        copyright            : (C) 2025
        email                : dgeo2cgeo2025@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'GeorefAuto'
__date__ = '2025-04-26'
__copyright__ = '(C) 2025'

# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

def classFactory(iface):
    """Load GeorefAuto class from file GeorefAuto.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .georef_auto import GeorefAuto
    return GeorefAuto(iface)
