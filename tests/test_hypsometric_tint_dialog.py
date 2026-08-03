# -*- coding: utf-8 -*-

"""
Tests for terrain/hypsometric_tint_dialog.py's
generate_from_dialog_values() - the accept-flow logic split out of
show_hypsometric_tint_dialog() so it can be exercised without driving
an actual modal QDialog. Mirrors tests/test_tanaka_dialog.py's shape,
covering the same "Add as new layer" default-replace-in-place
behaviour.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from .qgis_test_case import (
    build_synthetic_sloped_dem,
    FakeIface,
    QgisTestCase,
    make_canvas,
)

from MilitaryCartographyTools.terrain.hypsometric_tint import OUTPUT_LAYER_NAME
from MilitaryCartographyTools.terrain.hypsometric_tint_dialog import (
    generate_from_dialog_values,
)


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


    def _values(self, add_as_new_layer=False, opacity=1.0):

        return {
            "dem_layer": self.dem_layer,
            "opacity": opacity,
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


    def test_regenerate_preserves_manually_moved_layer_position(self):

        # Real usability complaint: correcting the layer in place is
        # only actually helpful if it doesn't also reset the layer's
        # position back to the default (bottom of the stack) every
        # time - the user is likely to have dragged it somewhere
        # deliberate.
        first = generate_from_dialog_values(self.iface, self._values())

        root = QgsProject.instance().layerTreeRoot()

        # generate_hypsometric_tint() places new layers at the
        # bottom by default - move it to the top instead, simulating
        # the user reordering things themselves.
        other = QgsVectorLayer("Point?crs=EPSG:4326", "Other", "memory")
        QgsProject.instance().addMapLayer(other, False)
        root.insertLayer(len(root.children()), other)

        node = root.findLayer(first.id())
        node.parent().removeChildNode(node)
        root.insertLayer(0, first)

        self.assertEqual(
            [c.name() for c in root.children()],
            [OUTPUT_LAYER_NAME, "Other"]
        )

        generate_from_dialog_values(self.iface, self._values())

        self.assertEqual(
            [c.name() for c in root.children()],
            [OUTPUT_LAYER_NAME, "Other"]
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


    def test_opacity_value_reaches_the_generated_layer(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values(opacity=0.4)
        )

        self.assertAlmostEqual(
            result.opacity(),
            0.4
        )
