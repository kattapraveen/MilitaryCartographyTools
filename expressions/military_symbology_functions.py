# -*- coding: utf-8 -*-

"""
Military symbology expression functions
for Military Cartography Tools
"""

from qgis.core import QgsExpression, qgsfunction

from ..military_symbology.sidc import build_sidc
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
    own attributes (usually via mct_build_sidc(), below) and the symbol
    drawn for it - see military_symbology/unit_layer.py.
    """

    if len(values) < 1:
        return "Need a SIDC string"

    sidc = str(values[0])

    return render_symbol_base64_path(sidc)


# ============================================================
# SIDC builder from named components
# ============================================================

@qgsfunction(
    'mct_build_sidc',
    group='Military Cartography Tools'
)
def mct_build_sidc(values, feature=None, parent=None):

    """
    Builds a 20-character SIDC from named components (affiliation, entity,
    echelon, status, headquarters) - calls straight into
    military_symbology/sidc.py's build_sidc() rather than re-implementing
    its field-position/code logic here, so that logic lives in exactly one
    place. Lets a unit layer's renderer go straight from a feature's own
    friendly attribute values to a rendered symbol
    (mct_sidc_svg(mct_build_sidc(...))) with no intermediate stored SIDC
    field to keep in sync.
    """

    if len(values) < 5:
        return "Need affiliation, entity, echelon, status, headquarters"

    affiliation, entity, echelon, status, headquarters = values[:5]

    try:

        return build_sidc(
            affiliation=str(affiliation),
            entity=str(entity),
            echelon=str(echelon),
            status=str(status),
            headquarters=bool(headquarters)
        )

    except KeyError as error:

        return str(error)


_FUNCTIONS = [
    mct_sidc_svg,
    mct_build_sidc,
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
