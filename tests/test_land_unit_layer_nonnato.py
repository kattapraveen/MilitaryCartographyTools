# -*- coding: utf-8 -*-

"""
Tests for military_symbology/land_unit_layer_nonnato.py - the
"Land Unit (Non-NATO)" layer, built on nonnato_symbol_engine.py's own
rendering rather than _point_symbol_layer.py's shared NATO builder.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
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
from MilitaryCartographyTools.military_symbology.land_unit_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_land_unit_layer_nonnato,
    build_land_unit_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    AIR_DEFENSE_ARTILLERY_ENTITY,
    AIR_FORCE_ENTITY,
    ENEMY_INFO_UNKNOWN_ENTITY,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

SYNTHETIC_ENTITIES = (
    ENEMY_INFO_UNKNOWN_ENTITY, AIR_DEFENSE_ARTILLERY_ENTITY, AIR_FORCE_ENTITY,
)


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_real_key_is_a_valid_app6e_ground_unit_entity(self):

        real_keys = entities_for_edition("2525E")["ground_unit"]

        for key in ENTITY_LABELS:

            if key in SYNTHETIC_ENTITIES:
                continue

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_count_matches_the_reviewed_list_plus_the_synthetic_entries(self):

        # 20 real entities the maintainer's reviewed check sheet
        # confirmed, plus Enemy (Info Unknown) (no SIDC at all), Air
        # Defence Artillery (Air Defence's real SIDC with Artillery's
        # own dot fixed up on top, requested live 2026-09-02), and Air
        # Force (Army Aviation's real SIDC with its own figure-of-8
        # opened on the right, requested live 2026-09-03) - none of the
        # three has a matching real ground_unit key of its own. See the
        # rules record's "Required entities" section.
        self.assertEqual(len(ENTITY_LABELS), 23)

        for entity in SYNTHETIC_ENTITIES:
            self.assertIn(entity, ENTITY_LABELS)


class TestBuildLandUnitLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def _render_path_for(self, layer, attributes):

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

        svg_layer = symbol.symbolLayer(0)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, expr_context, ""
        )

        self.assertTrue(ok, "expression failed to evaluate")

        return path


    def _render_size_for(self, layer, attributes):

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

        svg_layer = symbol.symbolLayer(0)

        size, ok = svg_layer.dataDefinedProperties().valueAsDouble(
            QgsSymbolLayer.Property.Size, expr_context, 0.0
        )

        self.assertTrue(ok, "size expression failed to evaluate")

        return size


    def test_every_field_exists_with_the_right_type(self):

        layer = build_land_unit_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation", "entity", "echelon", "status",
                "combined_arms", "unique_designation_left",
                "unique_designation_right", "rotation", "scale",
            ]
        )


    def test_every_real_entity_renders_a_valid_symbol_path(self):

        layer = build_land_unit_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(
                    layer,
                    {
                        "affiliation": "friend",
                        "entity": entity,
                        "echelon": "unspecified",
                        "status": "present",
                        "combined_arms": False,
                    },
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_affiliation_renders(self):

        layer = build_land_unit_layer_nonnato()

        for affiliation in (
            "friend", "hostile", "neutral", "unknown",
            "friendly_paramilitary", "nonstate_hostile",
        ):

            with self.subTest(affiliation=affiliation):

                path = self._render_path_for(
                    layer,
                    {
                        "affiliation": affiliation,
                        "entity": "infantry",
                        "echelon": "unspecified",
                        "status": "present",
                        "combined_arms": False,
                    },
                )

                self.assertTrue(path.startswith("base64:"))


    def test_combined_arms_checkbox_reaches_the_render(self):

        layer = build_land_unit_layer_nonnato()

        without = self._render_path_for(
            layer,
            {
                "affiliation": "friend", "entity": "infantry",
                "echelon": "unspecified", "status": "present",
                "combined_arms": False,
            },
        )
        with_ca = self._render_path_for(
            layer,
            {
                "affiliation": "friend", "entity": "infantry",
                "echelon": "unspecified", "status": "present",
                "combined_arms": True,
            },
        )

        self.assertNotEqual(without, with_ca)


    def test_left_and_right_designation_fields_reach_the_render(self):

        layer = build_land_unit_layer_nonnato()

        base_attributes = {
            "affiliation": "friend", "entity": "infantry",
            "echelon": "unspecified", "status": "present",
            "combined_arms": False,
        }

        plain = self._render_path_for(
            layer,
            {
                **base_attributes,
                "unique_designation_left": "",
                "unique_designation_right": "",
            },
        )
        left_only = self._render_path_for(
            layer,
            {
                **base_attributes,
                "unique_designation_left": "A1",
                "unique_designation_right": "",
            },
        )
        right_only = self._render_path_for(
            layer,
            {
                **base_attributes,
                "unique_designation_left": "",
                "unique_designation_right": "B2",
            },
        )
        both = self._render_path_for(
            layer,
            {
                **base_attributes,
                "unique_designation_left": "A1",
                "unique_designation_right": "B2",
            },
        )

        self.assertNotEqual(plain, left_only)
        self.assertNotEqual(plain, right_only)
        self.assertNotEqual(left_only, right_only)
        self.assertNotEqual(left_only, both)
        self.assertNotEqual(right_only, both)


    def test_a_typed_designation_does_not_shrink_the_icon(self):

        # Reported live, 2026-09-02: "when i insert a land unit with
        # designator, the size of the glyph is reducing making it
        # unreadable" - QGIS sizes an SVG marker by its own declared
        # width, and milsymbol widens that declared width to fit typed
        # text, so a FIXED marker size drew a visibly smaller icon the
        # moment text was typed in.
        #
        # The fix makes the Size PROPERTY itself grow with a
        # designation (by design - see stabilised_nonnato_size_
        # expression()'s own docstring for why) so the ICON's own drawn
        # footprint stays fixed instead. That footprint is Size *
        # (plain_width / amplified_width) - dividing the compensation
        # back out recovers the plain, no-designation size exactly,
        # which is what this test actually checks, rather than
        # (wrongly) expecting the raw Size property to stay flat.
        layer = build_land_unit_layer_nonnato()

        base_attributes = {
            "affiliation": "friend", "entity": "infantry",
            "echelon": "unspecified", "status": "present",
            "combined_arms": False,
        }

        without_designation = self._render_size_for(
            layer,
            {
                **base_attributes,
                "unique_designation_left": "",
                "unique_designation_right": "",
            },
        )
        with_designation = self._render_size_for(
            layer,
            {
                **base_attributes,
                "unique_designation_left": "HQ 3",
                "unique_designation_right": "",
            },
        )

        # The compensation must have actually kicked in - a designation
        # genuinely widens the icon's own bounding box.
        self.assertGreater(with_designation, without_designation)

        plain_width = QgsExpression(
            "mct_nonnato_unit_svg_width("
            "'friend','infantry','unspecified','present','','','false')"
        ).evaluate()

        amplified_width = QgsExpression(
            "mct_nonnato_unit_svg_width("
            "'friend','infantry','unspecified','present','HQ 3','','false')"
        ).evaluate()

        icon_footprint_without = without_designation
        icon_footprint_with = with_designation * plain_width / amplified_width

        self.assertAlmostEqual(
            icon_footprint_without, icon_footprint_with, places=3
        )


    def test_entity_keys_match_a_real_ground_unit_sidc(self):

        # Confirms ENTITY_LABELS' keys are exactly what
        # render_nonnato_unit_svg()'s own build_sidc() call expects -
        # not just present in the 2525E vocabulary (already checked
        # above) but resolving with no KeyError for every one. Skips
        # the synthetic entries with no real key of their own - Enemy
        # (Info Unknown) never reaches build_sidc() at all, and Air
        # Defence Artillery/Air Force only reach it through render_
        # nonnato_unit_svg()'s own alias resolution
        # (_UNIT_ENTITY_KEY_ALIASES), not as this raw key - see
        # test_nonnato_symbol_engine.py's own TestRenderNonnatoUnitSvg
        # for that path's own shape checks.
        for entity in ENTITY_LABELS:

            if entity in SYNTHETIC_ENTITIES:
                continue

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=entity,
                    symbol_set="ground_unit", edition="2525E",
                )


class TestAddLandUnitLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_land_unit_nonnato(self):

        layer = add_land_unit_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_land_unit_layer_nonnato(self.iface)

        result = add_land_unit_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
