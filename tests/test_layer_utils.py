# -*- coding: utf-8 -*-

"""
Tests for terrain/_layer_utils.py's replace_named_layer() and
add_layer_at_default_position() - shared by the Tanaka Contours,
Hypsometric Tint, Combined Hillshade, and Line of Sight dialogs to
correct their layer in place on regenerate, without resetting it to
whatever position a fresh generate would place a brand new layer at
by default.

Military Cartography Tools
"""

from qgis.core import QgsProject, QgsVectorLayer

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.terrain._layer_utils import (
    add_layer_at_default_position,
    replace_named_layer,
)


NAME = "Replaceable Layer"


def _make_layer():

    # generate()'s contract is "build and style only" - mirroring
    # generate_tanaka_contours()/generate_hypsometric_tint()/
    # generate_hillshade_combination()/generate_line_of_sight(), none
    # of which add themselves to the project any more (see
    # terrain/_layer_utils.py's own module docstring for why).
    return QgsVectorLayer(
        "Point?crs=EPSG:4326",
        NAME,
        "memory"
    )


def _default_insert_at_top(project, layer):

    project.layerTreeRoot().insertLayer(
        0,
        layer
    )


class TestReplaceNamedLayer(QgisTestCase):

    def test_first_generation_has_no_position_to_preserve(self):

        # No existing layer named NAME yet - generate() runs once,
        # and default_insert_position() places it.
        result = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

        self.assertIsNotNone(result)

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(result.id())
        )

        root = QgsProject.instance().layerTreeRoot()

        self.assertIsNotNone(
            root.findLayer(result.id())
        )


    def test_removes_the_old_layer_and_keeps_only_one(self):

        first = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

        first_id = first.id()

        second = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

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
        # sitting in the MIDDLE - i.e. somewhere its own default
        # placement (top of the tree) would never put it on its own -
        # simulating the user having dragged it there themselves.
        project = QgsProject.instance()
        root = project.layerTreeRoot()

        first = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

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
        # (middle) slot, not wherever its own default placement would
        # put a brand new layer.
        second = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

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
        first = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

        self.assertIsNotNone(first)

        result = replace_named_layer(
            NAME,
            lambda: None,
            _default_insert_at_top
        )

        self.assertIsNone(result)


    def test_generate_returning_none_leaves_the_existing_layer_alone(self):

        # A failed regenerate shouldn't destroy a previously
        # successful result just because the next attempt didn't
        # produce anything.
        first = replace_named_layer(
            NAME,
            _make_layer,
            _default_insert_at_top
        )

        replace_named_layer(
            NAME,
            lambda: None,
            _default_insert_at_top
        )

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(first.id())
        )

        matching = QgsProject.instance().mapLayersByName(NAME)

        self.assertEqual(len(matching), 1)


class TestAddLayerAtDefaultPosition(QgisTestCase):

    def test_adds_the_layer_to_the_project_and_positions_it(self):

        layer = _make_layer()

        result = add_layer_at_default_position(
            QgsProject.instance(),
            layer,
            _default_insert_at_top
        )

        self.assertIs(result, layer)

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(layer.id())
        )

        root = QgsProject.instance().layerTreeRoot()

        self.assertEqual(
            root.children()[0].name(),
            NAME
        )
