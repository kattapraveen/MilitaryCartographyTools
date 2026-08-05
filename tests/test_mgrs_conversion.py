# -*- coding: utf-8 -*-

"""
Tests for core.MGRSConverter (core/mgrs_converter.py + the vendored
core/mgrs_engine.py) and the coordinate/declination helpers in
core/coordinate_utils.py.

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.core import (
    MGRSConverter,
    mgrs_square_id,
    grid_convergence,
    magnetic_declination,
    true_bearing_and_distance,
)
from MilitaryCartographyTools.core.mgrs_engine import MgrsException


# Dar es Salaam-ish reference point, ordinary (non-polar) case -
# used throughout so every test works from the same known-good
# coordinate.
REF_LAT = -6.7924
REF_LON = 39.2083


class TestMGRSConversion(QgisTestCase):

    def test_round_trip(self):

        converter = MGRSConverter(precision=5)

        mgrs = converter.convert(REF_LAT, REF_LON)

        lat, lon = converter.to_latlon(mgrs)

        self.assertAlmostEqual(lat, REF_LAT, delta=0.001)
        self.assertAlmostEqual(lon, REF_LON, delta=0.001)


    def test_round_trip_at_every_precision(self):

        # Lower precision means a coarser (larger) grid square, so
        # the round-trip tolerance loosens accordingly - precision
        # 0 is a 100km square, precision 5 is 1m.
        tolerances = {
            0: 1.0,
            1: 0.1,
            2: 0.01,
            3: 0.005,
            4: 0.001,
            5: 0.001,
        }

        for precision, tolerance in tolerances.items():

            with self.subTest(precision=precision):

                converter = MGRSConverter(precision=precision)

                mgrs = converter.convert(REF_LAT, REF_LON)

                lat, lon = converter.to_latlon(mgrs)

                self.assertAlmostEqual(lat, REF_LAT, delta=tolerance)
                self.assertAlmostEqual(lon, REF_LON, delta=tolerance)


    def test_precision_out_of_range_raises(self):

        with self.assertRaises(ValueError):
            MGRSConverter(precision=6)

        with self.assertRaises(ValueError):
            MGRSConverter(precision=-1)


    def test_format_with_spaces(self):

        converter = MGRSConverter(precision=5)

        raw = converter.convert(REF_LAT, REF_LON)

        formatted = converter.format(raw, spaces=True)

        parts = formatted.split(" ")

        self.assertEqual(len(parts), 4)


    def test_format_without_spaces(self):

        converter = MGRSConverter(precision=5)

        raw = converter.convert(REF_LAT, REF_LON)

        formatted = converter.format(raw, spaces=False)

        self.assertNotIn(" ", formatted)


    def test_format_empty_string(self):

        converter = MGRSConverter()

        self.assertEqual(converter.format(""), "")


    def test_component_extraction(self):

        converter = MGRSConverter(precision=5)

        formatted = converter.format(
            converter.convert(REF_LAT, REF_LON)
        )

        gzd = converter.gzd(formatted)
        zone = converter.zone(formatted)
        square = converter.square(formatted)
        easting = converter.easting(formatted)
        northing = converter.northing(formatted)

        self.assertTrue(gzd.startswith(zone))
        self.assertEqual(len(square), 2)
        self.assertEqual(len(easting), 5)
        self.assertEqual(len(northing), 5)

        # Re-assembling the parts should reproduce the same string
        # format() produced.
        self.assertEqual(
            f"{gzd} {square} {easting} {northing}",
            formatted
        )


    def test_mgrs_square_id_matches_converter(self):

        # mgrs_square_id() works from raw UTM zone/easting/northing
        # (used by the grid generators, which already have those
        # values from a GZD feature) rather than lat/lon - cross-
        # check it agrees with the full lat/lon-based converter for
        # the same point.
        converter = MGRSConverter(precision=0)

        square_via_converter = converter.square(
            converter.format(
                converter.convert(REF_LAT, REF_LON)
            )
        )

        # Zone/easting/northing for REF_LAT/REF_LON in UTM 37S.
        from MilitaryCartographyTools.core.coordinate_utils import get_utm_crs
        from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsPointXY, QgsProject

        utm_crs = get_utm_crs(REF_LAT, REF_LON)

        transform = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:4326"),
            utm_crs,
            QgsProject.instance()
        )

        utm_point = transform.transform(
            QgsPointXY(REF_LON, REF_LAT)
        )

        zone = int(utm_crs.authid().split(":")[-1][-2:])

        square_via_helper = mgrs_square_id(
            zone,
            utm_point.x(),
            utm_point.y()
        )

        self.assertEqual(square_via_converter, square_via_helper)


    def test_ups_validation_rejects_invalid_second_letter(self):

        """
        Regression test for the mgrs_engine.py bug fix: a UPS/polar
        coordinate string whose second letter falls in the invalid
        set {D,E,M,N,V,W} must be rejected, not silently accepted.
        Before the fix, `letters[1] in [invalid]` (a list containing
        a list) could never be true, so this validation was a no-op.
        """

        converter = MGRSConverter()

        with self.assertRaises(MgrsException):
            converter.to_latlon("ADQ7513515087")


    def test_grid_convergence_near_zero_at_central_meridian(self):

        # UTM zone 37's central meridian is 39 degrees East - at
        # (any latitude, 39E) convergence should be ~0.
        self.assertAlmostEqual(
            grid_convergence(REF_LAT, 39.0),
            0.0,
            delta=0.01
        )


    def test_grid_convergence_sign_matches_hemisphere_and_side(self):

        # East of the central meridian, in the southern hemisphere,
        # grid convergence is negative (this first-order
        # approximation's sign convention - confirmed against the
        # plugin's own documented behaviour).
        value = grid_convergence(REF_LAT, 41.0)

        self.assertLess(value, 0.0)


    def test_magnetic_declination_returns_a_plausible_value(self):

        declination = magnetic_declination(REF_LAT, REF_LON)

        self.assertIsInstance(declination, float)

        # WMM declination values are bounded well within +/-90
        # degrees anywhere on Earth - a loose sanity bound, not a
        # precise expected value.
        self.assertGreater(declination, -90.0)
        self.assertLess(declination, 90.0)


    def test_true_bearing_and_distance_due_north(self):

        bearing, distance = true_bearing_and_distance(
            REF_LAT, REF_LON,
            REF_LAT + 1.0, REF_LON
        )

        self.assertAlmostEqual(bearing, 0.0, delta=0.01)

        # One degree of latitude's ellipsoidal arc length varies with
        # latitude (WGS84: ~110,574 m at the equator to ~111,694 m at
        # the poles) - a loose bound covering that whole range, not a
        # single equator-only expected value.
        self.assertGreater(distance, 110500.0)
        self.assertLess(distance, 111700.0)


    def test_true_bearing_and_distance_due_west_normalises_to_270(self):

        # QgsDistanceArea.bearing() itself returns radians in
        # (-pi, pi] - due west comes back as -90 degrees there, not
        # the 270 a conventional 0-360 azimuth would read.
        bearing, _distance = true_bearing_and_distance(
            REF_LAT, REF_LON,
            REF_LAT, REF_LON - 1.0
        )

        self.assertAlmostEqual(bearing, 270.0, delta=0.5)


    def test_true_bearing_and_distance_is_symmetric_in_distance_not_bearing(self):

        forward_bearing, forward_distance = true_bearing_and_distance(
            REF_LAT, REF_LON,
            REF_LAT + 1.0, REF_LON + 1.0
        )

        reverse_bearing, reverse_distance = true_bearing_and_distance(
            REF_LAT + 1.0, REF_LON + 1.0,
            REF_LAT, REF_LON
        )

        self.assertAlmostEqual(forward_distance, reverse_distance, delta=1.0)

        # The reverse bearing is roughly opposite (offset by ~180
        # degrees), not equal to the forward one.
        self.assertAlmostEqual(
            (forward_bearing + 180.0) % 360.0,
            reverse_bearing,
            delta=1.0
        )
