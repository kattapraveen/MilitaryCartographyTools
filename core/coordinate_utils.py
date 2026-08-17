# -*- coding: utf-8 -*-

"""
Coordinate transformation utilities.

Military Cartography Tools
"""

import datetime
import math

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsDistanceArea,
    QgsPointXY,
    QgsProject
)

from .geomag import GeoMag, WMM_2025


WGS84 = QgsCoordinateReferenceSystem(
    "EPSG:4326"
)


def project_to_wgs84(point):
    """
    Transform a point from the current project CRS
    to WGS84 latitude/longitude.

    Returns:
        QgsPointXY
        x = longitude
        y = latitude
    """

    project_crs = QgsProject.instance().crs()

    if project_crs == WGS84:
        return point


    transform = QgsCoordinateTransform(
        project_crs,
        WGS84,
        QgsProject.instance()
    )


    return transform.transform(
        point
    )



# The UTM grid is not a plain 6-degree lattice everywhere. Two
# exceptions are part of the standard itself, and both fall in
# northern Europe:
#
#   Band V (56-64N) - zone 31V is narrowed to 3 degrees and 32V
#   widened to 9, so that south-west Norway sits in one zone rather
#   than being split down the middle.
#
#   Band X (72-84N) - zones 32X, 34X and 36X do not exist at all, and
#   31X/33X/35X/37X widen to absorb their ground, keeping Svalbard's
#   islands whole.
#
# core/mgrs_engine.py has always applied both when assigning a zone to
# a coordinate; the drawn grid did not, which is the defect these
# helpers exist to fix (see docs/roadmap.md, 2026-08-17). Keyed
# (band, zone) rather than (zone, band) so the band - the thing that
# decides whether an exception applies at all - reads first.
UTM_ZONE_WIDTH_DEG = 6.0

UTM_ZONE_BOUNDS_EXCEPTIONS = {
    ("V", 31): (0.0, 3.0),
    ("V", 32): (3.0, 12.0),
    ("X", 31): (0.0, 9.0),
    ("X", 33): (9.0, 21.0),
    ("X", 35): (21.0, 33.0),
    ("X", 37): (33.0, 42.0),
}

UTM_ZONES_ABSENT_FROM_BAND = {
    ("X", 32),
    ("X", 34),
    ("X", 36),
}


def utm_zone_bounds(zone, band):

    """
    The (west, east) longitude bounds of one grid zone designator
    cell, in degrees - or None if that cell does not exist at all
    (32X, 34X and 36X).

    Returning None rather than raising is deliberate: a caller
    sweeping a range of zones across a range of bands should skip the
    absent ones as a normal part of the sweep, not have to know in
    advance which combinations are real.
    """

    key = (band, zone)

    if key in UTM_ZONES_ABSENT_FROM_BAND:
        return None

    if key in UTM_ZONE_BOUNDS_EXCEPTIONS:
        return UTM_ZONE_BOUNDS_EXCEPTIONS[key]

    west = -180.0 + ((zone - 1) * UTM_ZONE_WIDTH_DEG)

    return (west, west + UTM_ZONE_WIDTH_DEG)


def utm_candidate_zones(longitude_minimum, longitude_maximum):

    """
    The zone numbers that could possibly cover a longitude range,
    clamped to 1-60. Deliberately ONE ZONE WIDER on each side than
    plain 6-degree arithmetic gives, because a widened exception cell
    reaches into its neighbour's nominal ground: 32V covers 3-12E, so
    a map showing only 4-5E sits in zone 32 even though the naive
    arithmetic says 31.

    One zone of slack is enough - the widest exception (12 degrees) is
    exactly two nominal zones, so a cell can never start more than one
    zone before where the arithmetic puts it. Callers are expected to
    filter the result against utm_zone_bounds() for the band they are
    actually drawing, which is what removes the extra candidates
    again.
    """

    start = int((longitude_minimum + 180) / UTM_ZONE_WIDTH_DEG) + 1
    end = int((longitude_maximum + 180) / UTM_ZONE_WIDTH_DEG) + 1

    return list(
        range(
            max(1, start - 1),
            min(60, end + 1) + 1
        )
    )


def get_utm_zone(longitude):

    """
    Determine UTM zone from longitude.
    """

    zone = int(
        (longitude + 180) / 6
    ) + 1


    return zone



def get_utm_crs(latitude, longitude):

    """
    Return WGS84 UTM CRS for coordinate.
    """

    zone = get_utm_zone(
        longitude
    )


    if latitude >= 0:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone


    return QgsCoordinateReferenceSystem(
        f"EPSG:{epsg}"
    )



def get_utm_crs_from_zone_band(zone, band):

    """
    Return the WGS84 UTM CRS for a known UTM zone + MGRS latitude
    band letter - the hemisphere-selection counterpart to
    get_utm_crs() for callers that already have a zone/band (e.g.
    from a generated Grid Zone Designator feature) rather than a
    raw latitude/longitude to derive one from. Bands C-M are the
    southern hemisphere, N-X the northern.
    """

    if band >= "N":
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone

    return QgsCoordinateReferenceSystem(
        f"EPSG:{epsg}"
    )



def grid_convergence(latitude, longitude):

    """
    Approximate UTM grid convergence (the angle between grid
    north and true north) at a coordinate, in decimal degrees -
    positive means grid north is east of true north.

    Uses the standard first-order approximation (difference in
    longitude from the zone's central meridian, times sin of
    latitude). This is what grid-magnetic-angle diagrams on
    military topographic maps are built from; it omits the
    smaller ellipsoidal correction terms, which stay within a
    small fraction of a degree for any point inside a normal
    6-degree-wide UTM zone.
    """

    zone = get_utm_zone(
        longitude
    )

    central_meridian = -180 + (zone - 1) * 6 + 3

    delta_lambda = longitude - central_meridian

    return delta_lambda * math.sin(
        math.radians(latitude)
    )



def true_bearing_and_distance(lat1, lon1, lat2, lon2):

    """
    (true_bearing_degrees, distance_metres) from point 1 to point 2,
    both given as WGS84 latitude/longitude - the geodesic (ellipsoid
    surface) initial bearing and distance, not a flat-plane
    approximation, matching how the plugin's other coordinate
    calculations (e.g. MGRS conversion) already treat the earth as an
    ellipsoid rather than a plane.

    true_bearing_degrees is normalised to [0, 360) - QgsDistanceArea's
    own bearing() returns radians in (-pi, pi] (e.g. due west comes
    back as -90 degrees rather than 270), which doesn't match the
    0-360 convention azimuths are conventionally reported in.
    """

    distance_area = QgsDistanceArea()

    distance_area.setEllipsoid(
        "WGS84"
    )

    distance_area.setSourceCrs(
        WGS84,
        QgsProject.instance().transformContext()
    )

    point1 = QgsPointXY(lon1, lat1)
    point2 = QgsPointXY(lon2, lat2)

    distance_m = distance_area.measureLine(
        point1,
        point2
    )

    bearing_deg = math.degrees(
        distance_area.bearing(point1, point2)
    ) % 360.0

    return bearing_deg, distance_m



def _decimal_year(date=None):

    """
    A date (defaulting to today) as a decimal year, e.g.
    2026-07-27 -> ~2026.57.
    """

    if date is None:
        date = datetime.date.today()

    year_start = datetime.date(date.year, 1, 1)
    next_year_start = datetime.date(date.year + 1, 1, 1)

    days_in_year = (next_year_start - year_start).days
    days_passed = (date - year_start).days

    return date.year + (days_passed / days_in_year)



def magnetic_declination(latitude, longitude, date=None):

    """
    Magnetic declination (the angle between true north and
    magnetic north) at a coordinate and date, in decimal degrees -
    positive means magnetic north is east of true north.

    Unlike grid_convergence(), this isn't derivable from
    projection geometry alone - it depends on Earth's actual,
    slowly-shifting magnetic field. Uses NOAA/NCEI's WMM2025 model
    (valid 2025.0-2030.0) via a vendored copy of pyGeoMag - see
    THIRD_PARTY_NOTICES.md. allow_date_outside_lifespan=True so a
    date outside that window still returns an estimate (accuracy
    degrades the further outside it) rather than raising.
    """

    geo_mag = GeoMag(
        coefficients_data=WMM_2025
    )

    result = geo_mag.calculate(
        glat=latitude,
        glon=longitude,
        alt=0,
        time=_decimal_year(date),
        allow_date_outside_lifespan=True
    )

    return result.d