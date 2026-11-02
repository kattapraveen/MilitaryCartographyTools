# -*- coding: utf-8 -*-

"""
Tests for the three terrain tools that became Processing algorithms
alongside Contours on 2026-10-26 - Tanaka Contours, Hypsometric Tint
and Hillshade Combinations.

Replaces test_tanaka_dialog.py, test_hypsometric_tint_dialog.py and
test_hillshade_combination_dialog.py. The generators themselves are
covered by test_tanaka_contours.py, test_hypsometric_tint.py and
test_hillshade_combination.py, so what is tested here is the
Processing front end - and in particular the three behaviours that
had to survive the move: an empty extent still means the whole DEM,
re-running still replaces the layer instead of piling another one
up, and the replacement still lands where the user had dragged the
old one.

Note every algorithm here is given its DEM by PATH, never as a layer
object held on the test case. A refusal's traceback keeps the
parameters dict alive, and a Python-owned QgsRasterLayer still
reachable when QGIS shuts its GDAL providers down segfaults in
GDALClose - confirmed on QGIS 3.44 on 2026-10-26, well after the
suite had reported OK.

Military Cartography Tools
"""

import os

import processing

from qgis.core import (
    QgsApplication,
    QgsProcessing,
    QgsProcessingContext,
    QgsProcessingFeedback,
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
from MilitaryCartographyTools.algorithms.hillshade_combination import (
    PRESETS,
)
from MilitaryCartographyTools.algorithms.tanaka_contours import (
    DEFAULT_STYLE_INDEX,
    STYLE_MODES,
)
from MilitaryCartographyTools.terrain.hillshade_combination import (
    generate_hillshade_combination,
    THREE_DIRECTION_AZIMUTHS,
    TWO_DIRECTION_AZIMUTHS,
)
from MilitaryCartographyTools.terrain.hypsometric_tint import (
    generate_hypsometric_tint,
)
from MilitaryCartographyTools.terrain.tanaka_contours import (
    DEFAULT_STYLE_MODE,
    STYLE_ILLUMINATED_OVERLAY,
)


class _TerrainAlgorithmTestCase(QgisTestCase):

    ALGORITHM = None

    def setUp(self):

        super().setUp()

        # Held on self: the registry does not keep a Python provider
        # alive, and a collected one fails later with "Error creating
        # algorithm from createInstance()".
        self.provider = MilitaryCartographyProvider()

        QgsApplication.processingRegistry().addProvider(self.provider)

        self.dem_path = build_synthetic_cone_dem(
            width=60,
            height=60,
            pixel_size=0.0006,
            peak_elevation=1200.0,
            slope_per_pixel=14.0
        )

    def tearDown(self):

        QgsApplication.processingRegistry().removeProvider(self.provider)

        try:
            os.remove(self.dem_path)
        except OSError:
            pass

        super().tearDown()

    def _dem_extent(self):

        """
        The DEM's own extent, read from a layer that is released
        again straight away - see this module's docstring for why
        one is never kept around.
        """

        return QgsRasterLayer(self.dem_path, "dem").extent()

    def _run(self, **overrides):

        import processing

        parameters = dict(self.DEFAULTS)
        parameters["INPUT"] = self.dem_path
        parameters["OUTPUT"] = QgsProcessing.TEMPORARY_OUTPUT

        parameters.update(overrides)

        return processing.run(
            f"{PROVIDER_ID}:{self.ALGORITHM}", parameters
        )["OUTPUT"]


class TestTanakaContoursAlgorithm(_TerrainAlgorithmTestCase):

    ALGORITHM = "tanakacontours"

    DEFAULTS = {
        "EXTENT": None,
        "INTERVAL": 100.0,
        "SEGMENT_LENGTH": 60.0,
        "AZIMUTH": 315.0,
        "MIN_WIDTH": 0.15,
        "MAX_WIDTH": 0.6,
        "STYLE_MODE": DEFAULT_STYLE_INDEX,
        "REPLACE": True,
    }

    def _layer(self, **overrides):

        result = self._run(**overrides)

        if isinstance(result, str):
            return QgsVectorLayer(result, "out", "ogr")

        return result

    def test_it_produces_illuminated_segments(self):

        layer = self._layer()

        self.assertTrue(layer.isValid())
        self.assertGreater(layer.featureCount(), 0)

        self.assertIn("ILLUM", [field.name() for field in layer.fields()])

    def test_an_empty_extent_means_the_whole_dem(self):

        self.assertEqual(
            self._layer(EXTENT=None).featureCount(),
            self._layer(EXTENT=self._dem_extent()).featureCount()
        )

    def test_a_narrowed_extent_produces_less(self):

        extent = self._dem_extent()

        quarter = QgsRectangle(
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMinimum() + extent.width() / 2.0,
            extent.yMinimum() + extent.height() / 2.0
        )

        self.assertLess(
            self._layer(EXTENT=quarter).featureCount(),
            self._layer(EXTENT=None).featureCount()
        )

    def test_the_style_options_are_the_ones_the_dialog_offered(self):

        self.assertEqual(
            [mode for _, mode in STYLE_MODES],
            [
                "elevation_color",
                "monochrome",
                "illuminated_overlay",
            ]
        )

    def test_the_default_style_index_points_at_the_default_mode(self):

        """
        The guard against the options list being reordered and the
        default silently becoming a different style.
        """

        self.assertEqual(
            STYLE_MODES[DEFAULT_STYLE_INDEX][1],
            DEFAULT_STYLE_MODE
        )

    def test_illuminated_overlay_warns_when_there_is_no_tint_to_sit_on(self):

        """
        Carried over from the dialog. Non-blocking: the layer is
        still useful, the mode just looks like nothing without a
        Hypsometric Tint underneath.
        """

        from qgis.core import QgsProcessingFeedback

        class RecordingFeedback(QgsProcessingFeedback):

            def __init__(self):
                super().__init__()
                self.warnings = []

            def pushWarning(self, warning):
                self.warnings.append(warning)

        import processing

        feedback = RecordingFeedback()

        overlay = [
            mode for _, mode in STYLE_MODES
        ].index(STYLE_ILLUMINATED_OVERLAY)

        parameters = dict(self.DEFAULTS)
        parameters["INPUT"] = self.dem_path
        parameters["OUTPUT"] = QgsProcessing.TEMPORARY_OUTPUT
        parameters["STYLE_MODE"] = overlay

        processing.run(
            f"{PROVIDER_ID}:tanakacontours",
            parameters,
            feedback=feedback
        )

        self.assertTrue(
            any("Hypsometric Tint" in warning for warning in feedback.warnings)
        )

    def test_the_overlay_warning_reads_the_contexts_own_project(self):

        """
        processAlgorithm() runs on a background thread, so the layer
        registry it looks in has to be the context's, not the GUI
        thread's QgsProject.instance().

        The two are given DIFFERENT contents here to tell them apart:
        a Hypsometric Tint exists in QgsProject.instance() and not in
        the context's project, so a run that warns is reading the
        context and a run that stays quiet is reading the singleton.
        """

        from qgis.core import QgsProcessingFeedback

        class RecordingFeedback(QgsProcessingFeedback):

            def __init__(self):
                super().__init__()
                self.warnings = []

            def pushWarning(self, warning):
                self.warnings.append(warning)

        import processing

        tint = QgsVectorLayer(
            "Point?crs=EPSG:4326", "Hypsometric Tint", "memory"
        )

        QgsProject.instance().addMapLayer(tint)

        overlay = [
            mode for _, mode in STYLE_MODES
        ].index(STYLE_ILLUMINATED_OVERLAY)

        parameters = dict(self.DEFAULTS)
        parameters["INPUT"] = self.dem_path
        parameters["OUTPUT"] = QgsProcessing.TEMPORARY_OUTPUT
        parameters["STYLE_MODE"] = overlay

        feedback = RecordingFeedback()

        # The project is created FIRST and deleted LAST on purpose.
        # QgsProcessingContext holds a bare pointer to it, so the
        # context has to go while the project is still alive - the
        # same rule that made QgsProcessingMultiStepFeedback
        # unusable here. See terrain/_progress.py.
        other_project = QgsProject()

        context = QgsProcessingContext()
        context.setProject(other_project)

        try:
            processing.run(
                f"{PROVIDER_ID}:tanakacontours",
                parameters,
                feedback=feedback,
                context=context
            )

        finally:
            del context

        self.assertTrue(
            any(
                "Hypsometric Tint" in warning
                for warning in feedback.warnings
            ),
            "the warning was suppressed, so the layer registry read "
            "was QgsProject.instance() and not context.project()"
        )


class TestHypsometricTintAlgorithm(_TerrainAlgorithmTestCase):

    ALGORITHM = "hypsometrictint"

    DEFAULTS = {
        "EXTENT": None,
        "OPACITY": 100,
        "DISCRETE": False,
        "REPLACE": True,
    }

    def test_it_produces_a_readable_raster(self):

        written = self._run()

        layer = QgsRasterLayer(written, "tint")

        self.assertTrue(layer.isValid())
        self.assertGreater(layer.width(), 0)

    def test_an_empty_extent_means_the_whole_dem(self):

        whole = QgsRasterLayer(self._run(EXTENT=None), "whole")

        explicit = QgsRasterLayer(
            self._run(EXTENT=self._dem_extent()), "explicit"
        )

        self.assertEqual(whole.width(), explicit.width())
        self.assertEqual(whole.height(), explicit.height())

    def test_a_narrowed_extent_produces_a_smaller_raster(self):

        extent = self._dem_extent()

        quarter = QgsRectangle(
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMinimum() + extent.width() / 2.0,
            extent.yMinimum() + extent.height() / 2.0
        )

        self.assertLess(
            QgsRasterLayer(self._run(EXTENT=quarter), "part").width(),
            QgsRasterLayer(self._run(EXTENT=None), "whole").width()
        )


class TestHillshadeCombinationAlgorithm(_TerrainAlgorithmTestCase):

    ALGORITHM = "hillshadecombination"

    DEFAULTS = {
        "EXTENT": None,
        "PRESET": 1,
        "ALTITUDE": 45.0,
        "Z_FACTOR": 1.0,
        "OPACITY": 100,
        "REPLACE": True,
    }

    def test_it_produces_a_readable_raster(self):

        layer = QgsRasterLayer(self._run(), "hillshade")

        self.assertTrue(layer.isValid())
        self.assertGreater(layer.width(), 0)

    def test_both_light_direction_presets_are_offered(self):

        self.assertEqual(
            [azimuths for _, azimuths in PRESETS],
            [TWO_DIRECTION_AZIMUTHS, THREE_DIRECTION_AZIMUTHS]
        )

    def test_either_preset_produces_a_raster(self):

        for index in range(len(PRESETS)):

            with self.subTest(preset=PRESETS[index][0]):

                layer = QgsRasterLayer(self._run(PRESET=index), "hs")

                self.assertTrue(layer.isValid())

    def test_an_empty_extent_means_the_whole_dem(self):

        whole = QgsRasterLayer(self._run(EXTENT=None), "whole")

        explicit = QgsRasterLayer(
            self._run(EXTENT=self._dem_extent()), "explicit"
        )

        self.assertEqual(whole.width(), explicit.width())


class TestReplacementKeepsThePlaceTheUserPutItIn(QgisTestCase):

    """
    The second half of replace-in-place, and the easier one to drop
    on the way to Processing. A Processing output lands at the top of
    the Layers panel; a layer the user has dragged somewhere else has
    to come back where they left it, or the plugin reads as ignoring
    how they have organised the project.
    """

    LAYER_NAME = "Combined Hillshade"

    def _layer(self, name):

        layer = QgsVectorLayer(
            "LineString?crs=EPSG:4326", name, "memory"
        )

        QgsProject.instance().addMapLayer(layer)

        return layer

    def _bottom_of_tree(self, project, layer):

        root = project.layerTreeRoot()

        root.insertLayer(len(root.children()), layer)

    def _post_process(self, layer, replace=True):

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        StyleAndReplacePostProcessor.create(
            self.LAYER_NAME, None, replace, self._bottom_of_tree
        ).postProcessLayer(layer, context, None)

        self._settle()

    def _settle(self):

        """
        Let the event loop turn before anything is asserted.

        Not a flourish. QgsLayerTreeRegistryBridge drops a layer that
        has lost its last tree node from the project on the NEXT turn
        of the event loop, not there and then, so a post-processor
        that mishandles the tree looks perfectly healthy to a
        unittest and loses the layer in the real QGIS. That is
        exactly what shipped on 2026-10-26 and was only found by
        driving the real Processing dialog on 2026-11-02. Every
        assertion in this class has to be made on the far side of
        this call.
        """

        QCoreApplication.processEvents()

    def _names_in_tree(self):

        root = QgsProject.instance().layerTreeRoot()

        return [
            node.layer().name()
            for node in root.children()
            if node.layer() is not None
        ]

    def test_the_replacement_takes_the_old_layers_position(self):

        self._layer("Above")
        self._layer(self.LAYER_NAME)
        self._layer("Below")

        before = self._names_in_tree()

        self.assertEqual(before.index(self.LAYER_NAME), 1)

        fresh = self._layer(self.LAYER_NAME)

        self._post_process(fresh)

        after = self._names_in_tree()

        self.assertEqual(after, before)
        self.assertEqual(len(after), 3)

    def test_the_replacement_appears_exactly_once_in_the_tree(self):

        """
        Processing has already given the new layer a node by the time
        the post-processor runs, so repositioning has to MOVE that
        node. Inserting without detaching leaves the same layer in
        the panel twice.
        """

        self._layer(self.LAYER_NAME)

        fresh = self._layer(self.LAYER_NAME)

        self._post_process(fresh)

        self.assertEqual(
            self._names_in_tree().count(self.LAYER_NAME), 1
        )

    def test_with_nothing_to_replace_it_takes_the_default_position(self):

        self._layer("Already here")

        fresh = self._layer(self.LAYER_NAME)

        self._post_process(fresh)

        # Bottom of the tree, per the placement passed in - not the
        # top, where Processing dropped it.
        self.assertEqual(self._names_in_tree()[-1], self.LAYER_NAME)

    def test_the_layer_is_still_there_once_the_event_loop_turns(self):

        """
        The regression test for the bug that made every terrain tool
        appear to do nothing: the run reported success, wrote its
        output, and added no layer.

        Repositioning used to drop Processing's node first and insert
        the replacement after. Between those two the layer had no
        node at all, which is the one state QgsLayerTreeRegistryBridge
        reacts to - it removes such a layer from the project, on the
        next turn of the event loop, and re-inserting a node in the
        same breath does not call it off.
        """

        self._layer("Above")
        self._layer(self.LAYER_NAME)
        self._layer("Below")

        fresh = self._layer(self.LAYER_NAME)
        fresh_id = fresh.id()

        self._post_process(fresh)

        self.assertIn(
            fresh_id,
            QgsProject.instance().mapLayers(),
            "the replacement was dropped from the project"
        )

        self.assertEqual(
            self._names_in_tree().count(self.LAYER_NAME), 1
        )

    def test_add_as_new_also_takes_the_default_position(self):

        """
        The "keep the existing one" path. There is no previous
        position to inherit, so this feature's own default placement
        applies - otherwise a raster fill lands on top and hides the
        map.
        """

        existing = self._layer(self.LAYER_NAME)

        self._layer("Already here")

        fresh = self._layer(self.LAYER_NAME)

        self._post_process(fresh, replace=False)

        names = self._names_in_tree()

        self.assertEqual(names.count(self.LAYER_NAME), 2)
        self.assertIn(existing.id(), QgsProject.instance().mapLayers())


class TestWhatTheChildAlgorithmsAreGiven(_TerrainAlgorithmTestCase):

    """
    These generators do almost none of their own work: they delegate
    to gdal:warpreproject, gdal:contour, native:splitlinesbylength,
    gdal:hillshade, gdal:rastercalculator and gdal:translate. What
    they hand those children decides two separate things, and both
    were wrong after the 2026-10-26 conversion.

    **The feedback decides whether Cancel works**, which was the
    whole reason for the conversion - "a progress bar and a working
    Cancel, which was the whole complaint". No child was given it,
    so pressing Cancel did nothing until the run finished of its own
    accord; the algorithms only looked at isCanceled() between
    stages, and the stages are where the time goes. Fixing either
    half alone leaves Cancel broken, so both are tested: the
    feedback has to reach the children, and a cancelled run has to
    stop quietly rather than raise or hand back half a layer.

    **The context decides whether the run is thread-safe.** A child
    run without one calls dataobjects.createContext(), which reads
    QgsProject.instance() and QgsSettings() - GUI-thread objects -
    from the background thread the algorithm runs on.
    """

    ALGORITHM = "hypsometrictint"

    DEFAULTS = {
        "OPACITY": 1.0,
        "DISCRETE": False,
        "REPLACE": True,
    }

    def test_every_child_algorithm_is_given_the_parents_feedback(self):

        """
        The half that makes Cancel possible at all. A child that was
        never handed the feedback cannot learn it has been cancelled,
        however often the parent checks.
        """

        import processing

        real_run = processing.run

        seen = []

        def recording_run(*args, **kwargs):
            seen.append(kwargs.get("feedback"))
            return real_run(*args, **kwargs)

        feedback = QgsProcessingFeedback()

        processing.run = recording_run

        try:
            # The hillshade blend deliberately, not the tint: it runs
            # four children (the warp, one gdal:hillshade per azimuth,
            # then the average), so this also covers the generators
            # with more than one heavy step - the only ones a
            # multi-step feedback would ever be reintroduced for.
            generate_hillshade_combination(
                QgsRasterLayer(self.dem_path, "dem"),
                self._dem_extent(),
                QgsRasterLayer(self.dem_path, "dem").crs(),
                azimuths=TWO_DIRECTION_AZIMUTHS,
                feedback=feedback
            )

        finally:
            processing.run = real_run

        self.assertGreater(
            len(seen), 1, "the generator ran no child algorithm"
        )

        # The parent's own feedback object, not a wrapper around it.
        # A QgsProcessingMultiStepFeedback would give a nicer bar and
        # segfaults on the next turn of the event loop - see
        # terrain/_progress.py.
        for given in seen:
            self.assertIs(given, feedback)

    def test_every_child_algorithm_is_given_the_parents_context(self):

        """
        The same contract as the feedback above, for the same reason
        in reverse. A child run without a context calls
        `dataobjects.createContext()`, which reads
        `QgsProject.instance()` and `QgsSettings()` - both GUI-thread
        objects - from the worker thread the algorithm runs on.
        """

        import processing

        real_run = processing.run

        seen = []

        def recording_run(*args, **kwargs):
            seen.append(kwargs.get("context"))
            return real_run(*args, **kwargs)

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        processing.run = recording_run

        try:
            generate_hillshade_combination(
                QgsRasterLayer(self.dem_path, "dem"),
                self._dem_extent(),
                QgsRasterLayer(self.dem_path, "dem").crs(),
                azimuths=TWO_DIRECTION_AZIMUTHS,
                context=context
            )

        finally:
            processing.run = real_run

        self.assertGreater(
            len(seen), 1, "the generator ran no child algorithm"
        )

        for given in seen:
            self.assertIs(given, context)

    def test_the_generators_still_work_with_no_context(self):

        """
        `context` has to stay optional. Line of Sight, Viewshed and
        Sensor Coverage still call these generators from plain
        dialogs on the main thread, where there is no
        QgsProcessingContext to hand over, and the fallback to
        QgsProject.instance() is correct there.
        """

        tint = generate_hypsometric_tint(
            QgsRasterLayer(self.dem_path, "dem"),
            self._dem_extent(),
            QgsRasterLayer(self.dem_path, "dem").crs()
        )

        self.assertIsNotNone(tint)
        self.assertTrue(tint.isValid())

    def test_a_cancelled_run_stops_quietly(self):

        """
        The other half. A cancellation is not a failure and not a
        refusal: nothing is raised, and no half-built output is
        handed back for the post-processor to load.
        """

        feedback = QgsProcessingFeedback()

        feedback.cancel()

        results = processing.run(
            f"{PROVIDER_ID}:{self.ALGORITHM}",
            {
                "INPUT": self.dem_path,
                "EXTENT": None,
                "OPACITY": 1.0,
                "DISCRETE": False,
                "REPLACE": True,
                "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
            },
            feedback=feedback
        )

        self.assertNotIn("OUTPUT", results)

    def test_a_cancelled_generator_returns_none(self):

        """
        The contract every caller relies on, stated once here so it
        cannot drift: cancelled means None, not an exception and not
        an empty layer.
        """

        feedback = QgsProcessingFeedback()

        feedback.cancel()

        self.assertIsNone(
            generate_hypsometric_tint(
                QgsRasterLayer(self.dem_path, "dem"),
                self._dem_extent(),
                QgsRasterLayer(self.dem_path, "dem").crs(),
                feedback=feedback
            )
        )


class TestThePostProcessorCannotTakeTheLayersPanelDown(QgisTestCase):

    """
    `handleAlgorithmResults` calls every post-processor between
    `setUpdatesEnabled(False)` and `setUpdatesEnabled(True)`, and
    that loop is not wrapped in try/except. An exception leaving
    postProcessLayer() therefore skips the re-enable and the Layers
    panel stops repainting for the rest of the QGIS session, making
    every later algorithm look as though it did nothing too.

    The registry is tested here as well, because both live in
    postProcessLayer()'s own try/finally and a change to one can
    easily break the other.
    """

    LAYER_NAME = "Combined Hillshade"

    def setUp(self):

        super().setUp()

        StyleAndReplacePostProcessor._instances = []

    def _layer(self):

        layer = QgsVectorLayer(
            "LineString?crs=EPSG:4326", self.LAYER_NAME, "memory"
        )

        QgsProject.instance().addMapLayer(layer)

        return layer

    def _context(self):

        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())

        return context

    @staticmethod
    def _throwing_style(_loaded):
        raise RuntimeError("band statistics unavailable")

    def test_a_failing_style_is_reported_rather_than_raised(self):

        class RecordingFeedback(QgsProcessingFeedback):

            def __init__(self):
                super().__init__()
                self.errors = []

            def reportError(self, error, fatalError=False):
                self.errors.append(error)

        feedback = RecordingFeedback()

        processor = StyleAndReplacePostProcessor.create(
            self.LAYER_NAME, self._throwing_style, True, None
        )

        # Must not raise.
        processor.postProcessLayer(self._layer(), self._context(), feedback)

        self.assertTrue(
            any(
                "could not be styled" in error
                for error in feedback.errors
            ),
            "the failure was swallowed instead of reported"
        )

        self.assertTrue(
            any(
                "band statistics unavailable" in error
                for error in feedback.errors
            ),
            "the report did not name the underlying cause"
        )

    def test_with_no_feedback_a_failure_is_re_raised(self):

        """
        The negative control, and the reason the guard cannot be a
        bare `except: pass`. A direct call has nobody to report to,
        so the failure has to surface - otherwise this guard would
        hide the next bug of the kind it was added for.
        """

        processor = StyleAndReplacePostProcessor.create(
            self.LAYER_NAME, self._throwing_style, True, None
        )

        with self.assertRaises(RuntimeError):
            processor.postProcessLayer(self._layer(), self._context(), None)

    def test_the_registry_holds_the_instance_until_it_has_run(self):

        """
        The registry is not optional: measured on 2026-11-03, once
        the last Python reference goes the subclass is collected and
        what the context hands back is a bare
        QgsProcessingLayerPostProcessorInterface, whose
        postProcessLayer() does nothing at all.
        """

        processor = StyleAndReplacePostProcessor.create(
            self.LAYER_NAME, None, True, None
        )

        self.assertIn(processor, StyleAndReplacePostProcessor._instances)

    def test_the_registry_does_not_grow_across_runs(self):

        """
        These tools are used by re-running them - that is what
        replace-in-place is for - so an entry per run is an unbounded
        leak over a session.
        """

        for _ in range(5):

            processor = StyleAndReplacePostProcessor.create(
                self.LAYER_NAME, None, True, None
            )

            processor.postProcessLayer(
                self._layer(), self._context(), None
            )

        self.assertEqual(StyleAndReplacePostProcessor._instances, [])

    def test_a_failed_run_is_still_dropped_from_the_registry(self):

        """
        The pruning is in a `finally`, so a post-processor that threw
        does not stay behind for the session either.
        """

        processor = StyleAndReplacePostProcessor.create(
            self.LAYER_NAME, self._throwing_style, True, None
        )

        with self.assertRaises(RuntimeError):
            processor.postProcessLayer(self._layer(), self._context(), None)

        self.assertEqual(StyleAndReplacePostProcessor._instances, [])
