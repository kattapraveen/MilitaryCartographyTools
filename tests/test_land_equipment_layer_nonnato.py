# -*- coding: utf-8 -*-

"""
Tests for military_symbology/land_equipment_layer_nonnato.py - the
"Land Equipment (Non-NATO)" layer, built on nonnato_symbol_engine.py's
own rendering rather than _point_symbol_layer.py's shared NATO builder.

Military Cartography Tools
"""

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
from MilitaryCartographyTools.military_symbology import land_equipment_layer_nonnato
from MilitaryCartographyTools.military_symbology.land_equipment_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_land_equipment_layer_nonnato,
    build_land_equipment_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    MINE_GREEN,
    SIGINT_RADAR_ENTITY,
    UNKNOWN_MINE_ENTITY,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

SYNTHETIC_ENTITIES = frozenset({
    UNKNOWN_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
})

# Jammer/Radar are real APP-6E entities, but under symbol_set
# "sigint_land", not "land_equipment" - merged in here 2026-09-02 from
# the retired standalone SIGINT (Non-NATO) layer, once two entities
# stopped justifying their own module/layer/toolbar action. SIGINT's
# own Radar is stored as SIGINT_RADAR_ENTITY ("sigint_radar"), not the
# literal "radar" - that key was originally Land Equipment's own
# distinct "Radar" entity, later removed from this layer's own
# ENTITY_LABELS ("remove radar and keep only radar (sigint) since both
# are same; rename radar (sigint) as radar only"), so the alias is now
# the ONLY way to reach a Radar-like icon from this layer at all. This
# maps each STORED key to the real APP-6E entity key SIDC resolution
# actually needs (identical for jammer).
SIGINT_ENTITIES = frozenset({"jammer", SIGINT_RADAR_ENTITY})

SIGINT_REAL_ENTITY_KEYS = {
    "jammer": "jammer",
    SIGINT_RADAR_ENTITY: "radar",
}


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_real_key_is_a_valid_app6e_land_equipment_entity(self):

        real_keys = entities_for_edition("2525E")["land_equipment"]

        for key in ENTITY_LABELS:

            if key in SYNTHETIC_ENTITIES or key in SIGINT_ENTITIES:
                continue

            with self.subTest(entity=key):

                self.assertIn(key, real_keys)


    def test_jammer_and_radar_are_valid_app6e_sigint_land_entities(self):

        real_keys = entities_for_edition("2525E")["sigint_land"]

        for key in SIGINT_ENTITIES:

            with self.subTest(entity=key):

                self.assertIn(SIGINT_REAL_ENTITY_KEYS[key], real_keys)


    def test_land_equipments_own_separate_radar_entity_is_gone(self):

        # "remove radar and keep only radar (sigint) since both are
        # same; rename radar (sigint) as radar only" - the literal
        # "radar" key (Land Equipment's own, distinct from SIGINT_
        # RADAR_ENTITY) must no longer be offered.
        self.assertNotIn("radar", ENTITY_LABELS)
        self.assertEqual(ENTITY_LABELS[SIGINT_RADAR_ENTITY], "Radar")


    def test_count_matches_the_reviewed_list(self):

        # 52 real Land Equipment entities (10 non-tiered + 39
        # weapon-tier siblings + 3 repurposed Machine Gun tiers, one
        # fewer non-tiered entity than before since Land Equipment's
        # own separate "radar" was removed 2026-09-02) plus 5 synthetic
        # mine icons plus Jammer/Radar (Land-scoped SIGINT, merged in
        # 2026-09-02) - see the rules record's "Required entities"
        # section.
        self.assertEqual(len(ENTITY_LABELS), 59)

        for entity in SYNTHETIC_ENTITIES | SIGINT_ENTITIES:
            self.assertIn(entity, ENTITY_LABELS)


class TestBuildLandEquipmentLayerNonnato(QgisTestCase):

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


    def _decoded_svg_for(self, layer, attributes):

        import base64

        path = self._render_path_for(layer, attributes)

        self.assertTrue(path.startswith("base64:"))

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


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

        layer = build_land_equipment_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "unique_designation", "rotation", "scale"]
        )


    def test_no_echelon_status_or_combined_arms_field(self):

        layer = build_land_equipment_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        for absent in ("echelon", "status", "combined_arms"):
            self.assertNotIn(absent, field_names)


    def test_every_entity_renders_a_valid_symbol_path(self):

        layer = build_land_equipment_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                path = self._render_path_for(
                    layer, {"affiliation": "friend", "entity": entity}
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_affiliation_renders(self):

        layer = build_land_equipment_layer_nonnato()

        for affiliation in (
            "friend", "hostile", "neutral", "unknown",
            "friendly_paramilitary", "nonstate_hostile",
        ):

            with self.subTest(affiliation=affiliation):

                path = self._render_path_for(
                    layer, {"affiliation": affiliation, "entity": "tank"}
                )

                self.assertTrue(path.startswith("base64:"))


    def test_every_mine_entity_renders_green_regardless_of_affiliation(self):

        layer = build_land_equipment_layer_nonnato()

        for entity in SYNTHETIC_ENTITIES | {
            "land_mine", "antitank_mine", "antipersonnel_land_mine"
        }:

            with self.subTest(entity=entity):

                svg = self._decoded_svg_for(
                    layer, {"affiliation": "hostile", "entity": entity}
                )

                self.assertIn(MINE_GREEN, svg)


    def test_designation_reaches_the_render(self):

        layer = build_land_equipment_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {
                "affiliation": "friend", "entity": "tank",
                "unique_designation": "a1",
            },
        )

        self.assertIn("A1", svg)


    def test_a_typed_designation_does_not_shrink_the_icon(self):

        # Superseded 2026-09-02: designation text is now drawn centred
        # directly BELOW the icon (inject_centered_designation_below()),
        # not via milsymbol's own uniqueDesignation option, so it no
        # longer widens the icon's own viewBox at all - only its
        # height. QGIS sizes an SVG marker by width, so the rendered
        # SIZE now stays IDENTICAL with or without a designation - a
        # simpler invariant than the width-compensation dance the old
        # milsymbol-driven placement needed (see mct_nonnato_unit_svg_
        # width()'s own docstring for that older mechanism, still used
        # by Land Unit/SIGINT... but SIGINT is Equipment now too, so in
        # practice only Land Unit still needs it).
        layer = build_land_equipment_layer_nonnato()

        without_designation = self._render_size_for(
            layer,
            {"affiliation": "friend", "entity": "tank", "unique_designation": ""},
        )
        with_designation = self._render_size_for(
            layer,
            {"affiliation": "friend", "entity": "tank", "unique_designation": "HQ 3"},
        )

        self.assertAlmostEqual(without_designation, with_designation, places=3)


    def test_jammer_and_radar_render_bigger_than_the_declared_marker_size(self):

        # Reported live: "Jammer and radar (sigint) are still smaller
        # than other land equipment, adjust them same as others" - both
        # read visibly smaller than every other icon at the plain
        # declared MARKER_SIZE_MM, so they get their own size
        # multiplier (_ENTITY_SIZE_MULTIPLIERS) on top of it.
        layer = build_land_equipment_layer_nonnato()

        tank_size = self._render_size_for(
            layer, {"affiliation": "friend", "entity": "tank"}
        )
        jammer_size = self._render_size_for(
            layer, {"affiliation": "friend", "entity": "jammer"}
        )
        radar_size = self._render_size_for(
            layer, {"affiliation": "friend", "entity": SIGINT_RADAR_ENTITY}
        )

        self.assertGreater(jammer_size, tank_size)
        self.assertGreater(radar_size, tank_size)


    def test_entity_keys_match_a_real_land_equipment_sidc(self):

        # Confirms ENTITY_LABELS' keys are exactly what
        # render_nonnato_equipment_svg()'s own build_sidc() call
        # expects - not just present in the 2525E vocabulary (already
        # checked above) but resolving with no KeyError for every one.
        # Jammer/Radar resolve under "sigint_land" instead, per
        # nonnato_symbol_engine._EQUIPMENT_SYMBOL_SET_OVERRIDES, and
        # SIGINT's own Radar resolves through its own real entity key
        # ("radar", not the stored "sigint_radar" - see
        # _EQUIPMENT_ENTITY_KEY_ALIASES).
        for entity in ENTITY_LABELS:

            if entity in SYNTHETIC_ENTITIES:
                continue

            if entity in SIGINT_ENTITIES:
                real_entity = SIGINT_REAL_ENTITY_KEYS[entity]
                symbol_set = "sigint_land"
            else:
                real_entity = entity
                symbol_set = "land_equipment"

            with self.subTest(entity=entity):

                build_sidc(
                    affiliation="friend", entity=real_entity,
                    symbol_set=symbol_set, edition="2525E",
                )


    def test_jammer_and_radar_designation_renders_centred_below(self):

        # Same centred-below-the-icon designation treatment as every
        # other Land Equipment entity - see inject_centered_
        # designation_below()'s own docstring for the 2026-09-02 fix
        # this is (superseding the SIGINT-only y="130" nudge from
        # earlier the same day).
        layer = build_land_equipment_layer_nonnato()

        svg = self._decoded_svg_for(
            layer,
            {
                "affiliation": "friend", "entity": SIGINT_RADAR_ENTITY,
                "unique_designation": "a1",
            },
        )

        self.assertIn(">A1<", svg)
        self.assertIn('text-anchor="middle"', svg)


class TestAddLandEquipmentLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_a_layer_named_land_equipment_nonnato(self):

        layer = add_land_equipment_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), layer.id())


    def test_guards_against_a_duplicate(self):

        first = add_land_equipment_layer_nonnato(self.iface)

        result = add_land_equipment_layer_nonnato(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
