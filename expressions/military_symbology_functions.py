# -*- coding: utf-8 -*-

"""
Military symbology expression functions
for Military Cartography Tools
"""

from qgis.core import QgsDistanceArea, QgsExpression, QgsProject, qgsfunction

from ..military_symbology.sidc import build_sidc
from ..military_symbology.symbol_engine import render_symbol_base64_path


def _distance_area():

    """
    A QgsDistanceArea set up for geodesic (ellipsoid-surface)
    measurement in the current project's own CRS - matches
    core/coordinate_utils.py's true_bearing_and_distance() convention
    exactly, rather than a flat-plane calculation that would silently
    return nonsense (square degrees) for a layer in a geographic CRS
    like the AO/NAI area layers this plugin creates by default.

    Deliberately uses QgsProject.instance().crs() rather than taking a
    layer argument (e.g. via an @layer expression variable) - @layer is
    only populated when the calling UI explicitly builds its expression
    context with a layer scope, and that turned out NOT to be true of
    every QGIS expression entry point (confirmed live: QGIS's
    in-place/attribute-table field calculator toolbar evaluates
    mct_area_km2($geometry, @layer) with @layer unresolved, silently
    producing NULL - shown as "nan" in that widget's numeric preview -
    even though $geometry itself resolves fine). QgsProject.instance()
    is a plain Python singleton, always available regardless of which
    UI built the expression context, so this sidesteps that class of
    failure entirely. Correct for every layer this plugin itself
    creates (military_symbology/control_measures.py and unit_layer.py
    both build their layers in the project's own CRS) - would be wrong
    only if a layer were later reprojected independently of the
    project, an edge case not worth the fragility of the @layer
    alternative.
    """

    distance_area = QgsDistanceArea()

    distance_area.setEllipsoid(
        "WGS84"
    )

    distance_area.setSourceCrs(
        QgsProject.instance().crs(),
        QgsProject.instance().transformContext()
    )

    return distance_area


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
    symbol_set, echelon, status, headquarters, and optionally
    sector1_modifier, sector2_modifier) - calls straight into
    military_symbology/sidc.py's build_sidc() rather than re-implementing
    its field-position/code logic here, so that logic lives in exactly one
    place. Lets a unit layer's renderer go straight from a feature's own
    friendly attribute values to a rendered symbol
    (mct_sidc_svg(mct_build_sidc(...))) with no intermediate stored SIDC
    field to keep in sync. The two modifier arguments are optional (a
    6-argument call still works, e.g. mine_warfare's own expression,
    which has no sector modifier fields at all) - omitted or empty/falsy
    means "no modifier", matching build_sidc()'s own default.
    """

    if len(values) < 6:
        return (
            "Need affiliation, entity, symbol_set, echelon, status, "
            "headquarters"
        )

    affiliation, entity, symbol_set, echelon, status, headquarters = values[:6]
    sector1_modifier = values[6] if len(values) > 6 else None
    sector2_modifier = values[7] if len(values) > 7 else None

    try:

        return build_sidc(
            affiliation=str(affiliation),
            entity=str(entity),
            symbol_set=str(symbol_set),
            echelon=str(echelon),
            status=str(status),
            headquarters=bool(headquarters),
            sector1_modifier=str(sector1_modifier) if sector1_modifier else None,
            sector2_modifier=str(sector2_modifier) if sector2_modifier else None,
        )

    except KeyError as error:

        return str(error)


# ============================================================
# AO/NAI area & perimeter reporting
# ============================================================

@qgsfunction(
    'mct_area_km2',
    group='Military Cartography Tools'
)
def mct_area_km2(values, feature=None, parent=None):

    """
    A polygon's own geodesic area in square kilometres - the standard
    military reporting unit for an AO/NAI - via QgsDistanceArea rather
    than QGIS's own $area (which returns square DEGREES, not metres,
    on a layer in a geographic CRS unless the project's own Ellipsoidal
    measurement settings happen to be configured - not something this
    function should depend on to be correct). Use as
    mct_area_km2($geometry) - see _distance_area()'s own docstring for
    why this takes only a geometry, not a layer.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    area_m2 = _distance_area().measureArea(
        geometry
    )

    return area_m2 / 1_000_000.0


@qgsfunction(
    'mct_perimeter_km',
    group='Military Cartography Tools'
)
def mct_perimeter_km(values, feature=None, parent=None):

    """
    A polygon's own geodesic perimeter in kilometres - see
    mct_area_km2()'s own docstring for why QgsDistanceArea rather than
    QGIS's own $perimeter. Use as mct_perimeter_km($geometry).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    perimeter_m = _distance_area().measurePerimeter(
        geometry
    )

    return perimeter_m / 1000.0


@qgsfunction(
    'mct_length_km',
    group='Military Cartography Tools'
)
def mct_length_km(values, feature=None, parent=None):

    """
    A line's own geodesic length in kilometres - the line equivalent of
    mct_perimeter_km(), for phase lines/boundaries/axis of advance. Use
    as mct_length_km($geometry).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    length_m = _distance_area().measureLength(
        geometry
    )

    return length_m / 1000.0


_FUNCTIONS = [
    mct_sidc_svg,
    mct_build_sidc,
    mct_area_km2,
    mct_perimeter_km,
    mct_length_km,
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
