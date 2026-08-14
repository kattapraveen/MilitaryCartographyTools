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

import math

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsGeometryGeneratorSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsPalLayerSettings,
    QgsProject,
    QgsSimpleMarkerSymbolLayer,
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
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    POINTS_LAYER_NAME,
    POINT_ENTITY_LABELS,
    STATUS_LABELS,
    _CONTAIN_ARC_SYMBOL_LAYER_ID,
    _CONTAIN_ARROW_SYMBOL_LAYER_ID,
    _RETAIN_ARC_SYMBOL_LAYER_ID,
    add_defensive_control_measures_areas_layer,
    add_defensive_control_measures_lines_layer,
    add_defensive_control_measures_points_layer,
    create_defensive_control_measures_areas_layer,
    create_defensive_control_measures_lines_layer,
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


class TestContainAndRetain(QgisTestCase):

    """
    Table H-VIII's own two procedural constructions, built 2026-08-14
    from the maintainer's own dictated geometry after being deferred in
    H4 as not fitting the one-polygon-one-symbol model.

    Every assertion here is on EVALUATED geometry, not on expression
    strings - this appendix has shipped three separate defects that a
    string-level check passed straight through.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    # PT1 (0,10) and PT2 (0,-10) are the ends of the opening, so the
    # centre is the origin and the radius is 10. PT3 sits to the east.
    _CONTAIN = "LineString(0 10, 0 -10, 25 0)"

    # PT1 the centre, PT2 due north of it - radius 10.
    _RETAIN = "LineString(0 0, 0 10)"


    def _evaluate(self, function, wkt):

        expression = QgsExpression(
            "{}(geom_from_wkt('{}'))".format(function, wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_the_two_codes_match_the_table(self):

        self.assertEqual(
            LINE_MEASURE_TYPE_CODES,
            {"contain": "151204", "retain": "151205"}
        )

        self.assertEqual(
            set(LINE_MEASURE_TYPE_LABELS), set(LINE_MEASURE_TYPE_CODES)
        )


    def test_contain_opens_toward_pt3(self):

        # The standard's own layout: "Points 1 and 2 define the
        # endpoints of the semicircle's opening", and the opening
        # "typically faces enemy forces" - which is where PT3, the
        # arrow's own end, is. So the ARC must bulge the other way.
        parts = self._evaluate(
            "mct_contain_arc", self._CONTAIN
        ).asMultiPolyline()

        points = [point for part in parts for point in part]

        self.assertLess(min(point.x() for point in points), -9.5)

        self.assertLessEqual(max(point.x() for point in points), 0.01)


    def test_contain_teeth_point_inward_at_a_third_of_the_radius(self):

        teeth = self._evaluate(
            "mct_contain_teeth", self._CONTAIN
        ).asMultiPolyline()

        # 180 degrees at 18-degree spacing, INCLUSIVE of both ends -
        # "the last tooth in contain on both ends should be at pt1 and
        # pt2, not slightly inside". None is dropped; the one at 90
        # degrees is merely shortened to clear the "C".
        self.assertEqual(len(teeth), 11)

        for end, tooth in ((10.0, teeth[0]), (-10.0, teeth[-1])):

            self.assertAlmostEqual(tooth[0].x(), 0.0, places=6)
            self.assertAlmostEqual(tooth[0].y(), end, places=6)

        # Every tick's own TIP is at 2/3 of the radius; its foot is on
        # the perimeter except for the one shortened to clear the "C".
        for outer, inner in teeth:

            # INWARD - the opposite of Retain's, read off the template
            # at 480 dpi and confirmed by the maintainer.
            self.assertAlmostEqual(
                math.hypot(inner.x(), inner.y()), 10.0 - 10.0 / 3.0,
                places=6
            )

            self.assertLessEqual(
                math.hypot(outer.x(), outer.y()), 10.0 + 1e-6
            )


    def test_contain_arrow_is_perpendicular_with_its_tip_at_the_centre(self):

        # "The tip of the arrowhead will be at the center point of the
        # semicircle's diameter and will project perpendicularly from
        # the line between points 1 and 2." PT3 sets the LENGTH, not
        # the tail's own position.
        #
        # TWO parts, with the "ENY" gap between them - the shaft cannot
        # be masked (nothing inside a geometry generator can), so the
        # gap is cut into it.
        parts = self._evaluate(
            "mct_contain_arrow", self._CONTAIN
        ).asMultiPolyline()

        self.assertEqual(len(parts), 2)

        tail = parts[0][0]
        tip = parts[1][-1]

        self.assertAlmostEqual(tip.x(), 0.0, places=6)
        self.assertAlmostEqual(tip.y(), 0.0, places=6)

        # Perpendicular to the PT1-PT2 chord, which runs north-south.
        self.assertAlmostEqual(tail.y(), 0.0, places=6)
        self.assertAlmostEqual(tail.x(), 25.0, places=6)

        # Both inner ends sit on the axis, symmetric about the shaft's
        # own midpoint at x=12.5.
        self.assertAlmostEqual(
            (parts[0][-1].x() + parts[1][0].x()) / 2.0, 12.5, places=6
        )

        self.assertGreater(parts[0][-1].x(), parts[1][0].x())


    def test_a_pt3_off_the_perpendicular_is_projected_onto_it(self):

        # The arrow may not bend. A PT3 well off the axis still yields
        # a perpendicular arrow, just a shorter one.
        parts = self._evaluate(
            "mct_contain_arrow", "LineString(0 10, 0 -10, 25 40)"
        ).asMultiPolyline()

        tail = parts[0][0]
        tip = parts[1][-1]

        self.assertAlmostEqual(tip.x(), 0.0, places=6)
        self.assertAlmostEqual(tail.y(), 0.0, places=6)
        self.assertAlmostEqual(tail.x(), 25.0, places=6)

        for part in parts:
            for point in part:
                self.assertAlmostEqual(point.y(), 0.0, places=6)


    def test_the_arrowhead_rides_on_the_tip_half_alone(self):

        # A marker at LastVertex fires on the last vertex of EVERY
        # part, so putting the arrowhead on the two-part shaft would
        # drop a second one where the "ENY" gap starts - the bug Retain
        # hit when its own arc was split.
        head = self._evaluate(
            "mct_contain_arrow_head", self._CONTAIN
        ).asPolyline()

        self.assertEqual(len(head), 2)

        self.assertAlmostEqual(head[-1].x(), 0.0, places=6)
        self.assertAlmostEqual(head[-1].y(), 0.0, places=6)

        # It starts where the gap ends, not at the shaft's own tail.
        shaft = self._evaluate(
            "mct_contain_arrow", self._CONTAIN
        ).asMultiPolyline()

        self.assertAlmostEqual(head[0].x(), shaft[1][0].x(), places=6)


    def test_the_eny_gap_never_eats_the_whole_arrow(self):

        # The radius and the arrow length are independent - PT3 sets
        # one, PT1/PT2 the other - so a short arrow on a wide
        # semicircle would otherwise be cut away completely, leaving
        # the arrowhead floating with no shaft.
        parts = self._evaluate(
            "mct_contain_arrow", "LineString(0 100, 0 -100, 2 0)"
        ).asMultiPolyline()

        self.assertEqual(len(parts), 2)

        drawn = sum(
            abs(part[0].x() - part[-1].x()) for part in parts
        )

        self.assertAlmostEqual(drawn, 1.0, places=6)


    def test_retain_sweeps_330_degrees_clockwise_from_pt2(self):

        # 300 drawn, a 60-degree opening. The standard's own text says
        # the opening is 30 degrees; its own picture draws nearer 60,
        # and the maintainer asked for 300. See _RETAIN_ARC_DEG.
        parts = self._evaluate(
            "mct_retain_arc", self._RETAIN
        ).asMultiPolyline()

        def bearing(point):
            return math.degrees(math.atan2(point.y(), point.x()))

        first, last = parts[0], parts[-1]

        self.assertAlmostEqual(bearing(first[0]), 90.0, places=4)

        sweep = (bearing(first[0]) - bearing(last[-1])) % 360

        self.assertAlmostEqual(sweep, 300.0, places=4)

        # Clockwise: the second point's bearing is BELOW the first's.
        self.assertLess(bearing(first[1]), bearing(first[0]))


    def test_retain_teeth_point_outward_at_a_fifth_of_the_radius(self):

        teeth = self._evaluate(
            "mct_retain_teeth", self._RETAIN
        ).asMultiPolyline()

        # 300 degrees at 15-degree spacing inclusive of both ends is
        # 21, less the last, which sits under the arrowhead ("the last
        # tooth near the arrow head can be dropped, it is confusing").
        # The one at the "R" stays, just shortened.
        self.assertEqual(len(teeth), 20)

        # Every tick's own TIP is at 1.2 radii; its foot is on the
        # perimeter except for the one shortened to clear the "R".
        for inner, outer in teeth:

            self.assertAlmostEqual(
                math.hypot(outer.x(), outer.y()), 12.0, places=6
            )

            self.assertGreaterEqual(
                math.hypot(inner.x(), inner.y()), 10.0 - 1e-6
            )


    def test_each_letter_sits_on_the_perimeter(self):

        # ON the arc, not beside it - they cut their own gap in it, so
        # they have to be on it. An earlier build floated them outside
        # and had to give the two different clearances to keep the "R"
        # out of its own teeth; on the perimeter that problem is gone.
        contain = self._evaluate(
            "mct_contain_letter_point", self._CONTAIN
        ).asPoint()

        self.assertAlmostEqual(
            math.hypot(contain.x(), contain.y()), 10.0, places=6
        )

        # Half way round the arc, which bulges away from PT3.
        self.assertAlmostEqual(contain.x(), -10.0, places=6)

        retain = self._evaluate(
            "mct_retain_letter_point", self._RETAIN
        ).asPoint()

        self.assertAlmostEqual(
            math.hypot(retain.x(), retain.y()), 10.0, places=6
        )

        # 180 degrees round the sweep from PT2, which was due north.
        self.assertAlmostEqual(retain.x(), 0.0, places=6)
        self.assertAlmostEqual(retain.y(), -10.0, places=6)


    def test_degenerate_input_returns_the_geometry_untouched(self):

        # PT1 == PT2 (no radius) and a two-point Contain both have to
        # fall through rather than raise mid-render.
        for function, wkt in (
            ("mct_contain_arc", "LineString(0 0, 0 0, 5 5)"),
            ("mct_contain_arc", "LineString(0 10, 0 -10)"),
            ("mct_retain_arc", "LineString(0 0, 0 0)"),
        ):
            self.assertIsNotNone(self._evaluate(function, wkt))


class TestDefensiveLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_layer_builds_with_a_default_measure_type(self):

        layer = create_defensive_control_measures_lines_layer()

        self.assertTrue(layer.isValid())

        default = layer.defaultValueDefinition(
            layer.fields().indexOf("measure_type")
        ).expression()

        self.assertEqual(default, "'contain'")


    def _label_rules(self, layer):

        """
        {description: (settings, format, mask)} - every accessor held
        in its own variable. Chaining off these by-value accessors
        frees the C++ object mid-expression and segfaults, which is
        exactly how the first version of this test died.
        """

        labeling = layer.labeling()
        root = labeling.rootRule()

        rules = {}

        for rule in root.children():

            settings = rule.settings()
            text_format = settings.format()
            mask = text_format.mask()

            rules[rule.description()] = (settings, text_format, mask)

        return rules


    def test_all_three_labels_exist_one_per_text(self):

        layer = create_defensive_control_measures_lines_layer()

        self.assertEqual(
            set(self._label_rules(layer)), {"ENY", "C", "R"}
        )


    def test_no_label_here_carries_a_painted_mask(self):

        # "C" and "R" sit ON the perimeter and "ENY" on the arrow
        # shaft, so each needs a gap - and NONE of the three can be
        # painted by the label engine. Selective Masking does not reach
        # a symbol layer nested inside a geometry generator, and every
        # line in both symbols is one. "ENY" kept a mask on the arrow
        # until the maintainer reported the shaft still running through
        # the text; every gap is cut into the geometry now.
        layer = create_defensive_control_measures_lines_layer()

        rules = self._label_rules(layer)

        for text in ("ENY", "C", "R"):

            with self.subTest(text=text):

                self.assertFalse(rules[text][2].enabled())


    def test_only_eny_is_red(self):

        layer = create_defensive_control_measures_lines_layer()

        rules = self._label_rules(layer)

        self.assertEqual(rules["ENY"][1].color().name(), "#ff0000")

        # "C" and "R" instead follow the affiliation hue, like the arc
        # they sit on - a fixed colour on the format would override it.
        for text in ("C", "R"):

            settings = rules[text][0]

            properties = settings.dataDefinedProperties()

            self.assertIn(
                "affiliation",
                properties.property(
                    QgsPalLayerSettings.Property.Color
                ).expressionString(),
                text
            )


    def test_each_label_is_positioned_on_its_own_generated_geometry(self):

        # None of the three belongs on the feature's own clicked
        # points, so all three take a data-defined position.
        layer = create_defensive_control_measures_lines_layer()

        expected = {
            "ENY": "mct_contain_arrow_midpoint",
            "C": "mct_contain_letter_point",
            "R": "mct_retain_letter_point",
        }

        for text, (settings, _fmt, _mask) in self._label_rules(layer).items():

            properties = settings.dataDefinedProperties()

            for prop in (
                QgsPalLayerSettings.Property.PositionX,
                QgsPalLayerSettings.Property.PositionY,
            ):
                self.assertIn(
                    expected[text],
                    properties.property(prop).expressionString(),
                    text
                )


    def test_each_label_is_filtered_to_its_own_measure_type(self):

        layer = create_defensive_control_measures_lines_layer()

        labeling = layer.labeling()
        root = labeling.rootRule()

        for rule in root.children():

            expected = "retain" if rule.description() == "R" else "contain"

            self.assertEqual(
                rule.filterExpression(),
                "\"measure_type\" = '{}'".format(expected)
            )


    def test_adding_the_layer_inserts_exactly_one(self):

        layer = add_defensive_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertIsNone(
            add_defensive_control_measures_lines_layer(self.iface)
        )

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)), 1
        )


class TestArrowheadsAreOpen(QgisTestCase):

    """
    Neither arrowhead is filled. The only solid triangles on either
    template page are the annotation pointers to the PT. 1/2/3 labels -
    the fourth time this appendix has had to separate those from real
    geometry.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_contains_shaft_and_arrowhead_use_different_geometries(self):

        # The shaft is gapped for "ENY"; the arrowhead must ride on the
        # ungapped tip half, or LastVertex drops a second head at the
        # gap. Pinned at the symbol level, not just the expression one.
        symbol = defensive_control_measures._contain_symbol()

        expressions = {}

        for index in range(symbol.symbolLayerCount()):

            generator = symbol.symbolLayer(index)

            inner = generator.subSymbol()

            if inner is None:
                continue

            expressions[
                generator.geometryExpression()
            ] = inner.symbolLayer(0)

        self.assertIn("mct_contain_arrow($geometry)", expressions)
        self.assertIn("mct_contain_arrow_head($geometry)", expressions)

        self.assertEqual(
            expressions["mct_contain_arrow($geometry)"].id(),
            _CONTAIN_ARROW_SYMBOL_LAYER_ID
        )


    def test_both_arrowheads_are_stroke_only(self):

        for builder in (
            defensive_control_measures._contain_symbol,
            defensive_control_measures._retain_symbol,
        ):

            symbol = builder()

            heads = []

            for index in range(symbol.symbolLayerCount()):

                generator = symbol.symbolLayer(index)

                inner = generator.subSymbol()

                if inner is None:
                    continue

                candidate = inner.symbolLayer(0)

                if not isinstance(candidate, QgsMarkerLineSymbolLayer):
                    continue

                marker = candidate.subSymbol()
                head = marker.symbolLayer(0)

                if isinstance(head, QgsSimpleMarkerSymbolLayer):
                    heads.append(head)

            self.assertEqual(len(heads), 1, builder.__name__)

            head = heads[0]

            self.assertEqual(
                head.shape(),
                QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
                builder.__name__
            )

            self.assertEqual(head.fillColor().alpha(), 0, builder.__name__)


class TestLetterTicksAreShortenedNotRemoved(QgisTestCase):

    """
    Both letters land exactly on a tick - 180 degrees is a whole number
    of steps for both spacings. The manual does not drop that tick, so
    neither does this: its inner end is pulled back by the same amount
    of arc the letter's own gap takes out of the perimeter.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _teeth(self, function, wkt):

        expression = QgsExpression(
            "{}(geom_from_wkt('{}'))".format(function, wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result.asMultiPolyline()


    def test_each_arc_is_broken_where_its_letter_sits(self):

        # The gap is cut into the GEOMETRY, not painted by a mask -
        # QGIS's Selective Masking does not reach symbol layers inside
        # a geometry generator, and every part of these two symbols is
        # generated. Two parts means a real break.
        for function, letter_function, wkt in (
            ("mct_contain_arc", "mct_contain_letter_point",
             "LineString(0 10, 0 -10, 25 0)"),
            ("mct_retain_arc", "mct_retain_letter_point",
             "LineString(0 0, 0 10)"),
        ):

            parts = QgsExpression(
                "{}(geom_from_wkt('{}'))".format(function, wkt)
            ).evaluate().asMultiPolyline()

            self.assertEqual(len(parts), 2, function)

            letter = QgsExpression(
                "{}(geom_from_wkt('{}'))".format(letter_function, wkt)
            ).evaluate().asPoint()

            # Neither part comes near the letter.
            for part in parts:
                for point in part:
                    self.assertGreater(
                        math.hypot(
                            point.x() - letter.x(), point.y() - letter.y()
                        ),
                        0.9,
                        function
                    )


    def test_retains_arrowhead_rides_on_its_own_tail_not_the_split_arc(self):

        # A marker on the last vertex of the GAPPED arc lands on the
        # end of each part - a second arrowhead right beside the "R".
        wkt = "LineString(0 0, 0 10)"

        tail = QgsExpression(
            "mct_retain_arc_end(geom_from_wkt('{}'))".format(wkt)
        ).evaluate().asPolyline()

        self.assertEqual(len(tail), 2)

        parts = QgsExpression(
            "mct_retain_arc(geom_from_wkt('{}'))".format(wkt)
        ).evaluate().asMultiPolyline()

        # It ends where the whole arc ends.
        self.assertAlmostEqual(tail[-1].x(), parts[-1][-1].x(), places=6)
        self.assertAlmostEqual(tail[-1].y(), parts[-1][-1].y(), places=6)


    def test_the_tick_at_each_letter_is_shortened_not_removed(self):

        for teeth_function, letter_function, step, wkt in (
            ("mct_contain_teeth", "mct_contain_letter_point", 18.0,
             "LineString(0 10, 0 -10, 25 0)"),
            ("mct_retain_teeth", "mct_retain_letter_point", 15.0,
             "LineString(0 0, 0 10)"),
        ):

            teeth = self._teeth(teeth_function, wkt)

            letter = QgsExpression(
                "{}(geom_from_wkt('{}'))".format(letter_function, wkt)
            ).evaluate().asPoint()

            # The tick is still there - just standing off the letter.
            nearest = min(
                math.hypot(
                    tooth[0].x() - letter.x(), tooth[0].y() - letter.y()
                )
                for tooth in teeth
            )

            self.assertGreater(nearest, 0.5, teeth_function)
            self.assertLess(nearest, 3.0, teeth_function)


    def test_no_tick_foot_sits_on_a_letter(self):

        for teeth_function, letter_function, wkt in (
            ("mct_contain_teeth", "mct_contain_letter_point",
             "LineString(0 10, 0 -10, 25 0)"),
            ("mct_retain_teeth", "mct_retain_letter_point",
             "LineString(0 0, 0 10)"),
        ):

            letter = QgsExpression(
                "{}(geom_from_wkt('{}'))".format(letter_function, wkt)
            ).evaluate().asPoint()

            for tooth in self._teeth(teeth_function, wkt):

                # The tick's own foot on the perimeter, which is where
                # the letter sits too.
                foot = tooth[0]

                self.assertGreater(
                    math.hypot(
                        foot.x() - letter.x(), foot.y() - letter.y()
                    ),
                    1.0,
                    teeth_function
                )


    def test_retain_has_no_tick_under_its_arrowhead(self):

        wkt = "LineString(0 0, 0 10)"

        parts = QgsExpression(
            "mct_retain_arc(geom_from_wkt('{}'))".format(wkt)
        ).evaluate().asMultiPolyline()

        end = parts[-1][-1]

        for tooth in self._teeth("mct_retain_teeth", wkt):

            foot = tooth[0]

            self.assertGreater(
                math.hypot(foot.x() - end.x(), foot.y() - end.y()), 1.0
            )
