# -*- coding: utf-8 -*-

"""
Tests for the UTM grid's two standard exceptions - the narrowed/
widened 31V and 32V over south-west Norway, and the missing 32X/34X/
36X over Svalbard with their neighbours widened to absorb the ground.

core/mgrs_engine.py has always applied both when assigning a zone to a
coordinate (see _latLonToUtm()'s own special-case block); the DRAWN
grid did not, so the grid layer and the plugin's own MGRS conversion
disagreed with each other in exactly these two regions. These tests
pin the drawn grid to the standard, and pin the two agreeing with each
other.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRectangle,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.core import MGRSConverter
from MilitaryCartographyTools.core.coordinate_utils import (
    utm_candidate_zones,
    utm_zone_bounds,
)
from MilitaryCartographyTools.grid.grid_labels import GridLabelManager
from MilitaryCartographyTools.grid.utm_grid import (
    _minimum_half_extent_m,
    UTMGridGenerator,
)
from MilitaryCartographyTools.layout.grid_position import _required_zones


# The standard's own numbers, written out rather than computed, so a
# change to the implementation cannot quietly redefine what "correct"
# means here.
EXPECTED_BOUNDS = {
    (31, "V"): (0.0, 3.0),
    (32, "V"): (3.0, 12.0),
    (31, "X"): (0.0, 9.0),
    (33, "X"): (9.0, 21.0),
    (35, "X"): (21.0, 33.0),
    (37, "X"): (33.0, 42.0),
}

ABSENT = [(32, "X"), (34, "X"), (36, "X")]


class TestZoneBounds(QgisTestCase):

    def test_the_six_exception_cells_have_their_standard_bounds(self):

        for (zone, band), expected in EXPECTED_BOUNDS.items():

            with self.subTest(cell=f"{zone}{band}"):

                self.assertEqual(
                    utm_zone_bounds(zone, band),
                    expected
                )


    def test_the_three_missing_cells_do_not_exist(self):

        for zone, band in ABSENT:

            with self.subTest(cell=f"{zone}{band}"):

                self.assertIsNone(
                    utm_zone_bounds(zone, band)
                )


    def test_the_exceptions_tile_their_bands_without_gap_or_overlap(self):

        # The whole point of widening a neighbour is that no ground is
        # lost. 31V+32V must cover 0-12E exactly, as two plain zones
        # would have; 31X through 37X must cover 0-42E exactly, as
        # seven plain zones would have.
        band_v = [utm_zone_bounds(z, "V") for z in (31, 32)]
        band_x = [
            utm_zone_bounds(z, "X")
            for z in range(31, 38)
            if utm_zone_bounds(z, "X") is not None
        ]

        for cells, expected_span in ((band_v, (0.0, 12.0)), (band_x, (0.0, 42.0))):

            with self.subTest(span=expected_span):

                self.assertEqual(cells[0][0], expected_span[0])
                self.assertEqual(cells[-1][1], expected_span[1])

                for earlier, later in zip(cells, cells[1:]):
                    self.assertEqual(earlier[1], later[0])


    def test_a_zone_outside_the_exception_bands_is_a_plain_six_degrees(self):

        # 31U is directly below 31V and takes no exception at all -
        # confirming the exceptions are scoped to their own bands and
        # have not leaked into the general case.
        self.assertEqual(utm_zone_bounds(31, "U"), (0.0, 6.0))
        self.assertEqual(utm_zone_bounds(32, "U"), (6.0, 12.0))
        self.assertEqual(utm_zone_bounds(1, "N"), (-180.0, -174.0))


class TestCandidateZones(QgisTestCase):

    def test_candidates_reach_one_zone_wider_than_the_arithmetic(self):

        # 4-5E sits in 32V, but plain 6-degree arithmetic says zone 31.
        # The candidate list has to contain 32 or the cell covering
        # that ground could never be found.
        self.assertIn(
            32,
            utm_candidate_zones(4.0, 5.0)
        )


    def test_candidates_stay_inside_1_to_60(self):

        self.assertEqual(min(utm_candidate_zones(-180.0, -179.0)), 1)
        self.assertEqual(max(utm_candidate_zones(179.0, 180.0)), 60)


class TestDrawnGrid(QgisTestCase):

    """
    The generated GZD layer itself - the thing that was actually
    wrong. Every assertion here failed before 2026-08-17.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )


    def _cells(self, extent):

        layer = UTMGridGenerator().generate(extent)

        return {
            feature["GZD"]: feature.geometry().boundingBox()
            for feature in layer.getFeatures()
        }


    def test_norway_band_v_is_split_3_and_9_degrees(self):

        cells = self._cells(QgsRectangle(-1.0, 57.0, 13.0, 63.0))

        self.assertIn("31V", cells)
        self.assertIn("32V", cells)

        self.assertAlmostEqual(cells["31V"].xMinimum(), 0.0)
        self.assertAlmostEqual(cells["31V"].xMaximum(), 3.0)

        self.assertAlmostEqual(cells["32V"].xMinimum(), 3.0)
        self.assertAlmostEqual(cells["32V"].xMaximum(), 12.0)


    def test_a_map_wholly_inside_the_widened_32v_still_finds_it(self):

        # The regression the widened candidate sweep exists for: this
        # extent's own arithmetic says zone 31, and 31V does not reach
        # it. Before the fix this drew a 6-degree "31V" over ground
        # that belongs to 32V.
        cells = self._cells(QgsRectangle(4.0, 58.0, 5.0, 59.0))

        self.assertIn("32V", cells)
        self.assertNotIn("31V", cells)


    def test_svalbard_band_x_omits_32x_34x_and_36x(self):

        cells = self._cells(QgsRectangle(-1.0, 73.0, 43.0, 83.0))

        for zone, band in ABSENT:

            with self.subTest(cell=f"{zone}{band}"):

                self.assertNotIn(f"{zone}{band}", cells)


    def test_svalbard_band_x_widens_the_four_that_remain(self):

        cells = self._cells(QgsRectangle(-1.0, 73.0, 43.0, 83.0))

        for zone in (31, 33, 35, 37):

            expected = EXPECTED_BOUNDS[(zone, "X")]

            with self.subTest(cell=f"{zone}X"):

                self.assertIn(f"{zone}X", cells)

                self.assertAlmostEqual(cells[f"{zone}X"].xMinimum(), expected[0])
                self.assertAlmostEqual(cells[f"{zone}X"].xMaximum(), expected[1])


    def test_an_ordinary_area_is_untouched_by_any_of_this(self):

        # Tanzania - the extent the rest of the grid tests use. Plain
        # 6-degree cells, no exception anywhere near.
        cells = self._cells(QgsRectangle(39.0, -7.0, 39.5, -6.5))

        self.assertIn("37M", cells)

        self.assertAlmostEqual(cells["37M"].xMinimum(), 36.0)
        self.assertAlmostEqual(cells["37M"].xMaximum(), 42.0)


    def test_the_drawn_grid_agrees_with_the_mgrs_engine(self):

        # The real defect was a DISAGREEMENT: mgrs_engine.py applied
        # the exceptions and the drawn grid did not, so the same point
        # got two different zone designators depending on which part of
        # the plugin you asked. These points each sit in a cell whose
        # zone differs from plain arithmetic.
        converter = MGRSConverter(precision=5)

        for latitude, longitude, expected_gzd in (
            (58.0, 4.5, "32V"),
            (58.0, 1.0, "31V"),
            (75.0, 5.0, "31X"),
            (75.0, 15.0, "33X"),
            (75.0, 25.0, "35X"),
            (75.0, 38.0, "37X"),
        ):

            with self.subTest(point=(latitude, longitude)):

                mgrs = converter.format(
                    converter.convert(latitude, longitude)
                )

                self.assertTrue(
                    mgrs.startswith(expected_gzd),
                    f"engine gave {mgrs}, expected it to start {expected_gzd}"
                )

                cells = self._cells(
                    QgsRectangle(
                        longitude - 0.1,
                        latitude - 0.1,
                        longitude + 0.1,
                        latitude + 0.1
                    )
                )

                self.assertEqual(
                    list(cells),
                    [expected_gzd]
                )


class TestGridPositionDiagram(QgisTestCase):

    """
    layout/grid_position.py carried its own copy of the same
    arithmetic, so the grid-position diagram printed on every layout
    had the defect independently of the grid layer.
    """

    def test_required_zones_takes_the_band_into_account(self):

        extent = QgsRectangle(4.0, 58.0, 5.0, 59.0)

        self.assertEqual(_required_zones(extent, "V"), [32])

        # The same longitudes one band south are ordinary ground.
        self.assertEqual(_required_zones(extent, "U"), [31])


    def test_required_zones_skips_a_band_x_zone_that_does_not_exist(self):

        # 10-11E in band X is covered by the widened 33X; 32X, which
        # plain arithmetic would name, is not a cell at all.
        self.assertEqual(
            _required_zones(QgsRectangle(10.0, 74.0, 11.0, 75.0), "X"),
            [33]
        )


class TestPerCellLabelOffsetThreshold(QgisTestCase):

    """
    The GZD label's offset/centred switch used to fire at one global
    scale (3,000,000) for every cell in the world. It now reads each
    cell's own HALF_MIN_M. A single number cannot be right once cells
    range from 3 degrees wide to 12, and a 6-degree cell's ground
    width falls tenfold between the equator and band X.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        self.manager = GridLabelManager()


    def test_half_extent_is_measured_at_the_narrow_poleward_edge(self):

        # A cell narrows towards the pole, and the label is nudged
        # towards the pole - so measuring at the centroid would
        # overstate the room actually available.
        poleward = _minimum_half_extent_m(0.0, 6.0, 72.0, 84.0)
        equatorward = _minimum_half_extent_m(0.0, 6.0, 0.0, 8.0)

        self.assertLess(poleward, equatorward)


    def test_a_narrow_cell_gets_a_tighter_threshold_than_a_wide_one(self):

        layer = UTMGridGenerator().generate(
            QgsRectangle(-1.0, 57.0, 13.0, 63.0)
        )

        half = {
            feature["GZD"]: feature["HALF_MIN_M"]
            for feature in layer.getFeatures()
        }

        # 31V is 3 degrees wide, 32V is 9 - so 31V must switch to a
        # centred label while still more zoomed in than 32V does.
        self.assertLess(half["31V"], half["32V"])


    def test_the_threshold_expression_evaluates_per_feature(self):

        from qgis.core import QgsExpression, QgsExpressionContext
        from qgis.core import QgsExpressionContextUtils

        layer = UTMGridGenerator().generate(
            QgsRectangle(-1.0, 57.0, 13.0, 63.0)
        )

        expression = QgsExpression(
            self.manager._offset_max_scale_expression()
        )

        thresholds = {}

        for feature in layer.getFeatures():

            context = QgsExpressionContext()
            context.appendScopes(
                QgsExpressionContextUtils.globalProjectLayerScopes(layer)
            )
            context.setFeature(feature)

            value = expression.evaluate(context)

            self.assertFalse(
                expression.hasEvalError(),
                expression.evalErrorString()
            )

            thresholds[feature["GZD"]] = value

        self.assertLess(thresholds["31V"], thresholds["32V"])

        # The offset must still fit: at its own threshold scale, the
        # 12mm nudge lands inside the cell's half-extent with the
        # documented margin to spare.
        for gzd, scale in thresholds.items():

            with self.subTest(cell=gzd):

                offset_ground_m = (
                    self.manager.GZD_LABEL_OFFSET_MM / 1000.0
                ) * scale

                half_min = next(
                    f["HALF_MIN_M"]
                    for f in layer.getFeatures()
                    if f["GZD"] == gzd
                )

                self.assertAlmostEqual(
                    offset_ground_m,
                    half_min * self.manager.GZD_OFFSET_SAFE_FRACTION,
                    places=6
                )


    def test_a_layer_without_the_field_falls_back_to_the_old_constant(self):

        # A "UTM Grid" layer from a project saved before HALF_MIN_M
        # existed must keep working, with exactly the behaviour it
        # already had. Referencing a missing column is an evaluation
        # ERROR rather than a null, so coalesce() cannot rescue it -
        # get this wrong and such a layer loses its GZD label
        # entirely, since both rules then filter to false.
        from qgis.core import QgsVectorLayer

        legacy = QgsVectorLayer(
            "Polygon?crs=EPSG:4326&field=GZD:string",
            "UTM Grid",
            "memory"
        )

        self.assertEqual(
            self.manager._offset_max_scale_expression(legacy),
            str(self.manager.GZD_OFFSET_FALLBACK_SCALE)
        )

        self.manager.apply_label(legacy, "GZD")

        expressions = [
            rule.filterExpression()
            for rule in legacy.labeling().rootRule().children()
        ]

        self.assertIn(
            f"@map_scale < {self.manager.GZD_OFFSET_FALLBACK_SCALE}",
            expressions
        )
