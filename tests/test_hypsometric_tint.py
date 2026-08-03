# -*- coding: utf-8 -*-

"""
Tests for terrain/hypsometric_tint.py - the filled elevation-colour
raster pipeline.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsSingleBandPseudoColorRenderer,
    QgsVectorLayer,
)

from .qgis_test_case import build_synthetic_sloped_dem, QgisTestCase

from MilitaryCartographyTools.core.coordinate_utils import WGS84
from MilitaryCartographyTools.terrain._hypsometric_ramp import (
    hypsometric_color,
    LAND_RAMP,
    SEA_RAMP,
)
from MilitaryCartographyTools.terrain.hypsometric_tint import (
    _build_color_ramp_items,
    generate_hypsometric_tint,
    OUTPUT_LAYER_NAME,
)
from MilitaryCartographyTools.terrain.tanaka_contours import generate_tanaka_contours


class TestBuildColorRampItems(QgisTestCase):

    """
    _build_color_ramp_items() - converts the fraction-keyed
    SEA_RAMP/LAND_RAMP stops into absolute-elevation
    QgsColorRampShader.ColorRampItem entries, using the same
    normalisation convention as _hypsometric_ramp.hypsometric_color()
    (see tests/test_tanaka_contours.py's TestHypsometricColor, which
    covers that convention directly).
    """

    def test_inland_dataset_produces_only_land_ramp_items(self):

        items = _build_color_ramp_items(
            min_elevation=100.0,
            max_elevation=500.0
        )

        self.assertEqual(
            len(items),
            len(LAND_RAMP)
        )

        self.assertAlmostEqual(items[0].value, 100.0)
        self.assertAlmostEqual(items[-1].value, 500.0)

        self.assertEqual(
            (items[0].color.red(), items[0].color.green(), items[0].color.blue()),
            LAND_RAMP[0][1]
        )

        self.assertEqual(
            (items[-1].color.red(), items[-1].color.green(), items[-1].color.blue()),
            LAND_RAMP[-1][1]
        )


    def test_coastal_dataset_anchors_land_and_sea_at_zero(self):

        items = _build_color_ramp_items(
            min_elevation=-500.0,
            max_elevation=1000.0
        )

        self.assertEqual(
            len(items),
            len(SEA_RAMP) + len(LAND_RAMP)
        )

        values = [item.value for item in items]

        # Strictly ascending (QgsColorRampShader requires this) and
        # spanning the full min..max range.
        self.assertEqual(values, sorted(values))
        self.assertAlmostEqual(values[0], -500.0)
        self.assertAlmostEqual(values[-1], 1000.0)

        # Sea level (0) is present as an anchor point, since both
        # ramps meet there.
        self.assertIn(0.0, values)


class TestGenerateHypsometricTintIntegration(QgisTestCase):

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_sloped_dem(width=40, height=40)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _extent(self):

        return QgsRectangle(37.3402, -3.0935, 37.3428, -3.0905)


    def test_output_is_a_valid_pseudocolor_raster(self):

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        self.assertTrue(
            dem_layer.isValid()
        )

        output = generate_hypsometric_tint(
            dem_layer,
            self._extent(),
            WGS84
        )

        self.assertTrue(
            output.isValid()
        )

        self.assertEqual(
            output.name(),
            OUTPUT_LAYER_NAME
        )

        self.assertIsInstance(
            output.renderer(),
            QgsSingleBandPseudoColorRenderer
        )

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(output.id())
        )


    def test_opacity_is_applied(self):

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        output = generate_hypsometric_tint(
            dem_layer,
            self._extent(),
            WGS84,
            opacity=0.55
        )

        self.assertAlmostEqual(
            output.opacity(),
            0.55
        )


    def test_lands_at_bottom_of_layer_tree_even_with_other_layers_above(self):

        # A real bug this session: a new layer added via a plain
        # addMapLayer() ends up on TOP of the layer tree (rendered
        # last, i.e. visually in front) - which would let an opaque
        # raster cover any vector layers already in the project. The
        # tint layer must always land at the BOTTOM instead.
        dummy = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "dummy_on_top",
            "memory"
        )

        QgsProject.instance().addMapLayer(
            dummy
        )

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        generate_hypsometric_tint(
            dem_layer,
            self._extent(),
            WGS84
        )

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(
            names[-1],
            OUTPUT_LAYER_NAME
        )


class TestColorMatchesTanakaContours(QgisTestCase):

    """
    Regression coverage for a real complaint: over the same DEM and
    extent, a Tanaka Contours line and a Hypsometric Tint pixel at the
    same elevation used to come out different colours, because Tanaka
    normalised against the elevation range of its own *drawn contour
    lines* (quantised to the contour interval) while the tint
    normalised against the DEM's raw pixel range - two different
    ranges even for an identical DEM/extent. Both now share
    terrain._dem_utils.band_min_max() as the one source of truth (see
    terrain/tanaka_contours.py's _build_output_layer()).
    """

    def setUp(self):

        super().setUp()

        self._dem_path = build_synthetic_sloped_dem(width=40, height=40)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def test_tanaka_segment_color_matches_tint_at_the_same_elevation(self):

        from MilitaryCartographyTools.terrain._dem_utils import (
            band_min_max,
            clip_and_reproject_dem,
        )

        dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        extent = QgsRectangle(37.3402, -3.0935, 37.3428, -3.0905)

        tanaka = generate_tanaka_contours(
            dem_layer,
            extent,
            WGS84,
            interval=20.0,
            segment_length=5.0
        )

        # The ground truth both pipelines are meant to share - an
        # independent re-clip of the same DEM/extent, not something
        # read back out of either pipeline's own output.
        clipped_dem = clip_and_reproject_dem(dem_layer, extent, WGS84)

        min_elev, max_elev = band_min_max(clipped_dem)

        for feature in tanaka.getFeatures():

            expected = hypsometric_color(
                feature["ELEV"], min_elev, max_elev
            )

            actual = (feature["R"], feature["G"], feature["B"])

            self.assertEqual(actual, expected)
