# -*- coding: utf-8 -*-

"""
Tests for algorithms/range_rings.py.

The behaviour that matters, and the reason this is not just "buffer
the points": a ring is a NAME and a radius, and merging is keyed on
the name. Rings of the same type union where they overlap; rings of
different types never merge with each other. Asked for in those
terms on 2026-10-26.

Military Cartography Tools
"""

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransformContext,
    QgsDistanceArea,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessing,
    QgsVectorLayer,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.algorithms import (
    MilitaryCartographyProvider,
    PROVIDER_ID,
    parse_rings,
)
from MilitaryCartographyTools.algorithms.range_rings import (
    COLOUR_OPTIONS,
    CUSTOM_COLOUR_INDEX,
    CUSTOM_COLOUR_LABEL,
    LINE_STYLES,
    NATO_COLOURS,
    resolve_colour,
)


ALGORITHM = f"{PROVIDER_ID}:rangerings"


class TestParseRings(QgisTestCase):

    def test_radii_alone_name_themselves_after_their_distance(self):

        self.assertEqual(
            parse_rings("600, 1200", ""),
            [("600 km", 600.0), ("1200 km", 1200.0)]
        )


    def test_names_are_positional_and_optional(self):

        self.assertEqual(
            parse_rings("600,1200", "Combat,Ferry"),
            [("Combat", 600.0), ("Ferry", 1200.0)]
        )


    def test_a_missing_name_falls_back_to_the_distance(self):

        self.assertEqual(
            parse_rings("600,1200", "Combat"),
            [("Combat", 600.0), ("1200 km", 1200.0)]
        )


    def test_semicolons_and_stray_spaces_are_tolerated(self):

        self.assertEqual(
            parse_rings(" 600 ;  1200 ", ""),
            [("600 km", 600.0), ("1200 km", 1200.0)]
        )


    def test_nothing_at_all_is_refused_readably(self):

        with self.assertRaises(ValueError) as raised:
            parse_rings("", "")

        self.assertIn("at least one", str(raised.exception))


    def test_text_that_is_not_a_number_names_the_offending_piece(self):

        with self.assertRaises(ValueError) as raised:
            parse_rings("600, banana", "")

        self.assertIn("banana", str(raised.exception))


    def test_a_zero_or_negative_radius_is_refused(self):

        for radii in ("0", "-5", "600,-5"):

            with self.subTest(radii=radii):

                with self.assertRaises(ValueError):
                    parse_rings(radii, "")


class _RangeRingsTestCase(QgisTestCase):

    def setUp(self):

        super().setUp()

        # Held on self: the Processing registry does NOT keep a
        # Python provider alive, and a collected one fails later with
        # "Error creating algorithm from createInstance()".
        self.provider = MilitaryCartographyProvider()

        QgsApplication.processingRegistry().addProvider(self.provider)


    def tearDown(self):

        QgsApplication.processingRegistry().removeProvider(self.provider)

        super().tearDown()


    def _points(self, coordinates):

        layer = QgsVectorLayer("Point?crs=EPSG:4326", "bases", "memory")

        layer.startEditing()

        for longitude, latitude in coordinates:

            feature = QgsFeature(layer.fields())

            feature.setGeometry(
                QgsGeometry.fromPointXY(QgsPointXY(longitude, latitude))
            )

            layer.addFeature(feature)

        layer.commitChanges()

        return layer


    def _run(self, layer, **overrides):

        import processing

        parameters = {
            "INPUT": layer,
            "RADII": "600",
            "NAMES": "",
            "COLOUR": 0,
            "LINE_STYLE": 0,
            "LINE_WIDTH": 0.5,
            "MERGE": True,
            "LABEL_ON": True,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }

        parameters.update(overrides)

        return processing.run(ALGORITHM, parameters)["OUTPUT"]


class TestMergingIsKeyedOnTheRingName(_RangeRingsTestCase):

    # Two bases ~110 km apart, and a third ~3,000 km south. At a
    # 600 km radius the first two overlap and the third cannot.
    CLOSE_PAIR_AND_ONE_FAR = [(36.0, -1.0), (37.0, -1.0), (36.0, -28.0)]


    def test_same_type_rings_that_overlap_become_one_feature(self):

        result = self._run(
            self._points(self.CLOSE_PAIR_AND_ONE_FAR),
            RADII="600"
        )

        # The overlapping pair unions into one envelope; the distant
        # base stays its own.
        self.assertEqual(result.featureCount(), 2)


    def test_different_types_never_merge_even_when_overlapping(self):

        """
        The point of keying on the name. A single base with a 600 km
        and a 1,200 km ring must give two readable outlines, not one
        blob - the smaller circle lies entirely inside the larger.
        """

        result = self._run(
            self._points([(36.0, -1.0)]),
            RADII="600,1200",
            NAMES="Combat,Ferry"
        )

        self.assertEqual(
            sorted(feature["ring"] for feature in result.getFeatures()),
            ["Combat", "Ferry"]
        )


    def test_merging_off_keeps_one_ring_per_point_per_type(self):

        result = self._run(
            self._points(self.CLOSE_PAIR_AND_ONE_FAR),
            RADII="600,1200",
            NAMES="Combat,Ferry",
            MERGE=False
        )

        self.assertEqual(result.featureCount(), 6)


    def test_each_feature_carries_its_ring_name_and_radius(self):

        result = self._run(
            self._points([(36.0, -1.0)]),
            RADII="600,1200",
            NAMES="Combat,Ferry"
        )

        rows = {
            feature["ring"]: feature["radius_km"]
            for feature in result.getFeatures()
        }

        self.assertEqual(rows, {"Combat": 600.0, "Ferry": 1200.0})


class TestTheRadiusIsATrueGroundDistance(_RangeRingsTestCase):

    """
    Buffering in EPSG:4326 would buffer in DEGREES - neither circular
    nor the requested distance anywhere but the equator. Each circle
    is built in an azimuthal equidistant projection centred on its
    own point instead.
    """

    def _measured_radii(self, longitude, latitude, radius_km):

        result = self._run(
            self._points([(longitude, latitude)]),
            RADII=str(radius_km),
            MERGE=False
        )

        ring = next(result.getFeatures()).geometry().asPolygon()[0]

        measure = QgsDistanceArea()

        measure.setSourceCrs(
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsCoordinateTransformContext()
        )

        measure.setEllipsoid("WGS84")

        centre = QgsPointXY(longitude, latitude)

        return [
            measure.measureLine(centre, QgsPointXY(vertex)) / 1000.0
            for vertex in ring[::30]
        ]


    def test_every_point_on_the_ring_is_the_requested_distance_away(self):

        for radius in (600.0, 1200.0):

            with self.subTest(radius=radius):

                measured = self._measured_radii(36.0, -1.0, radius)

                for distance in measured:
                    self.assertAlmostEqual(distance, radius, delta=1.0)


    def test_it_holds_at_high_latitude_where_degrees_would_not(self):

        """
        At 60 degrees north a degree of longitude is half what it is
        at the equator. A degree-based buffer would come out as an
        ellipse half the width it should be; this must not.
        """

        measured = self._measured_radii(20.0, 60.0, 600.0)

        for distance in measured:
            self.assertAlmostEqual(distance, 600.0, delta=1.0)


class TestInputHandling(_RangeRingsTestCase):

    def test_an_empty_point_layer_is_refused_rather_than_silent(self):

        from qgis.core import QgsProcessingException

        with self.assertRaises(QgsProcessingException):
            self._run(self._points([]))


    def test_bad_radii_text_is_reported_through_processing(self):

        from qgis.core import QgsProcessingException

        with self.assertRaises(QgsProcessingException) as raised:
            self._run(self._points([(36.0, -1.0)]), RADII="banana")

        self.assertIn("banana", str(raised.exception))


    def test_the_output_is_wgs84_whatever_the_input_crs(self):

        layer = self._points([(36.0, -1.0)])

        result = self._run(layer)

        self.assertEqual(result.crs().authid(), "EPSG:4326")


class TestColourOptions(QgisTestCase):

    """
    Standard-identity colours plus a free choice, asked for on
    2026-10-26: "standard colours from NATO. but also option to
    choose any other colour if required".
    """

    def test_the_standard_identities_are_offered_first(self):

        self.assertEqual(
            list(COLOUR_OPTIONS[:4]),
            [
                "Friend (blue)",
                "Hostile (red)",
                "Neutral (green)",
                "Unknown (yellow)",
            ]
        )


    def test_custom_is_the_last_option(self):

        self.assertEqual(COLOUR_OPTIONS[-1], CUSTOM_COLOUR_LABEL)
        self.assertEqual(CUSTOM_COLOUR_INDEX, len(COLOUR_OPTIONS) - 1)


    def test_they_are_the_same_colours_this_plugin_already_draws_nato_in(self):

        """
        The guard against two tables of NATO colours drifting apart.

        These are not invented here - they are lifted from
        _control_measure_shared.py's own _AFFILIATION_COLOR_EXPRESSION,
        which is what every NATO control measure in the plugin is
        already coloured by. If this fails, one of the two moved and
        the ring colours no longer match the symbology beside them.
        """

        import re

        from MilitaryCartographyTools.military_symbology import (
            _control_measure_shared,
        )

        with open(_control_measure_shared.__file__) as handle:
            source = handle.read()

        expression = re.search(
            r"_AFFILIATION_COLOR_EXPRESSION = \((.*?)\n\)",
            source,
            re.S
        ).group(1)

        canonical = {
            affiliation: "#%02x%02x%02x" % (int(r), int(g), int(b))
            for affiliation, r, g, b in re.findall(
                r"'(\w+)' THEN color_rgb\((\d+), (\d+), (\d+)\)",
                expression
            )
        }

        ours = {
            "friend": NATO_COLOURS[0][1],
            "hostile": NATO_COLOURS[1][1],
            "neutral": NATO_COLOURS[2][1],
            "unknown": NATO_COLOURS[3][1],
        }

        self.assertEqual(ours, canonical)


    def test_a_standard_identity_ignores_the_custom_picker(self):

        from qgis.PyQt.QtGui import QColor

        self.assertEqual(
            resolve_colour(0, QColor("#123456")),
            NATO_COLOURS[0][1]
        )


    def test_custom_takes_whatever_the_picker_holds(self):

        from qgis.PyQt.QtGui import QColor

        self.assertEqual(
            resolve_colour(CUSTOM_COLOUR_INDEX, QColor("#123456")),
            "#123456"
        )


    def test_an_index_from_a_stale_model_falls_back_rather_than_raising(self):

        """
        Processing can hand over an index from a saved model written
        against a shorter options list. Falling back beats an
        IndexError out of a background algorithm.
        """

        self.assertEqual(resolve_colour(99, None), NATO_COLOURS[0][1])
        self.assertEqual(resolve_colour(-1, None), NATO_COLOURS[0][1])


    def test_every_qgis_pen_style_worth_drawing_is_offered(self):

        """
        All five of QGIS's simple-line pen styles. The sixth, "no
        pen", would draw nothing and is deliberately absent.
        """

        self.assertEqual(
            [style for _, style in LINE_STYLES],
            ["solid", "dash", "dot", "dash dot", "dash dot dot"]
        )
