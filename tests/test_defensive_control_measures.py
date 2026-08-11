# -*- coding: utf-8 -*-

"""
Tests for military_symbology/defensive_control_measures.py - the
Defensive Control Measures Areas layer (Table H-VIII) and Points layer
(Table H-IX, Observation Post family - moved into its own dedicated
layer here 2026-08-10, see module docstring), Mini-Phase H4. The Areas
layer is styled via a QgsRuleBasedRenderer keyed on "measure_type"; the
Points layer renders through milsymbol.js the same way control_measure_
points.py does. See the module's own docstring for what was scoped out
(Contain/Retain).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsGeometryGeneratorSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsPalLayerSettings,
    QgsProject,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSymbolLayer,
    QgsSymbolLayerUtils,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology import (
    defensive_control_measures,
)
from MilitaryCartographyTools.military_symbology.defensive_control_measures import (
    AFFILIATION_LABELS,
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    ECHELON_LABELS,
    POINTS_LAYER_NAME,
    POINT_ENTITY_LABELS,
    STATUS_LABELS,
    add_defensive_control_measures_areas_layer,
    add_defensive_control_measures_points_layer,
    create_defensive_control_measures_areas_layer,
    create_defensive_control_measures_points_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


def _rule_symbol_for(layer, measure_type):

    root = layer.renderer().rootRule()

    rule = next(
        rule for rule in root.children()
        if rule.filterExpression() == f'"measure_type" = \'{measure_type}\''
    )

    return rule.symbol()


def _resolve_stroke_color(symbol_layer, layer, affiliation):

    feature = QgsFeature(layer.fields())
    feature.setAttribute("affiliation", affiliation)

    context = layer.createExpressionContext()
    context.setFeature(feature)

    color, ok = symbol_layer.dataDefinedProperties().valueAsColor(
        QgsSymbolLayer.Property.StrokeColor,
        context,
        QColor(1, 2, 3)
    )

    return color, ok


class TestCreateDefensiveControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _rule_by_filter(self, layer, has_filter):

        # The Areas layer uses QgsRuleBasedLabeling (not
        # QgsVectorLayerSimpleLabeling, which has a single top-level
        # .settings()) - see _configure_area_designation_labeling()'s
        # own docstring for why: a Battle Position/Strong Point feature
        # needs BOTH its own centred name label AND a separate,
        # perimeter-anchored echelon label, two independent rules rather
        # than one shared label expression. The name rule has no filter
        # (applies to every measure type); the echelon rule is filtered
        # to just battle_position/strong_point with a non-blank echelon.
        for rule in layer.labeling().rootRule().children():

            if bool(rule.filterExpression()) == has_filter:

                return rule

        raise AssertionError("no matching labeling rule found")


    def _evaluate_name_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = self._rule_by_filter(layer, has_filter=False).settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def _evaluate_echelon_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = self._rule_by_filter(layer, has_filter=True).settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_defensive_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status", "echelon",
                "prepared", "unique_designation", "area_km2",
                "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_defensive_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_measure_type_uses_a_value_map_widget_defaulting_to_battle_position(self):

        layer = create_defensive_control_measures_areas_layer()

        idx = layer.fields().indexOf("measure_type")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in AREA_MEASURE_TYPE_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'battle_position'"
        )


    def test_affiliation_and_status_reuse_the_shared_fields(self):

        layer = create_defensive_control_measures_areas_layer()

        affiliation_idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.editorWidgetSetup(affiliation_idx).config()["map"],
            {label: value for value, label in AFFILIATION_LABELS.items()}
        )

        status_idx = layer.fields().indexOf("status")

        self.assertEqual(
            layer.editorWidgetSetup(status_idx).config()["map"],
            {label: value for value, label in STATUS_LABELS.items()}
        )


    def test_echelon_uses_a_value_map_widget_defaulting_to_blank(self):

        layer = create_defensive_control_measures_areas_layer()

        idx = layer.fields().indexOf("echelon")

        widget_setup = layer.editorWidgetSetup(idx)

        expected_map = {"(Not shown)": ""}
        expected_map.update(
            {label: value for value, label in ECHELON_LABELS.items()}
        )
        self.assertEqual(widget_setup.config()["map"], expected_map)

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "''"
        )


    def test_prepared_uses_a_value_map_widget_defaulting_to_no(self):

        layer = create_defensive_control_measures_areas_layer()

        idx = layer.fields().indexOf("prepared")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(widget_setup.type(), "ValueMap")
        self.assertEqual(
            widget_setup.config()["map"],
            {"No": "", "Prepared but not occupied": "P"}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "''"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_defensive_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_defensive_control_measures_areas_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)
            outline_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(outline_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_battle_position_name_label_has_no_echelon_in_it(self):

        # 2026-08-10 correction: the echelon glyph moved out of this
        # floating, polygon-centred name label entirely - see
        # _configure_area_designation_labeling()'s own docstring for why
        # (it's now a separate, masked label on the perimeter instead).
        layer = create_defensive_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_name_label(
                layer, "battle_position", unique_designation="xray"
            ),
            "XRAY"
        )

        self.assertEqual(
            self._evaluate_name_label(
                layer, "battle_position",
                unique_designation="7", echelon="battalion",
            ),
            "7"
        )

        self.assertEqual(
            self._evaluate_name_label(
                layer, "battle_position",
                unique_designation="mars", prepared="P",
            ),
            "(P) MARS"
        )


    def test_strong_point_name_label_has_no_echelon_in_it(self):

        layer = create_defensive_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_name_label(
                layer, "strong_point",
                unique_designation="two", echelon="team_crew",
            ),
            "TWO"
        )


    def test_engagement_area_label_prefixes_the_type_abbreviation(self):

        layer = create_defensive_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_name_label(
                layer, "engagement_area", unique_designation="rock"
            ),
            "EA ROCK"
        )


    def test_echelon_label_is_just_the_table_d_iii_glyph(self):

        layer = create_defensive_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_echelon_label(
                layer, "battle_position", echelon="battalion"
            ),
            "II"
        )

        self.assertEqual(
            self._evaluate_echelon_label(
                layer, "strong_point", echelon="team_crew"
            ),
            "Ø"
        )


    def test_echelon_label_rule_is_filtered_to_battle_position_and_strong_point(self):

        layer = create_defensive_control_measures_areas_layer()

        echelon_rule = self._rule_by_filter(layer, has_filter=True)

        self.assertEqual(
            echelon_rule.filterExpression(),
            "\"measure_type\" IN ('battle_position', 'strong_point')"
            " AND \"echelon\" IS NOT NULL AND \"echelon\" != ''"
        )


    def test_echelon_label_is_anchored_at_the_polygons_origin_point(self):

        # Per the project maintainer's own explicit instruction: "take
        # the origin point as the place to insert the echelon" - a label
        # geometry generator (the labeling-engine equivalent of
        # QgsGeometryGeneratorSymbolLayer) feeding the feature's own
        # first digitized vertex, not its centroid/default anchor.
        layer = create_defensive_control_measures_areas_layer()

        echelon_settings = self._rule_by_filter(layer, has_filter=True).settings()

        self.assertTrue(echelon_settings.geometryGeneratorEnabled)
        self.assertEqual(
            echelon_settings.geometryGenerator,
            "point_n($geometry, 1)"
        )
        self.assertEqual(
            echelon_settings.geometryGeneratorType,
            Qgis.GeometryType.Point
        )

        point_settings = echelon_settings.pointSettings()

        self.assertEqual(
            point_settings.quadrant(),
            Qgis.LabelQuadrantPosition.Over
        )


    def test_echelon_label_mask_targets_outlines_and_the_strong_point_ticks(self):

        # Regression test for the echelon glyph floating inside the
        # polygon instead of sitting in a real gap in the perimeter line
        # - see _configure_area_designation_labeling()'s own docstring.
        # The tick layer's own id is included too (2026-08-10 follow-up):
        # without it, Strong Point's own teeth kept drawing right through
        # the masked gap in the outline, hiding the glyph underneath.
        layer = create_defensive_control_measures_areas_layer()

        echelon_settings = self._rule_by_filter(layer, has_filter=True).settings()
        text_format = echelon_settings.format()
        mask = text_format.mask()

        self.assertTrue(mask.enabled())
        self.assertEqual(mask.size(), 3.0)

        refs = mask.maskedSymbolLayers()
        self.assertTrue(all(ref.layerId() == layer.id() for ref in refs))

        masked_ids = {ref.symbolLayerIdV2() for ref in refs}

        self.assertIn(
            defensive_control_measures._BATTLE_POSITION_OUTLINE_SYMBOL_LAYER_ID,
            masked_ids
        )
        self.assertIn(
            defensive_control_measures._STRONG_POINT_OUTLINE_SYMBOL_LAYER_ID,
            masked_ids
        )
        self.assertIn(
            defensive_control_measures._STRONG_POINT_TICK_SYMBOL_LAYER_ID,
            masked_ids
        )


    def test_battle_position_and_strong_point_outlines_have_stable_ids(self):

        layer = create_defensive_control_measures_areas_layer()

        battle_position_symbol = _rule_symbol_for(layer, "battle_position")

        self.assertEqual(
            battle_position_symbol.symbolLayer(0).id(),
            defensive_control_measures._BATTLE_POSITION_OUTLINE_SYMBOL_LAYER_ID
        )

        strong_point_symbol = _rule_symbol_for(layer, "strong_point")

        self.assertEqual(
            strong_point_symbol.symbolLayer(0).id(),
            defensive_control_measures._STRONG_POINT_OUTLINE_SYMBOL_LAYER_ID
        )


    def test_battle_position_dashes_when_prepared_regardless_of_status(self):

        # 2026-08-10 correction: "prepared" used to be ignored by the
        # line style entirely, so a feature with "prepared" set but
        # "status" left at its own default ("present") rendered with a
        # SOLID perimeter - wrong, since Table H-VIII's own "Prepared
        # but not occupied" variant (151202) is drawn dashed regardless.
        layer = create_defensive_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "battle_position")
        outline_layer = symbol.symbolLayer(0)

        # Only "present" + not-prepared stays solid; every other
        # combination (including "present" + "prepared" alone, the case
        # that used to be missed) is dashed.
        cases = [
            (("present", ""), QgsSymbolLayerUtils.decodePenStyle("solid")),
            (("present", "P"), QgsSymbolLayerUtils.decodePenStyle("dash")),
            (("planned", ""), QgsSymbolLayerUtils.decodePenStyle("dash")),
            (("planned", "P"), QgsSymbolLayerUtils.decodePenStyle("dash")),
        ]

        for (status, prepared), expected_style in cases:

            feature = QgsFeature(layer.fields())
            feature.setAttribute("status", status)
            feature.setAttribute("prepared", prepared)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            style, ok = outline_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.StrokeStyle, context, ""
            )
            self.assertTrue(ok, (status, prepared))
            self.assertEqual(
                QgsSymbolLayerUtils.decodePenStyle(style),
                expected_style,
                (status, prepared)
            )


    def test_strong_point_tick_layer_has_a_stable_id(self):

        layer = create_defensive_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "strong_point")
        tooth_generator = symbol.symbolLayer(1)
        tick_layer = tooth_generator.subSymbol().symbolLayer(0)

        self.assertEqual(
            tick_layer.id(),
            defensive_control_measures._STRONG_POINT_TICK_SYMBOL_LAYER_ID
        )


    def test_strong_point_has_a_toothed_outline_normalised_to_a_fixed_winding(self):

        # 2026-08-10 correction: the tooth marker-line layer is now
        # wrapped in a QgsGeometryGeneratorSymbolLayer using
        # force_rhr($geometry) - see _strong_point_symbol()'s own
        # docstring for why a fixed ring winding is required before a
        # fixed marker offset can reliably mean "outward" for every
        # feature, regardless of how the user digitized it.
        layer = create_defensive_control_measures_areas_layer()

        symbol = _rule_symbol_for(layer, "strong_point")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        tooth_generator = symbol.symbolLayer(1)

        self.assertIsInstance(tooth_generator, QgsGeometryGeneratorSymbolLayer)
        self.assertEqual(
            tooth_generator.geometryExpression(),
            "force_rhr($geometry)"
        )

        tooth_sub_symbol = tooth_generator.subSymbol()
        tooth_layer = tooth_sub_symbol.symbolLayer(0)

        self.assertIsInstance(tooth_layer, QgsMarkerLineSymbolLayer)
        self.assertEqual(
            tooth_layer.placements(),
            Qgis.MarkerLinePlacement.Interval
        )


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_defensive_control_measures_areas_layer()

            self.assertTrue(
                layer.defaultValueDefinition(
                    layer.fields().indexOf("area_km2")
                ).applyOnUpdate()
            )

            self.assertTrue(
                layer.defaultValueDefinition(
                    layer.fields().indexOf("perimeter_km")
                ).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateDefensiveControlMeasuresPointsLayer(QgisTestCase):

    """
    Table H-IX (Observation post, H.5.12.2) - moved into its own
    dedicated layer 2026-08-10 (see module docstring), out of the
    shared control_measure_points.py dropdown. Same milsymbol.js
    rendering mechanism as that module - see its own tests for the
    equivalent coverage this mirrors.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_has_the_expected_fields(self):

        layer = create_defensive_control_measures_points_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            ["affiliation", "entity", "status", "unique_designation"]
        )


    def test_is_a_point_layer(self):

        layer = create_defensive_control_measures_points_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Point"
        )


    def test_entity_dropdown_offers_exactly_table_h_ix(self):

        layer = create_defensive_control_measures_points_layer()

        idx = layer.fields().indexOf("entity")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in POINT_ENTITY_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'observation_post'"
        )


    def test_renderers_svg_layer_has_a_data_defined_name(self):

        layer = create_defensive_control_measures_points_layer()

        symbol = layer.renderer().symbol()
        # Symbol layer 0 is the Forward Observer diagonal anchor line
        # (added 2026-08-10, only enabled for that one entity - see
        # _build_points_renderer()'s own comment); the SVG icon layer is
        # now layer 1.
        svg_layer = symbol.symbolLayer(1)

        self.assertTrue(
            svg_layer.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.Name
            )
        )


    def test_a_real_feature_resolves_to_a_valid_symbol_path(self):

        layer = create_defensive_control_measures_points_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "hostile")
        feature.setAttribute("entity", "target_reference_point")
        feature.setAttribute("status", "present")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        symbol = layer.renderer().symbol()
        svg_layer = symbol.symbolLayer(1)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            context,
            ""
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_forward_observer_has_a_diagonal_anchor_line_only_for_that_entity(self):

        # 2026-08-10, per the project maintainer's own live-testing
        # report: milsymbol.js's own icon for this entity only draws
        # the triangle and the dot, missing the diagonal line the
        # standard's own template picture (page 425) shows - see
        # _forward_observer_anchor_line_layer()'s own comment.
        layer = create_defensive_control_measures_points_layer()

        symbol = layer.renderer().symbol()
        line_layer = symbol.symbolLayer(0)

        self.assertEqual(
            line_layer.shape(),
            QgsSimpleMarkerSymbolLayerBase.Shape.Line
        )

        enabled_feature = QgsFeature(layer.fields())
        enabled_feature.setAttribute("entity", "observation_post_forward_observer")

        disabled_feature = QgsFeature(layer.fields())
        disabled_feature.setAttribute("entity", "observation_post")

        enabled_context = layer.createExpressionContext()
        enabled_context.setFeature(enabled_feature)

        disabled_context = layer.createExpressionContext()
        disabled_context.setFeature(disabled_feature)

        self.assertTrue(
            line_layer.dataDefinedProperties().valueAsBool(
                QgsSymbolLayer.Property.LayerEnabled,
                enabled_context,
                False
            )[0]
        )

        self.assertFalse(
            line_layer.dataDefinedProperties().valueAsBool(
                QgsSymbolLayer.Property.LayerEnabled,
                disabled_context,
                False
            )[0]
        )


    def test_unique_designation_is_labeled_for_entities_milsymbol_cannot_place_text_for(self):

        # 2026-08-10, per the project maintainer's own live-testing
        # report: milsymbol.js has NO text-slot position config at all
        # for these six entities (unlike Target Reference Point, which
        # already works and is deliberately excluded here) - see
        # _POINTS_DESIGNATION_LABEL_EXPRESSION's own comment.
        layer = create_defensive_control_measures_points_layer()

        self.assertIsNotNone(layer.labeling())
        self.assertTrue(layer.labelsEnabled())

        label_expression = QgsExpression(
            layer.labeling().settings().fieldName
        )

        for entity in (
            "observation_post",
            "observation_post_reconnaissance",
            "observation_post_forward_observer",
            "observation_post_cbrn",
            "observation_post_sensor_listening",
            "observation_post_combat",
        ):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", entity)
            feature.setAttribute("unique_designation", "alpha")

            context = layer.createExpressionContext()
            context.setFeature(feature)

            self.assertEqual(
                label_expression.evaluate(context),
                "ALPHA"
            )

        target_reference_point_feature = QgsFeature(layer.fields())
        target_reference_point_feature.setAttribute("entity", "target_reference_point")
        target_reference_point_feature.setAttribute("unique_designation", "alpha")

        context = layer.createExpressionContext()
        context.setFeature(target_reference_point_feature)

        self.assertEqual(
            label_expression.evaluate(context),
            ""
        )


    def test_observation_post_unspecified_gets_a_larger_label_font(self):

        # 2026-08-10, per the project maintainer's own live-testing
        # report: the shared 3.5pt label size was unreadable for
        # "Observation Post/Outpost" specifically - the only one of the
        # six with an otherwise empty triangle, so it alone was bumped
        # to 8pt; the other five (each already sharing their own
        # triangle with an interior glyph) were left at 3.5pt - see
        # _POINTS_LABEL_FONT_SIZE_EXPRESSION's own comment.
        layer = create_defensive_control_measures_points_layer()

        # Held as explicit named locals rather than one long chained
        # expression - a long chain through several PyQt/SIP-wrapped
        # QGIS objects segfaulted here (confirmed live), the same class
        # of dangling-intermediate-reference bug this project has hit
        # before (see e.g. c2_measures.py's own Distress Call anchor
        # line docstring).
        labeling = layer.labeling()
        settings = labeling.settings()
        properties = settings.dataDefinedProperties()
        size_property = properties.property(QgsPalLayerSettings.Property.Size)

        size_expression = QgsExpression(size_property.expressionString())

        unspecified_feature = QgsFeature(layer.fields())
        unspecified_feature.setAttribute("entity", "observation_post")

        context = layer.createExpressionContext()
        context.setFeature(unspecified_feature)

        self.assertEqual(size_expression.evaluate(context), 8.0)

        forward_observer_feature = QgsFeature(layer.fields())
        forward_observer_feature.setAttribute("entity", "observation_post_forward_observer")

        context = layer.createExpressionContext()
        context.setFeature(forward_observer_feature)

        self.assertEqual(size_expression.evaluate(context), 3.5)


class TestAddDefensiveControlMeasuresPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_creates_and_adds_the_layer(self):

        layer = add_defensive_control_measures_points_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_defensive_control_measures_points_layer(self.iface)

        result = add_defensive_control_measures_points_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


class TestAddDefensiveControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_creates_and_adds_the_layer(self):

        layer = add_defensive_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_defensive_control_measures_areas_layer(self.iface)

        result = add_defensive_control_measures_areas_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_defensive_control_measures_areas_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], AREAS_LAYER_NAME)
