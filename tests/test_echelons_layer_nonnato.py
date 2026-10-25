# -*- coding: utf-8 -*-

"""
Tests for military_symbology/echelons_layer_nonnato.py - the "Echelons
(Non-NATO)" layer, which draws one echelon marker on its own. What each
marker looks like is tested in test_nonnato_symbol_engine.py's
TestEchelonMarkers; here only that the layer wires it up.

Military Cartography Tools
"""

import base64
import re

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsSymbolLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import nonnato_symbology_functions
from MilitaryCartographyTools.military_symbology.echelons_layer_nonnato import (
    DEFAULT_ENTITY,
    ENTITY_LABELS,
    LAYER_NAME,
    _label_for,
    add_echelons_layer_nonnato,
    build_echelons_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.land_unit_layer_nonnato import (
    ECHELON_LABELS,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    ECHELON_MARKER_ENTITIES,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestBuildEchelonsLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def _decoded_svg_for(self, layer, attributes):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))

        for name, value in attributes.items():
            feature.setAttribute(name, value)

        expr_context = QgsExpressionContext()
        expr_context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        expr_context.setFeature(feature)

        render_context = QgsRenderContext()
        render_context.setExpressionContext(expr_context)

        symbol = layer.renderer().symbol().clone()
        symbol.startRender(render_context, layer.fields())

        path, ok = symbol.symbolLayer(0).dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, expr_context, ""
        )

        self.assertTrue(ok, "expression failed to evaluate")
        self.assertTrue(path.startswith("base64:"))

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def test_the_layer_builds(self):

        layer = build_echelons_layer_nonnato()

        self.assertTrue(layer.isValid())
        self.assertEqual(layer.name(), LAYER_NAME)


    def test_the_fields_are_entity_affiliation_and_size(self):

        # "Layer, entity, affiliation and size; nothing else" - a bare
        # marker has nowhere to put a status, a designation, a
        # Headquarters mast or Combined Arms.
        self.assertEqual(
            [field.name() for field in build_echelons_layer_nonnato().fields()],
            ["affiliation", "entity", "scale"],
        )


    def test_it_offers_ten_entities_and_no_unspecified(self):

        self.assertEqual(len(ENTITY_LABELS), 10)
        self.assertEqual(list(ENTITY_LABELS), list(ECHELON_MARKER_ENTITIES))
        self.assertNotIn("unspecified", ENTITY_LABELS)

        self.assertIn(DEFAULT_ENTITY, ENTITY_LABELS)


    def test_the_dropdowns_are_configured(self):

        layer = build_echelons_layer_nonnato()

        for field, expected in (
            ("entity", set(ENTITY_LABELS.values())),
            ("affiliation", None),
        ):

            with self.subTest(field=field):

                setup = layer.editorWidgetSetup(layer.fields().indexOf(field))

                self.assertEqual(setup.type(), "ValueMap")

                if expected is not None:
                    self.assertEqual(set(setup.config()["map"]), expected)


    def test_every_entity_renders(self):

        layer = build_echelons_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                svg = self._decoded_svg_for(
                    layer, {"affiliation": "friend", "entity": entity}
                )

                self.assertIn("<svg", svg)
                self.assertIn("#3060c0", svg)


    def test_every_marker_is_drawn_in_the_same_box(self):

        layer = build_echelons_layer_nonnato()

        boxes = {
            re.search(r'viewBox="([^"]+)"', self._decoded_svg_for(
                layer, {"affiliation": "friend", "entity": entity}
            )).group(1)
            for entity in ENTITY_LABELS
        }

        # A box around each marker's own ink would make Company's
        # single bar as wide as the whole Army Group row.
        self.assertEqual(len(boxes), 1)


    def test_a_null_entity_still_renders(self):

        # coalesce() on every field reference, or a NULL blanks the
        # icon - the same trap every other non-NATO layer guards.
        layer = build_echelons_layer_nonnato()

        svg = self._decoded_svg_for(layer, {})

        self.assertIn("<svg", svg)


class TestAddEchelonsLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)
        QgsProject.instance().removeAllMapLayers()


    def test_it_adds_the_layer_once(self):

        iface = FakeIface()

        self.assertIsNotNone(add_echelons_layer_nonnato(iface))
        self.assertIsNone(add_echelons_layer_nonnato(iface))


class TestLabelTablesAgree(QgisTestCase):

    """
    The two tables that have to agree, and what happens if they ever
    stop agreeing.

    This layer's labels are DERIVED from Land Unit's ECHELON_LABELS,
    which is the master (settled 2026-10-01: "when in doubt the
    echelon naming in land units is the master"). Before 2026-10-25
    that derivation indexed the master directly at module scope, so a
    missing label raised KeyError on IMPORT - and plugin.py imports
    this module at module scope, so the whole plugin failed to load
    over one missing string. Flagged in the 2026-10-04 code review.

    The fix is not to tolerate drift. It is to catch it HERE, in
    development, instead of on a user's machine.
    """

    def test_every_marker_entity_has_a_real_label_in_the_master(self):

        """
        The guard-rail. If this fails, the tables have drifted: add
        the missing entity to ECHELON_LABELS in
        land_unit_layer_nonnato.py rather than working around it - the
        fallback exists to keep the plugin loadable, not to make a
        missing label acceptable.
        """

        missing = [
            entity
            for entity in ECHELON_MARKER_ENTITIES
            if entity not in ECHELON_LABELS
        ]

        self.assertEqual(missing, [])


    def test_a_known_entity_takes_the_masters_own_label(self):

        for entity in ECHELON_MARKER_ENTITIES:

            with self.subTest(entity=entity):

                self.assertEqual(
                    _label_for(entity),
                    ECHELON_LABELS[entity]
                )


    def test_an_unknown_entity_falls_back_instead_of_raising(self):

        """
        The whole point: a missing label must not be able to stop the
        module importing, because plugin.py imports it at module
        scope and the blast radius is the entire plugin.
        """

        self.assertEqual(
            _label_for("brigade_group"),
            "Brigade Group"
        )


    def test_the_fallback_is_obviously_a_placeholder(self):

        """
        Readable so the layer stays usable, but visibly derived from
        the stored key rather than silently plausible - a wrong label
        that looks right is worse than one that looks wrong.
        """

        fallback = _label_for("some_unmapped_echelon")

        self.assertEqual(fallback, "Some Unmapped Echelon")
        self.assertNotIn(fallback, set(ECHELON_LABELS.values()))
