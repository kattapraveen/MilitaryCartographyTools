# -*- coding: utf-8 -*-

"""
MGRS expression functions
for Military Cartography Tools
"""

from qgis.core import (
    QgsExpression,
    QgsLayoutItemMap,
    QgsProject,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPointXY,
    qgsfunction
)

import datetime

from ..core import MGRSConverter, grid_convergence, magnetic_declination
from ..core.coordinate_utils import WGS84



# ============================================================
# MGRS precision formatter
# ============================================================

def format_mgrs_precision(mgrs_text, precision):

    """
    Reduce MGRS precision.

    precision:
        5 = 1 metre
        4 = 10 metres
        3 = 100 metres
        2 = 1 kilometre
    """

    try:
        precision = int(precision)
    except Exception:
        # precision came from a QGIS expression argument, so it
        # could be a non-numeric string, None, or an expression
        # evaluation error object - fall back to full precision
        # rather than letting an unexpected argument type crash
        # every expression that calls this.
        precision = 5


    if precision >= 5:
        return mgrs_text


    parts = mgrs_text.split()

    if len(parts) != 4:
        return mgrs_text


    zone = parts[0]
    square = parts[1]
    easting = parts[2]
    northing = parts[3]


    easting = easting[:precision]
    northing = northing[:precision]


    return f"{zone} {square} {easting} {northing}"



# ============================================================
# MGRS from latitude / longitude
# ============================================================

@qgsfunction(
    'mct_mgrs',
    group='Military Cartography Tools'
)
def mct_mgrs(values, feature=None, parent=None):

    if len(values) < 2:
        return "Need latitude, longitude"


    latitude = float(values[0])
    longitude = float(values[1])


    converter = MGRSConverter()

    result = converter.convert(
        latitude,
        longitude
    )

    return converter.format(result)



# ============================================================
# MGRS components from latitude / longitude
# ============================================================

def _mgrs_component(values, extractor):

    """
    Shared body for the four mct_mgrs_*(lat, lon) component
    functions below - convert lat/lon to a raw MGRS string, then
    hand it to whichever MGRSConverter method extracts the
    requested piece.
    """

    if len(values) < 2:
        return "Need latitude, longitude"


    latitude = float(values[0])
    longitude = float(values[1])


    converter = MGRSConverter()

    mgrs_string = converter.convert(
        latitude,
        longitude
    )

    return extractor(
        converter,
        mgrs_string
    )



@qgsfunction(
    'mct_mgrs_zone',
    group='Military Cartography Tools'
)
def mct_mgrs_zone(values, feature=None, parent=None):

    """
    mct_mgrs_zone(latitude, longitude)

    Returns the Grid Zone Designator, e.g. "37M".
    """

    return _mgrs_component(
        values,
        lambda converter, mgrs_string: converter.gzd(mgrs_string)
    )



@qgsfunction(
    'mct_mgrs_square',
    group='Military Cartography Tools'
)
def mct_mgrs_square(values, feature=None, parent=None):

    """
    mct_mgrs_square(latitude, longitude)

    Returns the 100km square identifier, e.g. "DQ".
    """

    return _mgrs_component(
        values,
        lambda converter, mgrs_string: converter.square(mgrs_string)
    )



@qgsfunction(
    'mct_mgrs_easting',
    group='Military Cartography Tools'
)
def mct_mgrs_easting(values, feature=None, parent=None):

    """
    mct_mgrs_easting(latitude, longitude)

    Returns the full-precision easting digits, e.g. "75135".
    """

    return _mgrs_component(
        values,
        lambda converter, mgrs_string: converter.easting(mgrs_string)
    )



@qgsfunction(
    'mct_mgrs_northing',
    group='Military Cartography Tools'
)
def mct_mgrs_northing(values, feature=None, parent=None):

    """
    mct_mgrs_northing(latitude, longitude)

    Returns the full-precision northing digits, e.g. "15087".
    """

    return _mgrs_component(
        values,
        lambda converter, mgrs_string: converter.northing(mgrs_string)
    )



# ============================================================
# Reverse conversion: MGRS string back to a coordinate
# ============================================================

@qgsfunction(
    'mct_mgrs_to_point',
    group='Military Cartography Tools'
)
def mct_mgrs_to_point(values, feature=None, parent=None):

    """
    mct_mgrs_to_point(mgrs_string)

    Returns a point geometry (WGS84) for an MGRS string.
    """

    if len(values) < 1:
        return "Need MGRS string"


    converter = MGRSConverter()

    latitude, longitude = converter.to_latlon(
        str(values[0])
    )

    return QgsGeometry.fromPointXY(
        QgsPointXY(longitude, latitude)
    )



@qgsfunction(
    'mct_mgrs_lat',
    group='Military Cartography Tools'
)
def mct_mgrs_lat(values, feature=None, parent=None):

    """
    mct_mgrs_lat(mgrs_string)

    Returns the WGS84 latitude for an MGRS string.
    """

    if len(values) < 1:
        return "Need MGRS string"


    converter = MGRSConverter()

    latitude, longitude = converter.to_latlon(
        str(values[0])
    )

    return latitude



@qgsfunction(
    'mct_mgrs_lon',
    group='Military Cartography Tools'
)
def mct_mgrs_lon(values, feature=None, parent=None):

    """
    mct_mgrs_lon(mgrs_string)

    Returns the WGS84 longitude for an MGRS string.
    """

    if len(values) < 1:
        return "Need MGRS string"


    converter = MGRSConverter()

    latitude, longitude = converter.to_latlon(
        str(values[0])
    )

    return longitude



# ============================================================
# Grid convergence
# ============================================================

@qgsfunction(
    'mct_grid_convergence',
    group='Military Cartography Tools'
)
def mct_grid_convergence(values, feature=None, parent=None):

    """
    mct_grid_convergence(latitude, longitude)

    Returns the approximate UTM grid convergence at a
    coordinate, in decimal degrees.
    """

    if len(values) < 2:
        return "Need latitude, longitude"


    return grid_convergence(
        float(values[0]),
        float(values[1])
    )



# ============================================================
# Magnetic declination
# ============================================================

def _parse_date(value):

    """
    Parse an optional trailing date argument shared by the
    mct_*_magnetic_declination() functions below. QGIS expression
    date literals/fields typically arrive as a QDate or a
    datetime.date already (both expose year/month/day), so this
    only needs to fall back to ISO-string parsing for a plain
    text argument; anything else (missing/None) defers to
    magnetic_declination()'s own "today" default.
    """

    if value is None or value == '':
        return None

    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return datetime.date(value.year(), value.month(), value.day()) \
            if callable(value.year) else \
            datetime.date(value.year, value.month, value.day)

    return datetime.date.fromisoformat(str(value))



@qgsfunction(
    'mct_magnetic_declination',
    group='Military Cartography Tools'
)
def mct_magnetic_declination(values, feature=None, parent=None):

    """
    mct_magnetic_declination(latitude, longitude, [date])

    Returns the magnetic declination at a coordinate, in decimal
    degrees, using the WMM2025 model. date is an optional ISO
    string ('2026-07-27') or date value - defaults to today.
    """

    if len(values) < 2:
        return "Need latitude, longitude"


    date = _parse_date(
        values[2]
    ) if len(values) > 2 else None

    return magnetic_declination(
        float(values[0]),
        float(values[1]),
        date
    )



# ============================================================
# Layout / map item lookup helpers
#
# Every mct_map_*() function below takes the same two leading
# arguments - a layout name and an optional map item id - so the
# lookup itself (shared by all of them) lives here once. Each
# function still parses its own argument list, since a couple
# (like mct_map_center_mgrs's precision) have an extra parameter
# in between.
# ============================================================

def _find_layout(project, layout_name):

    for layout in project.layoutManager().printLayouts():

        if layout.name() == layout_name:

            return layout

    return None



def _find_map_item(layout, map_id=None):

    for item in layout.items():

        if isinstance(item, QgsLayoutItemMap):

            if map_id:

                if item.id() == map_id:
                    return item

            else:

                return item

    return None



def _get_map_item(values, project, map_id_index=1):

    """
    Resolve (layout name, optional map id) from values into a
    map item. map_id_index is the position of the map id
    argument, since it differs between functions with an extra
    parameter (like precision) in between.

    Returns (map_item, error_message) - error_message is None
    on success.
    """

    if len(values) < 1:
        return None, "Need layout name"


    layout_name = str(values[0])

    map_id = None

    if len(values) > map_id_index:
        map_id = str(values[map_id_index])


    layout = _find_layout(project, layout_name)

    if layout is None:
        return None, "Layout not found"


    map_item = _find_map_item(layout, map_id)

    if map_item is None:
        return None, "Map not found"


    return map_item, None



def _map_center_wgs84(map_item, project):

    """
    Map item's extent centre, transformed to WGS84 lat/lon.
    """

    center = map_item.extent().center()

    transform = QgsCoordinateTransform(
        map_item.crs(),
        WGS84,
        project
    )

    center = transform.transform(center)

    return center.y(), center.x()



# ============================================================
# MGRS from layout map centre
# ============================================================

@qgsfunction(
    'mct_map_center_mgrs',
    group='Military Cartography Tools'
)
def mct_map_center_mgrs(values, feature=None, parent=None):

    project = QgsProject.instance()


    # Default precision
    precision = 5

    if len(values) > 1:
        precision = int(values[1])


    # Map id (if given) comes after precision for this function.
    map_item, error = _get_map_item(values, project, map_id_index=2)

    if error:
        return error


    latitude, longitude = _map_center_wgs84(map_item, project)


    converter = MGRSConverter()

    result = converter.convert(
        latitude,
        longitude
    )

    mgrs_text = converter.format(result)


    return format_mgrs_precision(
        mgrs_text,
        precision
    )



# ============================================================
# Layout map metadata
# ============================================================

@qgsfunction(
    'mct_map_scale',
    group='Military Cartography Tools'
)
def mct_map_scale(values, feature=None, parent=None):

    """
    mct_map_scale(layout_name, [map_id])

    Returns the map item's scale as "1:N".
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    return f"1:{round(map_item.scale())}"



@qgsfunction(
    'mct_map_rotation',
    group='Military Cartography Tools'
)
def mct_map_rotation(values, feature=None, parent=None):

    """
    mct_map_rotation(layout_name, [map_id])

    Returns the map item's map rotation, in degrees.
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    return map_item.mapRotation()



@qgsfunction(
    'mct_map_width',
    group='Military Cartography Tools'
)
def mct_map_width(values, feature=None, parent=None):

    """
    mct_map_width(layout_name, [map_id])

    Returns the map item's extent width, in the map's own CRS
    units (typically metres for a projected CRS).
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    return map_item.extent().width()



@qgsfunction(
    'mct_map_height',
    group='Military Cartography Tools'
)
def mct_map_height(values, feature=None, parent=None):

    """
    mct_map_height(layout_name, [map_id])

    Returns the map item's extent height, in the map's own CRS
    units (typically metres for a projected CRS).
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    return map_item.extent().height()



@qgsfunction(
    'mct_map_center_lat',
    group='Military Cartography Tools'
)
def mct_map_center_lat(values, feature=None, parent=None):

    """
    mct_map_center_lat(layout_name, [map_id])

    Returns the map item's centre latitude (WGS84, decimal
    degrees).
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    latitude, longitude = _map_center_wgs84(map_item, project)

    return latitude



@qgsfunction(
    'mct_map_center_lon',
    group='Military Cartography Tools'
)
def mct_map_center_lon(values, feature=None, parent=None):

    """
    mct_map_center_lon(layout_name, [map_id])

    Returns the map item's centre longitude (WGS84, decimal
    degrees).
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    latitude, longitude = _map_center_wgs84(map_item, project)

    return longitude



@qgsfunction(
    'mct_map_convergence',
    group='Military Cartography Tools'
)
def mct_map_convergence(values, feature=None, parent=None):

    """
    mct_map_convergence(layout_name, [map_id])

    Returns the approximate UTM grid convergence at the map
    item's centre, in decimal degrees - the grid-magnetic-angle
    diagram's "grid to true north" figure.
    """

    project = QgsProject.instance()

    map_item, error = _get_map_item(values, project)

    if error:
        return error


    latitude, longitude = _map_center_wgs84(map_item, project)

    return grid_convergence(latitude, longitude)



@qgsfunction(
    'mct_map_magnetic_declination',
    group='Military Cartography Tools'
)
def mct_map_magnetic_declination(values, feature=None, parent=None):

    """
    mct_map_magnetic_declination(layout_name, [date], [map_id])

    Returns the magnetic declination at the map item's centre, in
    decimal degrees, using the WMM2025 model. date is an optional
    ISO string ('2026-07-27') or date value - defaults to today.
    Same argument order as mct_map_center_mgrs (the optional
    middle argument comes before map_id).
    """

    project = QgsProject.instance()

    date = _parse_date(
        values[1]
    ) if len(values) > 1 else None

    map_item, error = _get_map_item(values, project, map_id_index=2)

    if error:
        return error


    latitude, longitude = _map_center_wgs84(map_item, project)

    return magnetic_declination(latitude, longitude, date)



# ============================================================
# Registration
# ============================================================

_FUNCTIONS = [
    mct_mgrs,
    mct_mgrs_zone,
    mct_mgrs_square,
    mct_mgrs_easting,
    mct_mgrs_northing,
    mct_mgrs_to_point,
    mct_mgrs_lat,
    mct_mgrs_lon,
    mct_grid_convergence,
    mct_magnetic_declination,
    mct_map_center_mgrs,
    mct_map_scale,
    mct_map_rotation,
    mct_map_width,
    mct_map_height,
    mct_map_center_lat,
    mct_map_center_lon,
    mct_map_convergence,
    mct_map_magnetic_declination,
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