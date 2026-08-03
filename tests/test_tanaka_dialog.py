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
    QgsRectangle,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from .qgis_test_case import (
    build_synthetic_sloped_dem,
    FakeIface,
    QgisTestCase,
    make_canvas,
)

from MilitaryCartographyTools.terrain.tanaka_contours import OUTPUT_LAYER_NAME
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

        canvas = make_canvas()

        canvas.setExtent(
            QgsRectangle(37.3402, -3.0935, 37.3428, -3.0905)
        )

        self.iface = FakeIface(canvas=canvas)


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass


    def _values(self, add_as_new_layer=False, monochrome=False):

        return {
            "dem_layer": self.dem_layer,
            "interval": 20.0,
            "segment_length": 5.0,
            "light_azimuth_deg": 315.0,
            "min_width_mm": 0.15,
            "max_width_mm": 0.6,
            "monochrome": monochrome,
            "add_as_new_layer": add_as_new_layer,
        }


    def test_no_dem_layer_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values() | {"dem_layer": None}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


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


    def test_monochrome_flag_reaches_the_generated_symbol(self):

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
            self._values(monochrome=False, add_as_new_layer=True)
        )

        color_expression = stroke_color_expression(color_result)

        monochrome_result = generate_from_dialog_values(
            self.iface,
            self._values(monochrome=True, add_as_new_layer=True)
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
