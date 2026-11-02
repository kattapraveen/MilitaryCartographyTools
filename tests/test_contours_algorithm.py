# -*- coding: utf-8 -*-

"""
Tests for algorithms/contours.py - Contours as a Processing
algorithm.

Replaces the old test_contours_dialog.py. The tool was a plain
dialog until 2026-10-26; it moved to Processing as task 7's option C,
for the progress bar and working Cancel that brings. The geometry and
the guards still live in terrain/contours.py and are covered by
test_contours.py - what is tested here is the Processing front end,
and in particular the two behaviours that had to survive the move:
an empty extent still means the whole DEM, and re-running still
replaces the layer instead of piling another one up.

Military Cartography Tools
"""

import os

from unittest.mock import patch

from qgis.core import (
    QgsApplication,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QCoreApplication

from .qgis_test_case import build_synthetic_cone_dem, QgisTestCase

from MilitaryCartographyTools.algorithms import (
    MilitaryCartographyProvider,
    PROVIDER_ID,
)
from MilitaryCartographyTools.algorithms._replace_in_place import (
    StyleAndReplacePostProcessor,
)
from MilitaryCartographyTools.terrain import contours as contours_module
from MilitaryCartographyTools.terrain.contours import (
    ELEVATION_FIELD,
    OUTPUT_LAYER_NAME,
)


ALGORITHM = f"{PROVIDER_ID}:contours"


class _ContoursAlgorithmTestCase(QgisTestCase):

    def setUp(self):

        super().setUp()

        # Held on self: the registry does not keep a Python provider
        # alive, and a collected one fails later with "Error creating
        # algorithm from createInstance()".
        self.provider = MilitaryCartographyProvider()

        QgsApplication.processingRegistry().addProvider(self.provider)

        self._dem_path = build_synthetic_cone_dem(
            width=100,
            height=100,
            pixel_size=0.00035,
            peak_elevation=1200.0,
            slope_per_pixel=8.0
        )

        self.dem = QgsRasterLayer(self._dem_path, "cone")


    def tearDown(self):

        QgsApplication.processingRegistry().removeProvider(self.provider)

        self.dem = None

        try:
            os.remove(self._dem_path)
        except OSError:
            pass

        super().tearDown()


    def _run(self, **overrides):

        import processing

        # The DEM goes in by PATH, not as the layer object held on
        # self. A refusal's traceback keeps this dict alive, and a
        # Python-owned QgsRasterLayer still reachable when QGIS shuts
        # its GDAL providers down segfaults in GDALClose - confirmed
        # on QGIS 3.44 on 2026-10-26, after the suite had already
        # reported OK. By path, Processing loads its own copy into
        # the context, which owns and releases it.
        parameters = {
            "INPUT": self._dem_path,
            "EXTENT": None,
            "INTERVAL": 50.0,
            "INDEX_EVERY": 5,
            "COLOUR": "#8a5a2b",
            "REPLACE": True,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }

        parameters.update(overrides)

        result = processing.run(ALGORITHM, parameters)["OUTPUT"]

        if isinstance(result, str):
            return QgsVectorLayer(result, "out", "ogr")

        return result


class TestTheAlgorithmProducesContours(_ContoursAlgorithmTestCase):

    def test_it_draws_contours_at_the_requested_interval(self):

        layer = self._run(INTERVAL=50.0)

        self.assertTrue(layer.isValid())
        self.assertGreater(layer.featureCount(), 0)

        for feature in layer.getFeatures():

            with self.subTest(elevation=feature[ELEVATION_FIELD]):
                self.assertAlmostEqual(
                    feature[ELEVATION_FIELD] % 50.0, 0.0, places=6
                )


    def test_an_empty_extent_means_the_whole_dem(self):

        """
        What the old dialog defaulted to, and what every caller
        before the move expected.
        """

        whole = self._run(EXTENT=None)

        explicit = self._run(EXTENT=self.dem.extent())

        self.assertEqual(whole.featureCount(), explicit.featureCount())


    def test_a_narrowed_extent_produces_less(self):

        extent = self.dem.extent()

        quarter = QgsRectangle(
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMinimum() + extent.width() / 2.0,
            extent.yMinimum() + extent.height() / 2.0
        )

        self.assertLess(
            self._run(EXTENT=quarter).featureCount(),
            self._run(EXTENT=None).featureCount()
        )


    def test_a_refusal_becomes_a_processing_exception(self):

        """
        terrain/contours.py raises ValueError with a message written
        for the user. Processing shows a QgsProcessingException
        properly, so it must be translated rather than escaping as a
        traceback.
        """

        with patch.object(contours_module, "MAX_CONTOUR_FEATURES", 5):

            with self.assertRaises(QgsProcessingException) as raised:
                self._run()

        self.assertIn("contour lines", str(raised.exception))


class TestReplaceInPlaceSurvivedTheMove(_ContoursAlgorithmTestCase):

    """
    A Processing algorithm always emits a NEW output, but this tool
    came from a dialog that corrected the existing layer instead -
    behaviour that exists because of a real usability complaint:
    re-running used to leave a pile of stale layers behind. The
    post-processor carries it over.
    """

    def _post_process(self, layer, replace):

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        StyleAndReplacePostProcessor.create(
            OUTPUT_LAYER_NAME, None, replace
        ).postProcessLayer(layer, context, None)

        # The event loop has to turn before anything is asserted:
        # QgsLayerTreeRegistryBridge removes a layer that has lost
        # its last tree node only on the next turn, so mishandling
        # the tree is invisible to a unittest that checks straight
        # away. See test_terrain_algorithms.py's _settle().
        QCoreApplication.processEvents()


    def _named_layers(self):

        return QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)


    def test_replacing_leaves_exactly_one_layer_of_that_name(self):

        for _ in range(2):
            stale = QgsVectorLayer(
                "LineString?crs=EPSG:4326", OUTPUT_LAYER_NAME, "memory"
            )
            QgsProject.instance().addMapLayer(stale)

        fresh = QgsVectorLayer(
            "LineString?crs=EPSG:4326", OUTPUT_LAYER_NAME, "memory"
        )
        QgsProject.instance().addMapLayer(fresh)

        self.assertEqual(len(self._named_layers()), 3)

        self._post_process(fresh, replace=True)

        remaining = self._named_layers()

        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0].id(), fresh.id())


    def test_not_replacing_keeps_them_all(self):

        stale = QgsVectorLayer(
            "LineString?crs=EPSG:4326", OUTPUT_LAYER_NAME, "memory"
        )
        QgsProject.instance().addMapLayer(stale)

        fresh = QgsVectorLayer(
            "LineString?crs=EPSG:4326", OUTPUT_LAYER_NAME, "memory"
        )
        QgsProject.instance().addMapLayer(fresh)

        self._post_process(fresh, replace=False)

        self.assertEqual(len(self._named_layers()), 2)


    def test_it_never_removes_the_layer_it_was_given(self):

        fresh = QgsVectorLayer(
            "LineString?crs=EPSG:4326", OUTPUT_LAYER_NAME, "memory"
        )
        QgsProject.instance().addMapLayer(fresh)

        self._post_process(fresh, replace=True)

        self.assertEqual(len(self._named_layers()), 1)


    def test_a_layer_the_user_renamed_is_left_alone(self):

        """
        Only layers by this exact name are replaced, so something the
        user has since renamed is theirs to keep - the same rule the
        old replace_named_layer() followed.
        """

        renamed = QgsVectorLayer(
            "LineString?crs=EPSG:4326", "My contours", "memory"
        )
        QgsProject.instance().addMapLayer(renamed)

        fresh = QgsVectorLayer(
            "LineString?crs=EPSG:4326", OUTPUT_LAYER_NAME, "memory"
        )
        QgsProject.instance().addMapLayer(fresh)

        self._post_process(fresh, replace=True)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName("My contours")),
            1
        )
