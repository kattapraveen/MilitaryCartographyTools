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
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSymbolLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import nonnato_symbology_functions
from MilitaryCartographyTools.military_symbology.land_equipment_layer_nonnato import (
    LAYER_NAME,
    ENTITY_LABELS,
    add_land_equipment_layer_nonnato,
    build_land_equipment_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    AFFILIATION_COLOURS,
    APV_WHEELED_ENTITY,
    ARMOURED_RECCE_VEHICLE_ENTITY,
    B_VEHICLE_ENTITY,
    BRIDGE_LAYER_TANK_ENTITY,
    C_VEHICLE_ENTITY,
    LIGHT_RECCE_VEHICLE_ENTITY,
    MOBILITY_SELF_PROPELLED,
    MOBILITY_TRACKED,
    SIGINT_RADAR_ENTITY,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    build_sidc,
    entities_for_edition,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

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

# Three synthetic entities built from Armoured Protected Vehicle's own
# oval glyph, added 2026-09-03 - no matching real land_equipment key of
# their own (they alias to "armored_protected_vehicle" at SIDC-build
# time via nonnato_symbol_engine._EQUIPMENT_ENTITY_KEY_ALIASES).
SYNTHETIC_APV_ENTITIES = frozenset({
    BRIDGE_LAYER_TANK_ENTITY, ARMOURED_RECCE_VEHICLE_ENTITY, APV_WHEELED_ENTITY,
})

# The Vehicle family that replaced APP-6E's own real "vehicle" entity
# on this layer, 2026-09-05 - FULLY synthetic, unlike the three above:
# no SIDC and so no key alias either, a complete SVG authored in
# nonnato_symbol_engine._SYNTHETIC_VEHICLE_SVG.
SYNTHETIC_VEHICLE_ENTITIES = frozenset({
    B_VEHICLE_ENTITY, C_VEHICLE_ENTITY, LIGHT_RECCE_VEHICLE_ENTITY,
})


class TestEntityLabelsMatchTheReviewedList(QgisTestCase):

    def test_every_real_key_is_a_valid_app6e_land_equipment_entity(self):

        real_keys = entities_for_edition("2525E")["land_equipment"]

        for key in ENTITY_LABELS:

            if (
                key in SIGINT_ENTITIES
                or key in SYNTHETIC_APV_ENTITIES
                or key in SYNTHETIC_VEHICLE_ENTITIES
            ):
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

        # 54 real Land Equipment entities (6 non-tiered + 42
        # weapon-tier siblings across 14 families, Machine Gun's own
        # bare-keyed "light"/"medium" siblings included - see the rules
        # record's 2026-09-02 correction - plus 3 synthetic entities
        # built from Armoured Protected Vehicle's own oval, added
        # 2026-09-03, and 3 fully synthetic Vehicle-family entities that
        # replaced the real "vehicle" entity 2026-09-05) plus
        # Jammer/Radar (Land-scoped SIGINT, merged in 2026-09-02) - see
        # the rules record's "Required entities" section. The mine
        # family (9 entities) moved out to its own "Mines and Obstacles
        # (Non-NATO)" layer 2026-09-03 - see
        # test_mines_and_obstacles_layer_nonnato.py.
        self.assertEqual(len(ENTITY_LABELS), 56)

        for entity in SIGINT_ENTITIES:
            self.assertIn(entity, ENTITY_LABELS)


    def test_the_real_vehicle_entity_was_replaced_by_the_vehicle_family(self):

        # "remove the existing vehicle glyph, we will replace with 'B'
        # Vehicle and 'C' Vehicle" - APP-6E's own real "vehicle" key
        # (a stadium hull on two small wheels) is no longer offered.
        self.assertNotIn("vehicle", ENTITY_LABELS)

        for entity in SYNTHETIC_VEHICLE_ENTITIES:
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
            [
                "affiliation", "entity", "unique_designation",
                # Tracked/Self-Propelled, added 2026-09-06.
                "mobility",
                "rotation", "scale",
            ]
        )


    def test_no_echelon_status_or_combined_arms_field(self):

        layer = build_land_equipment_layer_nonnato()

        field_names = [field.name() for field in layer.fields()]

        for absent in ("echelon", "status", "combined_arms"):
            self.assertNotIn(absent, field_names)


    def test_apv_wheels_are_their_own_simple_marker_layers(self):

        # Real bug this exists to prevent regressing: circles drawn
        # INSIDE the SVG, below milsymbol's own declared draw area, are
        # clipped by QGIS's own marker rendering whatever the viewBox
        # says ("the circles below the ellipse are not visible... being
        # cropped"). They are three separate simple-marker layers
        # instead - the same multi-layer composition the NATO side
        # already uses to add elements to a milsymbol icon.
        layer = build_land_equipment_layer_nonnato()

        symbol = layer.renderer().symbol()

        self.assertEqual(symbol.symbolLayerCount(), 4)  # SVG + 3 wheels

        for index in range(1, 4):

            wheel = symbol.symbolLayer(index)

            self.assertIsInstance(wheel, QgsSimpleMarkerSymbolLayer)
            self.assertEqual(
                wheel.shape(), QgsSimpleMarkerSymbolLayerBase.Shape.Circle
            )


    def test_apv_wheels_only_render_for_apv_wheeled(self):

        # One shared symbol serves the whole layer, so the wheels
        # collapse to size 0 for every other entity.
        layer = build_land_equipment_layer_nonnato()

        wheel = layer.renderer().symbol().symbolLayer(1)

        size_property = wheel.dataDefinedProperties().property(
            QgsSymbolLayer.Property.Size
        )

        for entity, expected_visible in (
            (APV_WHEELED_ENTITY, True),
            ("armored_protected_vehicle", False),
            ("tank", False),
        ):
            with self.subTest(entity=entity):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("entity", entity)

                context = QgsExpressionContext()
                context.appendScope(
                    QgsExpressionContextUtils.layerScope(layer)
                )
                context.setFeature(feature)

                size = size_property.valueAsDouble(context, 0.0)[0]

                if expected_visible:
                    self.assertGreater(size, 0)
                else:
                    self.assertEqual(size, 0)


    def test_apv_wheels_stay_with_the_hull_when_a_designation_is_typed(self):

        # Reported live, 2026-09-03: "when i add the unique designator
        # in APV wheeled, the wheels shift and overlap on the text of
        # unique designation instead of staying where they are". A
        # designation grows the SVG's own viewBox downward, which moves
        # the marker's anchor (its viewBox centre) DOWN and so shifts
        # the icon itself UP - a fixed wheel offset would stay put and
        # land on the text. The offset expression reads the icon's own
        # rendered height instead, so it shrinks by the same amount.
        layer = build_land_equipment_layer_nonnato()

        wheel = layer.renderer().symbol().symbolLayer(1)

        offset_property = wheel.dataDefinedProperties().property(
            QgsSymbolLayer.Property.Offset
        )

        def offset_y_for(designation):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", APV_WHEELED_ENTITY)
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("unique_designation", designation)

            context = QgsExpressionContext()
            context.appendScope(QgsExpressionContextUtils.layerScope(layer))
            context.setFeature(feature)

            return float(
                offset_property.valueAsString(context, "")[0].split(",")[1]
            )

        plain = offset_y_for("")
        with_designation = offset_y_for("A1")

        # Both still put the wheels BELOW the anchor...
        self.assertGreater(plain, 0)
        self.assertGreater(with_designation, 0)

        # ...but the designation moves the anchor down, so the wheels
        # must sit closer to it to stay on the hull.
        self.assertLess(with_designation, plain)


    def test_apv_wheels_follow_the_affiliation_colour(self):

        layer = build_land_equipment_layer_nonnato()

        wheel = layer.renderer().symbol().symbolLayer(1)

        colour_property = wheel.dataDefinedProperties().property(
            QgsSymbolLayer.Property.StrokeColor
        )

        for affiliation, expected in AFFILIATION_COLOURS.items():

            with self.subTest(affiliation=affiliation):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("entity", APV_WHEELED_ENTITY)
                feature.setAttribute("affiliation", affiliation)

                context = QgsExpressionContext()
                context.appendScope(
                    QgsExpressionContextUtils.layerScope(layer)
                )
                context.setFeature(feature)

                self.assertEqual(
                    colour_property.valueAsString(context, "")[0], expected
                )


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
        # multiplier (nonnato_symbol_engine.
        # NONNATO_ENTITY_SIZE_MULTIPLIERS) on top of it.
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
        # _EQUIPMENT_ENTITY_KEY_ALIASES). The three synthetic APV
        # entities all alias to "armored_protected_vehicle" the same
        # way. The three Vehicle-family entities are skipped outright -
        # they never reach build_sidc() at all, being rendered from a
        # complete hand-authored SVG (_SYNTHETIC_VEHICLE_SVG).
        for entity in ENTITY_LABELS:

            if entity in SYNTHETIC_VEHICLE_ENTITIES:
                continue

            if entity in SIGINT_ENTITIES:
                real_entity = SIGINT_REAL_ENTITY_KEYS[entity]
                symbol_set = "sigint_land"
            elif entity in SYNTHETIC_APV_ENTITIES:
                real_entity = "armored_protected_vehicle"
                symbol_set = "land_equipment"
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


    def test_the_vehicle_family_renders_through_the_real_expression(self):

        # The three Vehicle-family entities never reach build_sidc() -
        # they render from a complete hand-authored SVG. This is the
        # end-to-end check that the layer's own data-defined Name
        # expression still resolves them, added 2026-09-05.
        layer = build_land_equipment_layer_nonnato()

        expected_marks = {
            B_VEHICLE_ENTITY: ">B</text>",
            C_VEHICLE_ENTITY: ">C</text>",
            LIGHT_RECCE_VEHICLE_ENTITY: "<path",
        }

        for entity, mark in expected_marks.items():

            with self.subTest(entity=entity):

                svg = self._decoded_svg_for(
                    layer, {"affiliation": "friend", "entity": entity},
                )

                self.assertIn('<rect x="25" y="50" width="150" height="100"', svg)
                self.assertEqual(svg.count("<circle"), 2)
                self.assertIn(mark, svg)


    def test_the_vehicle_family_gets_no_apv_wheel_symbol_layers(self):

        # Their wheels are drawn INSIDE the SVG, so the three simple-
        # marker wheel layers - which exist only for Armoured
        # Protection Vehicle (Wheeled) - must collapse to size 0 here,
        # or the icon gets a second, wrong set of wheels on top.
        layer = build_land_equipment_layer_nonnato()

        symbol = layer.renderer().symbol()

        for index in range(1, symbol.symbolLayerCount()):

            expression = symbol.symbolLayer(index).dataDefinedProperties().property(
                QgsSymbolLayer.Property.Size
            ).expressionString()

            self.assertIn(APV_WHEELED_ENTITY, expression)

            for entity in SYNTHETIC_VEHICLE_ENTITIES:

                with self.subTest(layer=index, entity=entity):

                    self.assertNotIn(entity, expression)


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


class TestMobilityFieldOnTheLayer(QgisTestCase):

    """The Tracked/Self-Propelled dropdown, added 2026-09-06."""

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def _decoded_svg_for(self, layer, attributes):

        import base64

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))

        for name, value in attributes.items():
            feature.setAttribute(name, value)

        expr_context = QgsExpressionContext()
        expr_context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        expr_context.setFeature(feature)

        path, ok = layer.renderer().symbol().symbolLayer(
            0
        ).dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, expr_context, ""
        )

        self.assertTrue(ok, "expression failed to evaluate")
        self.assertTrue(path.startswith("base64:"))

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def test_the_field_offers_the_three_choices_and_defaults_to_none(self):

        layer = build_land_equipment_layer_nonnato()

        index = layer.fields().indexOf("mobility")

        setup = layer.editorWidgetSetup(index)

        self.assertEqual(setup.type(), "ValueMap")
        self.assertEqual(
            set(setup.config()["map"]),
            {"None", "Tracked", "Self-Propelled"},
        )

        self.assertEqual(
            layer.defaultValueDefinition(index).expression(), "''"
        )


    def test_the_mark_reaches_the_render_through_the_real_expression(self):

        layer = build_land_equipment_layer_nonnato()

        plain = self._decoded_svg_for(
            layer, {"affiliation": "friend", "entity": "tank"}
        )

        for mobility in (MOBILITY_TRACKED, MOBILITY_SELF_PROPELLED):

            with self.subTest(mobility=mobility):

                marked = self._decoded_svg_for(
                    layer,
                    {
                        "affiliation": "friend", "entity": "tank",
                        "mobility": mobility,
                    },
                )

                self.assertNotEqual(marked, plain)
                self.assertGreater(marked.count("<path"), plain.count("<path"))


    def test_a_null_mobility_renders_exactly_like_no_mark(self):

        # coalesce() in the expression - a feature created before this
        # field existed, or one left untouched, must render unchanged.
        layer = build_land_equipment_layer_nonnato()

        self.assertEqual(
            self._decoded_svg_for(
                layer, {"affiliation": "friend", "entity": "tank"}
            ),
            self._decoded_svg_for(
                layer,
                {"affiliation": "friend", "entity": "tank", "mobility": ""},
            ),
        )
