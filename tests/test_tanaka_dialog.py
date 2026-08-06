# -*- coding: utf-8 -*-

"""
Tests for terrain/tanaka_dialog.py's generate_from_dialog_values() -
the accept-flow logic split out of show_tanaka_contour_dialog() so it
can be exercised without driving an actual modal QDialog.

Regression coverage for a real usability complaint: every run of the
dialog was creating a brand new "Tanaka Contours" layer, so tweaking
settings and re-running left a pile of stale layers behind instead of
correcting the existing one. Default behaviour now replaces the
existing layer in place; an "Add as new layer" checkbox opts back
into keeping it.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRasterLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from .qgis_test_case import (
    build_synthetic_sloped_dem,
    FakeIface,
    QgisTestCase,
    make_canvas,
)

from MilitaryCartographyTools.terrain.hypsometric_tint import (
    OUTPUT_LAYER_NAME as HYPSOMETRIC_TINT_LAYER_NAME,
)
from MilitaryCartographyTools.terrain.tanaka_contours import (
    OUTPUT_LAYER_NAME,
    STYLE_ELEVATION_COLOR,
    STYLE_ILLUMINATED_OVERLAY,
    STYLE_MONOCHROME,
)
from MilitaryCartographyTools.terrain.tanaka_dialog import generate_from_dialog_values


class TestGenerateFromDialogValues(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        self._dem_path = build_synthetic_sloped_dem()

        self.dem_layer = QgsRasterLayer(
            self._dem_path,
            "test_dem"
        )

        # generate_from_dialog_values() now clips to the DEM's own
        # full extent rather than the canvas, so the canvas's own
        # extent no longer affects generation - kept only because
        # FakeIface expects one.
        self.iface = FakeIface(canvas=make_canvas())


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _values(self, add_as_new_layer=False, style_mode=STYLE_ELEVATION_COLOR):

        return {
            "dem_layer": self.dem_layer,
            "interval": 20.0,
            "segment_length": 5.0,
            "light_azimuth_deg": 315.0,
            "min_width_mm": 0.15,
            "max_width_mm": 0.6,
            "style_mode": style_mode,
            "add_as_new_layer": add_as_new_layer,
        }


    def test_no_dem_layer_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"dem_layer": None}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_generation_uses_the_dems_own_extent_not_the_canvas(self):

        # Regression test: generation used to clip to canvas.extent(),
        # so a regenerate could silently produce a different result
        # (or nothing at all) if the view had shifted even slightly
        # since the last run. Moving the canvas somewhere completely
        # disjoint from the DEM must not affect the result at all.
        from qgis.core import QgsRectangle

        self.iface.mapCanvas().setExtent(
            QgsRectangle(100.0, 40.0, 101.0, 41.0)
        )

        result = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(result)
        self.assertGreater(result.featureCount(), 0)


    def test_default_replaces_existing_layer_rather_than_adding_another(self):

        first = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(first)

        first_id = first.id()

        second = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(second)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)

        # The old layer object was actually removed from the
        # project, not just shadowed by name.
        self.assertIsNone(
            QgsProject.instance().mapLayer(first_id)
        )


    def test_style_mode_reaches_the_generated_symbol(self):

        def stroke_color_expression(layer):

            symbol_layer = layer.renderer().symbol().symbolLayer(0)

            return symbol_layer.dataDefinedProperties().property(
                QgsSymbolLayer.Property.StrokeColor
            ).expressionString()

        # add_as_new_layer=True on both, so the second call doesn't
        # remove the first result out from under this test (default
        # replace-in-place behaviour is covered separately above).
        color_result = generate_from_dialog_values(
            self.iface,
            self._values(style_mode=STYLE_ELEVATION_COLOR, add_as_new_layer=True)
        )

        color_expression = stroke_color_expression(color_result)

        monochrome_result = generate_from_dialog_values(
            self.iface,
            self._values(style_mode=STYLE_MONOCHROME, add_as_new_layer=True)
        )

        monochrome_expression = stroke_color_expression(monochrome_result)

        self.assertIn(
            'color_rgb("R", "G", "B")',
            color_expression
        )

        self.assertIn(
            "color_mix_rgb",
            monochrome_expression
        )

        self.assertNotIn(
            '"R"',
            stroke_color_expression(monochrome_result)
        )


    def test_illuminated_overlay_sets_soft_light_blend_mode_on_the_layer(self):

        from qgis.PyQt.QtGui import QPainter

        result = generate_from_dialog_values(
            self.iface,
            self._values(style_mode=STYLE_ILLUMINATED_OVERLAY)
        )

        self.assertEqual(
            result.blendMode(),
            QPainter.CompositionMode.CompositionMode_SoftLight
        )


    def test_illuminated_overlay_without_hypsometric_tint_warns_but_still_generates(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values(style_mode=STYLE_ILLUMINATED_OVERLAY)
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_illuminated_overlay_with_hypsometric_tint_present_does_not_warn(self):

        tint_layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            HYPSOMETRIC_TINT_LAYER_NAME,
            "memory"
        )

        QgsProject.instance().addMapLayer(
            tint_layer
        )

        result = generate_from_dialog_values(
            self.iface,
            self._values(style_mode=STYLE_ILLUMINATED_OVERLAY)
        )

        self.assertIsNotNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 0)


    def test_other_style_modes_do_not_warn_about_hypsometric_tint(self):

        generate_from_dialog_values(
            self.iface,
            self._values(style_mode=STYLE_ELEVATION_COLOR)
        )

        self.assertEqual(len(self.iface.messageBar().calls), 0)


    def test_regenerate_preserves_manually_moved_layer_position(self):

        # Real usability complaint: correcting the layer in place is
        # only actually helpful if it doesn't also reset the layer's
        # position in the Layers panel back to the default every
        # time - the user is likely to have dragged it somewhere
        # deliberate (e.g. above a basemap, below a grid).
        first = generate_from_dialog_values(self.iface, self._values())

        root = QgsProject.instance().layerTreeRoot()

        # generate_tanaka_contours() adds via a plain addMapLayer(),
        # which lands new layers at the top - add another layer
        # above it, then move the Tanaka layer below it, simulating
        # the user reordering things themselves.
        other = QgsVectorLayer("Point?crs=EPSG:4326", "Other", "memory")
        QgsProject.instance().addMapLayer(other, False)
        root.insertLayer(0, other)

        node = root.findLayer(first.id())
        node.parent().removeChildNode(node)
        root.insertLayer(1, first)

        self.assertEqual(
            [c.name() for c in root.children()],
            ["Other", OUTPUT_LAYER_NAME]
        )

        generate_from_dialog_values(self.iface, self._values())

        self.assertEqual(
            [c.name() for c in root.children()],
            ["Other", OUTPUT_LAYER_NAME]
        )


    def test_checkbox_keeps_previous_layer_alongside_the_new_one(self):

        first = generate_from_dialog_values(self.iface, self._values())

        second = generate_from_dialog_values(
            self.iface,
            self._values(add_as_new_layer=True)
        )

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 2)

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(first.id())
        )
