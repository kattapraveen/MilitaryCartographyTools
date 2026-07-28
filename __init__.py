# -*- coding: utf-8 -*-
"""
Military Cartography Tools

QGIS plugin entry point.
"""

from .plugin import MilitaryCartographyTools


def classFactory(iface):
    """
    Load MilitaryCartographyTools.

    Parameters
    ----------
    iface : QgisInterface
        A QGIS interface instance.

    Returns
    -------
    MilitaryCartographyTools
        Plugin instance.
    """
    return MilitaryCartographyTools(iface)