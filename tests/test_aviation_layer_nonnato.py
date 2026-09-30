# -*- coding: utf-8 -*-

"""
Tests for military_symbology/aviation_layer_nonnato.py - the "Aviation
(Non-NATO)" layer, added 2026-09-06 by moving Army Aviation and Air
Force off Land Unit and adding six mast-carrying entities of its own.

Military Cartography Tools
"""

import base64

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsSymbolLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import nonnato_symbology_functions
from MilitaryCartographyTools.military_symbology.aviation_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_aviation_layer_nonnato,
    build_aviation_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.land_unit_layer_nonnato import (
    ENTITY_LABELS as LAND_UNIT_ENTITY_LABELS,
    build_land_unit_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    AIR_FORCE_ENTITY,
    AVIATION_ENTITIES,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestAviationEntityList(QgisTestCase):

    def test_it_offers_the_eight_agreed_entities(self):

        self.assertEqual(len(ENTITY_LABELS), 8)

        # The two that moved keep their own existing keys, so a project
        # already carrying them renders unchanged.
        self.assertEqual(ENTITY_LABELS["aviation_fixed_wing"], "Army Aviation")
        self.assertEqual(ENTITY_LABELS[AIR_FORCE_ENTITY], "Air Force")

        for entity in AVIATION_ENTITIES:
            self.assertIn(entity, ENTITY_LABELS)


    def test_the_two_moved_entities_left_land_unit(self):

        for entity in ("aviation_fixed_wing", AIR_FORCE_ENTITY):

            with self.subTest(entity=entity):

                self.assertNotIn(entity, LAND_UNIT_ENTITY_LABELS)


    def test_nothing_is_offered_on_both_layers(self):

        self.assertEqual(
            set(ENTITY_LABELS) & set(LAND_UNIT_ENTITY_LABELS), set()
        )


class TestAviationLayerMatchesLandUnit(QgisTestCase):

    """
    "same rules as land unit i.e. same dialog box replicated" - the two
    layers share their builder outright, and these pin that so a future
    change to one cannot silently skip the other.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_the_fields_are_identical_but_for_combined_arms(self):

        """
        Aviation carries Land Unit's field list with exactly one field
        removed - "in aviation - there is no requirement for combined
        arms" (2026-09-30). Written as a subtraction rather than as its
        own literal list so that a field added to Land Unit later still
        has to be accounted for here.
        """

        aviation = build_aviation_layer_nonnato()
        land_unit = build_land_unit_layer_nonnato()

        self.assertEqual(
            [(f.name(), f.type()) for f in aviation.fields()],
            [
                (f.name(), f.type())
                for f in land_unit.fields()
                if f.name() != "combined_arms"
            ],
        )


    def test_there_is_no_combined_arms_field(self):

        """The exception itself, pinned: dropped outright, not left
        inert. A checkbox that changes nothing is worse than none."""

        aviation = build_aviation_layer_nonnato()

        self.assertEqual(aviation.fields().indexOf("combined_arms"), -1)


    def test_the_renderer_passes_combined_arms_as_a_literal_false(self):

        """
        A reference to a field that does not exist evaluates to NULL,
        and one NULL argument blanks the whole icon - so dropping the
        field means the expression has to stop naming it. Rendering is
        covered below; this pins the reason.
        """

        aviation = build_aviation_layer_nonnato()

        properties = aviation.renderer().symbol().symbolLayer(
            0
        ).dataDefinedProperties()

        rendering = [
            (key, properties.property(key).expressionString())
            for key in properties.propertyKeys()
            if "mct_nonnato_unit_svg" in
            properties.property(key).expressionString()
        ]

        self.assertTrue(rendering, "no symbol expression to check")

        for key, expression in rendering:

            with self.subTest(property=key):
                self.assertNotIn("combined_arms", expression)
                self.assertIn(",false,", expression)


    def test_every_widget_matches_except_the_entity_list(self):

        aviation = build_aviation_layer_nonnato()
        land_unit = build_land_unit_layer_nonnato()

        for name in ("affiliation", "echelon", "status", "headquarters"):

            with self.subTest(field=name):

                a = aviation.editorWidgetSetup(aviation.fields().indexOf(name))
                l = land_unit.editorWidgetSetup(
                    land_unit.fields().indexOf(name)
                )

                self.assertEqual(a.type(), l.type())
                self.assertEqual(a.config(), l.config())


    def test_the_entity_dropdown_lists_this_layers_own_entities(self):

        layer = build_aviation_layer_nonnato()

        setup = layer.editorWidgetSetup(layer.fields().indexOf("entity"))

        self.assertEqual(set(setup.config()["map"]), set(ENTITY_LABELS.values()))


    def test_the_renderer_expressions_match_but_for_combined_arms(self):

        """
        Same renderer as Land Unit's, with the one substitution the
        dropped field forces. Comparing the substituted text rather
        than skipping the check keeps every other argument pinned.
        """

        aviation = build_aviation_layer_nonnato()
        land_unit = build_land_unit_layer_nonnato()

        def expressions(layer):
            properties = layer.renderer().symbol().symbolLayer(
                0
            ).dataDefinedProperties()
            return {
                key: properties.property(key).expressionString()
                for key in properties.propertyKeys()
            }

        land_unit_without_the_field = {
            key: value.replace('coalesce("combined_arms", false)', "false")
            for key, value in expressions(land_unit).items()
        }

        self.assertEqual(expressions(aviation), land_unit_without_the_field)


class TestAviationRendering(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def _svg_for(self, layer, entity, **attributes):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", entity)

        for name, value in attributes.items():
            feature.setAttribute(name, value)

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        context.setFeature(feature)

        path, ok = layer.renderer().symbol().symbolLayer(
            0
        ).dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok, "expression failed to evaluate")

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def test_every_entity_renders_through_the_real_expression(self):

        layer = build_aviation_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                svg = self._svg_for(layer, entity)

                self.assertTrue(svg.startswith("<svg"))
                self.assertIn("<path", svg)


    def test_the_mast_carrying_entities_drop_the_frame_and_amplifiers(self):

        # "this glyph - other than the unique identifiers, nothing else
        # is needed - so no need to check headquarters etc". The fields
        # still exist, they just do nothing here.
        layer = build_aviation_layer_nonnato()

        for entity in AVIATION_ENTITIES:

            with self.subTest(entity=entity):

                plain = self._svg_for(layer, entity)

                self.assertNotIn("M25,50 l150,0 0,100 -150,0 z", plain)

                for amplified in (
                    {"echelon": "battalion"},
                    {"headquarters": True},
                    {"status": "planned"},
                ):
                    self.assertEqual(
                        plain, self._svg_for(layer, entity, **amplified)
                    )


    def test_army_aviation_and_air_force_keep_their_frames(self):

        layer = build_aviation_layer_nonnato()

        for entity in ("aviation_fixed_wing", AIR_FORCE_ENTITY):

            with self.subTest(entity=entity):

                svg = self._svg_for(layer, entity)

                self.assertIn("M25,50 l150,0 0,100 -150,0 z", svg)

                self.assertNotEqual(
                    svg, self._svg_for(layer, entity, echelon="battalion")
                )


    def test_the_designations_still_work_on_the_mast_entities(self):

        layer = build_aviation_layer_nonnato()

        for entity in AVIATION_ENTITIES:

            with self.subTest(entity=entity):

                svg = self._svg_for(
                    layer, entity,
                    unique_designation_left="a", unique_designation_right="1",
                )

                self.assertIn(">A</text>", svg)
                self.assertIn(">1</text>", svg)


class TestAddAviationLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_it_adds_the_layer(self):

        layer = add_aviation_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_it_guards_against_a_duplicate(self):

        add_aviation_layer_nonnato(self.iface)

        self.assertIsNone(add_aviation_layer_nonnato(self.iface))
