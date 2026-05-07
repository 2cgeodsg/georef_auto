# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeorefAuto_refatore
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

__author__ = 'GeorefAuto_refatore'
__date__ = '2025-04-26'
__copyright__ = '(C) 2025'

# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

def classFactory(iface):
    """Load GeorefAuto_refatore class from file GeorefAuto_refatore.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .main_plugin import GeorefAuto_refatore
    return GeorefAuto_refatore(iface)
