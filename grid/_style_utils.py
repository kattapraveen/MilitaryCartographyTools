# -*- coding: utf-8 -*-

"""
Shared styling helper for the grid generator classes.

UTMGridGenerator and MGRS100KGenerator both style their (simple,
single-symbol) polygon layer identically - transparent fill, a
solid outline, differing only in outline width - so that one
pattern is factored out here. MGRSSubGridGenerator's own styling
is a genuinely different, multi-tier rule-based renderer (see its
own apply_style()), not a variant of this one, so it isn't
included here.

Military Cartography Tools
"""

from qgis.core import QgsFillSymbol


def apply_simple_fill_style(layer, outline_width, color="transparent", outline_color="black"):

    """
    Transparent-fill, solid-outline styling for a simple polygon
    grid layer (UTM GZD squares, MGRS 100km squares).
    """

    symbol = QgsFillSymbol.createSimple(
        {
            "color": color,
            "outline_color": outline_color,
            "outline_width": outline_width
        }
    )

    layer.renderer().setSymbol(
        symbol
    )

    layer.triggerRepaint()
