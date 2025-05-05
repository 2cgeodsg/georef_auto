# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeorefAuto
                                 A QGIS plugin
 Automatic georeferencing of aerial images
                             -------------------
        begin                : 2025-04-26
        copyright            : (C) 2025
        email                : info@example.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
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
