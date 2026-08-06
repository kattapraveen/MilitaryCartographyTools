# -*- coding: utf-8 -*-

"""
Military symbology expression functions
for Military Cartography Tools
"""

from qgis.core import QgsExpression, qgsfunction

from ..military_symbology.symbol_engine import render_symbol_base64_path


# ============================================================
# SIDC-to-symbol renderer
# ============================================================

@qgsfunction(
    'mct_sidc_svg',
    group='Military Cartography Tools'
)
def mct_sidc_svg(values, feature=None, parent=None):

    """
    Renders a MIL-STD-2525/APP-6 symbol for a SIDC string, returning a
    "base64:<...>" path a QgsSvgMarkerSymbolLayer's own data-defined path
    property can use directly. Used as the one link between a feature's
    own attributes (via a "sidc" field, or an expression that builds one)
    and the symbol drawn for it - see military_symbology/unit_layer.py.
    """

    if len(values) < 1:
        return "Need a SIDC string"

    sidc = str(values[0])

    return render_symbol_base64_path(sidc)


_FUNCTIONS = [
    mct_sidc_svg,
]


def register():

    for function in _FUNCTIONS:

        QgsExpression.registerFunction(
            function
        )


def unregister():

    for function in _FUNCTIONS:

        QgsExpression.unregisterFunction(
            function.name()
        )
