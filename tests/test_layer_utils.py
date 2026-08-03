# -*- coding: utf-8 -*-

"""
Tests for terrain/_layer_utils.py's replace_named_layer() - shared by
the Tanaka Contours and Hypsometric Tint dialogs to correct their
layer in place on regenerate, without resetting it to whatever
position a fresh generate_*() call would place a brand new layer at
by default.

Military Cartography Tools
"""

from qgis.core import QgsProject, QgsVectorLayer

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.terrain._layer_utils import replace_named_layer


NAME = "Replaceable Layer"


def _make_layer():

    # generate()'s contract is "build AND add" - mirroring
    # generate_tanaka_contours()/generate_hypsometric_tint(), which
    # both add themselves to the project via QgsProject.addMapLayer()
    # rather than leaving that to the caller.
    layer = QgsVectorLayer(
        "Point?crs=EPSG:4326",
        NAME,
        "memory"
    )

    QgsProject.instance().addMapLayer(
        layer
    )

    return layer


class TestReplaceNamedLayer(QgisTestCase):

    def test_first_generation_has_no_position_to_preserve(self):

        # No existing layer named NAME yet - generate() runs once,
        # and whatever position it puts the layer at is left alone.
        result = replace_named_layer(NAME, _make_layer)

        self.assertIsNotNone(result)

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(result.id())
        )


    def test_removes_the_old_layer_and_keeps_only_one(self):

        first = replace_named_layer(NAME, _make_layer)

        first_id = first.id()

        second = replace_named_layer(NAME, _make_layer)

        matching = QgsProject.instance().mapLayersByName(NAME)

        self.assertEqual(len(matching), 1)

        self.assertIsNone(
            QgsProject.instance().mapLayer(first_id)
        )

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(second.id())
        )


    def test_preserves_manually_moved_layer_tree_position(self):

        # Deterministically build a stack with the replaceable layer
        # sitting in the MIDDLE - i.e. somewhere generate()'s own
        # default placement (wherever a plain addMapLayer() happens
        # to put a brand new layer) would never put it on its own -
        # simulating the user having dragged it there themselves.
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        first = _make_layer()

        layer_a = QgsVectorLayer("Point?crs=EPSG:4326", "A", "memory")
        project.addMapLayer(layer_a, False)

        layer_c = QgsVectorLayer("Point?crs=EPSG:4326", "C", "memory")
        project.addMapLayer(layer_c, False)

        node = root.findLayer(first.id())
        node.parent().removeChildNode(node)

        root.insertLayer(0, layer_c)
        root.insertLayer(1, first)
        root.insertLayer(2, layer_a)

        self.assertEqual(
            [c.name() for c in root.children()],
            ["C", NAME, "A"]
        )

        # Regenerate - the new layer should land back in the same
        # (middle) slot, not wherever generate()'s own default
        # placement would put a brand new layer.
        second = replace_named_layer(NAME, _make_layer)

        self.assertEqual(
            [c.name() for c in root.children()],
            ["C", NAME, "A"]
        )

        node = root.findLayer(second.id())
        self.assertIsNotNone(node)


    def test_generate_returning_none_does_not_crash_and_returns_none(self):

        # Real reported bug: generate() can genuinely fail (e.g.
        # generate_line_of_sight() when a point falls outside the
        # DEM) - replace_named_layer() used to assume generate()
        # always returns a layer and crashed on new_layer.id().
        first = replace_named_layer(NAME, _make_layer)

        self.assertIsNotNone(first)

        result = replace_named_layer(NAME, lambda: None)

        self.assertIsNone(result)


    def test_generate_returning_none_leaves_the_existing_layer_alone(self):

        # A failed regenerate shouldn't destroy a previously
        # successful result just because the next attempt didn't
        # produce anything.
        first = replace_named_layer(NAME, _make_layer)

        replace_named_layer(NAME, lambda: None)

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(first.id())
        )

        matching = QgsProject.instance().mapLayersByName(NAME)

        self.assertEqual(len(matching), 1)
