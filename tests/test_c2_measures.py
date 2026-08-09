# -*- coding: utf-8 -*-

"""
Tests for military_symbology/c2_measures.py - the C2 Measures
line/area layers (Boundary, Light Line, Area of Operations, Named/
Target Area of Interest, Airfield Zone), styled via a
QgsRuleBasedRenderer keyed on "measure_type".

**2026-08-09**: module renamed from control_measures.py to
c2_measures.py (and this test file to match) when the project
maintainer asked for Appendix H's control measures to be broken down
into their own H.5.x logical-group layers/modules rather than one
shared pair growing to cover the whole appendix - see c2_measures.py's
own docstring for the full rationale and _control_measure_shared.py for
the helpers now shared with future H-group modules (Maneuver,
Defensive, Offensive, etc.) as they land. Trimmed down 2026-08-09
alongside that rename to only what the appendix-by-appendix completion
plan has actually re-verified so far - Boundary (Mini-Phase H0), then
Light Line/Area of Operations/Named+Target Area of Interest/Airfield
Zone (Mini-Phase H2).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsExpressionContext,
    QgsFeature,
    QgsFontMarkerSymbolLayer,
    QgsGeometry,
    QgsGeometryGeneratorSymbolLayer,
    QgsMarkerLineSymbolLayer,
    QgsPointXY,
    QgsProject,
    QgsSymbolLayer,
    QgsSymbolLayerUtils,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
    QgsVectorLayerUtils,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology import c2_measures
from MilitaryCartographyTools.military_symbology.c2_measures import (
    AFFILIATION_LABELS,
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    ECHELON_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    STATUS_LABELS,
    add_c2_measures_areas_layer,
    add_c2_measures_lines_layer,
    create_c2_measures_areas_layer,
    create_c2_measures_lines_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import AFFILIATIONS


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


class TestCreateC2MeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_c2_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status", "echelon",
                "unique_designation", "far_designation", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_c2_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_measure_type_uses_a_value_map_widget_defaulting_to_boundary(self):

        layer = create_c2_measures_lines_layer()

        idx = layer.fields().indexOf("measure_type")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'boundary'"
        )


    def test_affiliation_uses_a_value_map_widget_defaulting_to_unspecified(self):

        layer = create_c2_measures_lines_layer()

        idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'unspecified'"
        )


    def test_status_uses_a_value_map_widget_defaulting_to_present(self):

        layer = create_c2_measures_lines_layer()

        idx = layer.fields().indexOf("status")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(widget_setup.type(), "ValueMap")
        self.assertEqual(
            widget_setup.config()["map"],
            {label: value for value, label in STATUS_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'present'"
        )


    def test_echelon_uses_a_value_map_widget_defaulting_to_blank(self):

        layer = create_c2_measures_lines_layer()

        idx = layer.fields().indexOf("echelon")

        widget_setup = layer.editorWidgetSetup(idx)

        self.assertEqual(widget_setup.type(), "ValueMap")

        expected_map = {"(Not shown)": ""}
        expected_map.update(
            {label: value for value, label in ECHELON_LABELS.items()}
        )
        self.assertEqual(widget_setup.config()["map"], expected_map)

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "''"
        )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        # Per the actual MIL-STD-2525D standard (Appendix H, section
        # H.5.1.1.1 Standard identity (color rules)): "black, blue
        # (friendly), red (hostile), green (neutral or obstacles), or
        # yellow (unknown ...)" - five distinct colours.
        layer = create_c2_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)
            stroke_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                color, ok = _resolve_stroke_color(
                    stroke_layer, layer, affiliation
                )
                self.assertTrue(ok, (measure_type, affiliation))
                self.assertEqual(
                    color.name(), hex_color, (measure_type, affiliation)
                )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_c2_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {
            rule.filterExpression() for rule in root.children()
        }

        expected = {
            f'"measure_type" = \'{measure_type}\''
            for measure_type in LINE_MEASURE_TYPE_LABELS
        }

        self.assertEqual(filters, expected)


    def test_labelling_is_enabled_and_uses_the_boundary_aware_expression(self):

        layer = create_c2_measures_lines_layer()

        self.assertTrue(layer.labelsEnabled())

        settings = layer.labeling().settings()

        self.assertTrue(settings.isExpression)
        self.assertEqual(
            settings.fieldName,
            c2_measures._BOUNDARY_DESIGNATION_LABEL_EXPRESSION
        )


    def test_line_labels_use_online_placement_not_the_default_above_line(self):

        # QGIS's own default line-label placement flags are AboveLine |
        # MapOrientation - the whole label always sits above the line,
        # never straddling it. Boundary's own two-line near/far label
        # needs to straddle the line (near above, far below the echelon
        # gap), which only happens with OnLine - found by rendering a
        # real boundary feature both ways, not assumed from the flag's
        # own name (see _configure_designation_labeling()'s own comment).
        layer = create_c2_measures_lines_layer()

        settings = layer.labeling().settings()

        self.assertEqual(
            settings.lineSettings().placementFlags(),
            Qgis.LabelLinePlacementFlag.OnLine
        )


    def test_designation_label_is_forced_to_upper_case_per_h_5_4(self):

        # H.5.4 Labeling: "All text labeling shall be in upper case
        # letters" - found unimplemented while re-auditing H.5.1-H.5.4
        # for Mini-Phase H0 (2026-08-09).
        layer = create_c2_measures_lines_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "some_other_type")
        feature.setAttribute("unique_designation", "phl bravo")

        expression = QgsExpression(layer.labeling().settings().fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(result, "PHL BRAVO")


    def test_boundary_label_combines_near_echelon_and_far(self):

        # Table H-III shows the near unit's T/AS above, the Field B
        # echelon amplifier in the line's own gap, and the far unit's
        # T/AS below - built as a single 3-line label (see
        # _boundary_symbol()'s own comment in c2_measures.py for why
        # the echelon glyph is embedded in the label, not a separate
        # symbol layer).
        layer = create_c2_measures_lines_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "boundary")
        feature.setAttribute("unique_designation", "2id (usa)")
        feature.setAttribute("echelon", "division")
        feature.setAttribute("far_designation", "52id (gbr)")

        expression = QgsExpression(layer.labeling().settings().fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(result, "2ID (USA)\nXX\n52ID (GBR)")


    def test_boundary_label_omits_echelon_and_far_lines_when_blank(self):

        layer = create_c2_measures_lines_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "boundary")
        feature.setAttribute("unique_designation", "2id (usa)")

        expression = QgsExpression(layer.labeling().settings().fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(result, "2ID (USA)")


    def test_boundary_label_includes_echelon_line_without_far_designation(self):

        layer = create_c2_measures_lines_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", "boundary")
        feature.setAttribute("unique_designation", "2id (usa)")
        feature.setAttribute("echelon", "command")

        expression = QgsExpression(layer.labeling().settings().fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        self.assertEqual(result, "2ID (USA)\n++")


    def test_boundary_line_is_solid_when_present_and_dashed_when_planned(self):

        # H.5.1.1.3 Status/Table H-I: present=solid, planned=dashed.
        layer = create_c2_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "boundary")
        line_layer = symbol.symbolLayer(0)

        for status, expected_style in (
            ("present", QgsSymbolLayerUtils.decodePenStyle("solid")),
            ("planned", QgsSymbolLayerUtils.decodePenStyle("dash")),
        ):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("status", status)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            style, ok = line_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.StrokeStyle,
                context,
                ""
            )
            self.assertTrue(ok, status)
            self.assertEqual(
                QgsSymbolLayerUtils.decodePenStyle(style), expected_style, status
            )


    def test_boundary_line_symbol_layer_has_a_stable_id(self):

        # Referenced by the label's own mask settings (see
        # test_boundary_label_mask_targets_the_line_symbol_layer() below)
        # so masking knows exactly which symbol layer to cut a hole in.
        layer = create_c2_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "boundary")

        self.assertEqual(symbol.symbolLayerCount(), 1)
        self.assertEqual(
            symbol.symbolLayer(0).id(),
            c2_measures._BOUNDARY_LINE_SYMBOL_LAYER_ID
        )


    def test_boundary_label_mask_targets_the_line_symbol_layer(self):

        # Regression test for three real, wrong attempts at the echelon
        # glyph, all found by the project maintainer rendering a real
        # boundary over a non-white (terrain) background rather than
        # QGIS's own white canvas default: a bordered white square, then
        # a borderless-but-still-solid-fill white square (both plainly
        # "a box" against colour), then a font-glyph halo (QGIS's own
        # real-world font rendering produced a messy white burst rather
        # than a clean hourglass gap - not reproduced in this project's
        # own offscreen renders). QGIS's own Selective Masking is the
        # actual fix - see _boundary_symbol()'s and
        # _configure_designation_labeling()'s own docstrings for the
        # full history.
        layer = create_c2_measures_lines_layer()

        # Chained one-liners here (settings().format().mask()...) have
        # triggered real PyQt/sip segfaults in this test suite before -
        # each intermediate C++ object returned by value must be kept
        # alive in its own Python variable for as long as anything
        # further down the chain is still being read from it.
        settings = layer.labeling().settings()
        text_format = settings.format()
        mask = text_format.mask()

        self.assertTrue(mask.enabled())

        refs = mask.maskedSymbolLayers()
        self.assertTrue(all(ref.layerId() == layer.id() for ref in refs))
        self.assertIn(
            c2_measures._BOUNDARY_LINE_SYMBOL_LAYER_ID,
            {ref.symbolLayerIdV2() for ref in refs}
        )


    def test_boundary_label_repeats_along_the_line(self):

        # Approximates Table H-III's own "the line segment between each
        # pair of anchor points will repeat all information" rule -
        # interval-based (QGIS's own repeat mechanism), not exactly
        # per-segment, but repeats a long boundary's label (and the
        # masked gap around it) multiple times rather than just once -
        # see _BOUNDARY_LABEL_REPEAT_DISTANCE_MM's own comment for why
        # this is an approximation, not an exact match.
        layer = create_c2_measures_lines_layer()

        settings = layer.labeling().settings()

        self.assertGreater(settings.repeatDistance, 0)


    def test_length_km_default_value_recalculates_on_update(self):

        # Reported during manual smoke testing: mct_area_km2/
        # mct_perimeter_km/mct_length_km used to require an @layer
        # expression argument that doesn't reliably populate across
        # every QGIS expression entry point (confirmed: QGIS's
        # in-place attribute-table field calculator doesn't set it,
        # silently producing "nan"). length_km's default value must
        # not depend on @layer, and must actually recalculate
        # (applyOnUpdate) rather than being a one-shot default.
        military_symbology_functions.register()

        try:

            QgsProject.instance().setCrs(WGS84)

            layer = create_c2_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            definition = layer.defaultValueDefinition(idx)

            self.assertEqual(
                definition.expression(),
                "mct_length_km($geometry)"
            )

            self.assertTrue(definition.applyOnUpdate())

            # A 0.01deg line along the equator - real reference value
            # already verified in tests/test_area_perimeter_functions.py:
            # ~1.1132 km.
            geometry = QgsGeometry.fromWkt("LINESTRING(0 0, 0.01 0)")

            feature = QgsVectorLayerUtils.createFeature(layer, geometry)

            self.assertAlmostEqual(
                feature["length_km"],
                1.1131949079327358,
                places=6
            )

        finally:

            military_symbology_functions.unregister()


    def test_light_line_is_solid_when_present_and_dashed_when_planned(self):

        # H.5.1.1.3/Table H-I: present=solid, planned=dashed - same
        # general rule as Boundary's own.
        layer = create_c2_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "light_line")
        line_layer = symbol.symbolLayer(0)

        for status, expected_style in (
            ("present", QgsSymbolLayerUtils.decodePenStyle("solid")),
            ("planned", QgsSymbolLayerUtils.decodePenStyle("dash")),
        ):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("status", status)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            style, ok = line_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.StrokeStyle, context, ""
            )
            self.assertTrue(ok, status)
            self.assertEqual(
                QgsSymbolLayerUtils.decodePenStyle(style), expected_style, status
            )


    def test_light_line_symbol_layer_has_a_stable_id(self):

        # Referenced by the shared Lines-layer label mask (see
        # test_light_line_label_mask_targets_the_line_symbol_layer()
        # below).
        layer = create_c2_measures_lines_layer()

        symbol = _rule_symbol_for(layer, "light_line")

        self.assertEqual(
            symbol.symbolLayer(0).id(),
            c2_measures._LIGHT_LINE_SYMBOL_LAYER_ID
        )


    def test_light_line_label_mask_targets_the_line_symbol_layer(self):

        # Regression test: Light Line's own optional name (H.5.7 - "as
        # often as necessary for clarity") repeats along the line the
        # same way Boundary's own label does (they share one Lines-layer
        # label configuration), but only Boundary's line was originally
        # in the mask's own target list - confirmed wrong by rendering a
        # long Light Line and seeing the name painted flat on top of the
        # line instead of cutting a real gap (the line still showed
        # through the open parts of letters like "C"/"R"). Both lines'
        # own symbol-layer ids must be in the mask's target list.
        layer = create_c2_measures_lines_layer()

        settings = layer.labeling().settings()
        text_format = settings.format()
        mask = text_format.mask()

        target_ids = {ref.symbolLayerIdV2() for ref in mask.maskedSymbolLayers()}

        self.assertEqual(
            target_ids,
            {
                c2_measures._BOUNDARY_LINE_SYMBOL_LAYER_ID,
                c2_measures._LIGHT_LINE_SYMBOL_LAYER_ID,
            }
        )


    def test_light_line_has_an_ll_label_at_each_end_with_no_tick(self):

        # Table H-IV, code 110200 (page 397): a fixed "LL" label above
        # each end (PT1/PT2) - see _end_label_layer()'s own comment in
        # c2_measures.py for why an earlier version also drew a
        # perpendicular tick at each end, and why that was wrong (the
        # template's own up-arrows connecting the labels to the line are
        # diagram callouts, not drawn geometry, the project maintainer's
        # own correction after live-testing).
        layer = create_c2_measures_lines_layer()
        symbol = _rule_symbol_for(layer, "light_line")

        # symbolLayer(0) is the base line; exactly one label per end,
        # no separate tick layer.
        self.assertEqual(symbol.symbolLayerCount(), 3)

        placements_seen = []
        font_layers = []

        for i in (1, 2):

            marker_line_layer = symbol.symbolLayer(i)
            self.assertIsInstance(marker_line_layer, QgsMarkerLineSymbolLayer)
            placements_seen.append(marker_line_layer.placements())

            font_layer = marker_line_layer.subSymbol().symbolLayer(0)
            self.assertIsInstance(font_layer, QgsFontMarkerSymbolLayer)
            font_layers.append(font_layer)

        self.assertEqual(
            set(placements_seen),
            {
                QgsTemplatedLineSymbolLayerBase.Placement.FirstVertex,
                QgsTemplatedLineSymbolLayerBase.Placement.LastVertex,
            }
        )

        for font_layer in font_layers:

            self.assertEqual(font_layer.character(), "LL")

            # Offset must move the label above the line, not below - a
            # real bug the project maintainer caught live (positive Y
            # rendered "LL" below the line instead of above it).
            self.assertLess(font_layer.offset().y(), 0)


class TestCreateC2MeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_has_the_expected_fields(self):

        layer = create_c2_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_c2_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_measure_type_offers_table_h_v_areas_defaulting_to_ao(self):

        # Table H-V (Mini-Phase H2) - Area of Operations, Named/Target
        # Area of Interest, Airfield Zone - see c2_measures.py's
        # own docstring for why every other area measure type is still
        # absent (not yet re-verified against the standard).
        layer = create_c2_measures_areas_layer()

        idx = layer.fields().indexOf("measure_type")

        self.assertEqual(
            layer.editorWidgetSetup(idx).config()["map"],
            {label: value for value, label in AREA_MEASURE_TYPE_LABELS.items()}
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'area_of_operations'"
        )


    def test_affiliation_uses_a_value_map_widget_defaulting_to_unspecified(self):

        layer = create_c2_measures_areas_layer()

        idx = layer.fields().indexOf("affiliation")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'unspecified'"
        )


    def test_status_uses_a_value_map_widget_defaulting_to_present(self):

        # H.5.1.1.3/Table H-I's own text explicitly covers "area control
        # measures", not just linear ones - see
        # create_c2_measures_areas_layer()'s own comment.
        layer = create_c2_measures_areas_layer()

        idx = layer.fields().indexOf("status")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(),
            "'present'"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_c2_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {
            rule.filterExpression() for rule in root.children()
        }

        expected = {
            f'"measure_type" = \'{measure_type}\''
            for measure_type in AREA_MEASURE_TYPE_LABELS
        }

        self.assertEqual(filters, expected)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        # See the Lines layer's own
        # test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1
        # for the standard citation.
        layer = create_c2_measures_areas_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)

            for affiliation, hex_color in expected.items():

                color, ok = _resolve_stroke_color(
                    symbol.symbolLayer(0), layer, affiliation
                )
                self.assertTrue(ok, (measure_type, affiliation))
                self.assertEqual(
                    color.name(), hex_color, (measure_type, affiliation)
                )


    def test_area_outline_is_solid_when_present_and_dashed_when_planned(self):

        layer = create_c2_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)
            outline_layer = symbol.symbolLayer(0)

            for status, expected_style in (
                ("present", QgsSymbolLayerUtils.decodePenStyle("solid")),
                ("planned", QgsSymbolLayerUtils.decodePenStyle("dash")),
            ):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("status", status)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                style, ok = outline_layer.dataDefinedProperties().valueAsString(
                    QgsSymbolLayer.Property.StrokeStyle, context, ""
                )
                self.assertTrue(ok, (measure_type, status))
                self.assertEqual(
                    QgsSymbolLayerUtils.decodePenStyle(style),
                    expected_style,
                    (measure_type, status)
                )


    def _evaluate_area_label(self, layer, measure_type, unique_designation=""):

        # The Areas layer uses QgsRuleBasedLabeling (not
        # QgsVectorLayerSimpleLabeling, which has a single top-level
        # .settings()) - see _configure_area_designation_labeling()'s
        # own docstring for why. Both of its rules share the identical
        # label EXPRESSION (only PLACEMENT differs, per measure_type),
        # so any one rule's settings() gives the same field expression
        # this helper is actually testing.
        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)
        feature.setAttribute("unique_designation", unique_designation)

        first_rule = next(iter(layer.labeling().rootRule().children()))
        field_name = first_rule.settings().fieldName

        expression = QgsExpression(field_name)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_ao_nai_tai_labels_prefix_the_type_abbreviation(self):

        # Table H-V's own examples: "AO BUFFALO", "NAI 1", "TAI YUKON".
        layer = create_c2_measures_areas_layer()

        self.assertEqual(
            self._evaluate_area_label(layer, "area_of_operations", "buffalo"),
            "AO BUFFALO"
        )
        self.assertEqual(
            self._evaluate_area_label(layer, "named_area_of_interest", "1"),
            "NAI 1"
        )
        self.assertEqual(
            self._evaluate_area_label(layer, "target_area_of_interest", "yukon"),
            "TAI YUKON"
        )


    def test_ao_nai_tai_labels_omit_the_name_when_blank(self):

        layer = create_c2_measures_areas_layer()

        self.assertEqual(
            self._evaluate_area_label(layer, "area_of_operations"),
            "AO"
        )


    def test_airfield_zone_label_has_no_type_prefix(self):

        # Airfield Zone's own template has no Field A abbreviation (an
        # icon instead - see _airfield_zone_symbol()'s own comment) -
        # falls through to the plain designation, unlike AO/NAI/TAI.
        layer = create_c2_measures_areas_layer()

        self.assertEqual(
            self._evaluate_area_label(layer, "airfield_zone", "gander"),
            "GANDER"
        )


    def test_airfield_zone_has_a_centred_crossed_runway_icon(self):

        # Corrected 2026-08-09: page 400's own template/example draws
        # two runway lines crossing at an unequal angle, not a symmetric
        # X - see _airfield_zone_symbol()'s own docstring for the
        # live-testing correction from the original "cross2" shape.
        layer = create_c2_measures_areas_layer()
        symbol = _rule_symbol_for(layer, "airfield_zone")

        self.assertEqual(symbol.symbolLayerCount(), 2)

        icon_layer = symbol.symbolLayer(1)
        self.assertIsInstance(icon_layer, QgsGeometryGeneratorSymbolLayer)
        self.assertEqual(
            icon_layer.geometryExpression(),
            "centroid($geometry)"
        )
        self.assertEqual(
            icon_layer.symbolType(),
            Qgis.SymbolType.Marker
        )

        icon_marker = icon_layer.subSymbol()

        self.assertEqual(icon_marker.symbolLayerCount(), 2)

        angles = {
            icon_marker.symbolLayer(i).angle()
            for i in range(icon_marker.symbolLayerCount())
        }

        self.assertEqual(angles, {90, 50})


    def test_airfield_zone_label_is_placed_outside_the_polygon(self):

        # Page 400's own example ("750M") sits just outside the bounded
        # area, unlike AO/NAI/TAI's own labels, which sit inside their
        # own boundary (centred) - a real live-testing-caught mistake,
        # see _configure_area_designation_labeling()'s own docstring.
        layer = create_c2_measures_areas_layer()

        rules_by_filter = {
            rule.filterExpression(): rule
            for rule in layer.labeling().rootRule().children()
        }

        airfield_rule = rules_by_filter['"measure_type" = \'airfield_zone\'']

        self.assertEqual(
            airfield_rule.settings().placement,
            Qgis.LabelPlacement.OutsidePolygons
        )

        other_rule = next(
            rule for filter_expression, rule in rules_by_filter.items()
            if filter_expression != '"measure_type" = \'airfield_zone\''
        )

        self.assertEqual(
            other_rule.settings().placement,
            Qgis.LabelPlacement.OverPoint
        )


    def test_labelling_is_enabled_on_the_designation_field(self):

        layer = create_c2_measures_areas_layer()

        self.assertTrue(layer.labelsEnabled())


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        # See the Lines layer's own
        # test_length_km_default_value_recalculates_on_update() for why
        # this matters (no @layer dependency, applyOnUpdate=True).
        military_symbology_functions.register()

        try:

            QgsProject.instance().setCrs(WGS84)

            layer = create_c2_measures_areas_layer()

            area_idx = layer.fields().indexOf("area_km2")
            perimeter_idx = layer.fields().indexOf("perimeter_km")

            area_definition = layer.defaultValueDefinition(area_idx)
            perimeter_definition = layer.defaultValueDefinition(perimeter_idx)

            self.assertEqual(
                area_definition.expression(),
                "mct_area_km2($geometry)"
            )
            self.assertTrue(area_definition.applyOnUpdate())

            self.assertEqual(
                perimeter_definition.expression(),
                "mct_perimeter_km($geometry)"
            )
            self.assertTrue(perimeter_definition.applyOnUpdate())

            # A 0.01deg x 0.01deg box at the equator - real reference
            # values already verified in
            # tests/test_area_perimeter_functions.py: ~1.2309 km^2 area,
            # ~4.4379 km perimeter.
            geometry = QgsGeometry.fromWkt(
                "POLYGON((0 0, 0 0.01, 0.01 0.01, 0.01 0, 0 0))"
            )

            feature = QgsVectorLayerUtils.createFeature(layer, geometry)

            self.assertAlmostEqual(
                feature["area_km2"],
                1.2309072049932537,
                places=6
            )

            self.assertAlmostEqual(
                feature["perimeter_km"],
                4.43787531568142,
                places=6
            )

        finally:

            military_symbology_functions.unregister()


class TestAddC2MeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_c2_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_c2_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        # Same safety property as unit_layer.py's own add_unit_layer() -
        # this layer's content is hand-drawn operational data, not
        # something safe to silently recreate.
        first = add_c2_measures_lines_layer(self.iface)

        result = add_c2_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_areas_layer_is_never_replaced_if_it_already_exists(self):

        first = add_c2_measures_areas_layer(self.iface)

        result = add_c2_measures_areas_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_c2_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)


class TestAffiliationLabelsMatchSidc(QgisTestCase):

    # A weaker guard than unit_layer.py's own TestVocabularyLabelsMatchSidc
    # (SUPERSET, not equality) since 2026-08-09: AFFILIATION_LABELS
    # legitimately has one value, "unspecified", that sidc.py's own
    # point-symbol AFFILIATIONS does not - see DEFAULT_AFFILIATION's own
    # comment in c2_measures.py for the H.5.1.1.1 citation behind
    # that 5th, control-measure-only colour. This still guards the 4
    # shared values (friend/hostile/neutral/unknown) from drifting.
    def test_affiliation_labels_cover_at_least_sidcs_affiliations(self):

        self.assertTrue(
            set(AFFILIATIONS).issubset(set(AFFILIATION_LABELS))
        )

        self.assertEqual(
            set(AFFILIATION_LABELS) - set(AFFILIATIONS),
            {"unspecified"}
        )


class TestEchelonLabelsMatchSidc(QgisTestCase):

    # Same reasoning as TestAffiliationLabelsMatchSidc above, but the
    # other direction: ECHELON_LABELS is a SUBSET of sidc.py's own
    # ECHELONS (it deliberately excludes "unspecified", which has no
    # Table D-III glyph of its own - see ECHELON_LABELS' own comment).
    def test_echelon_labels_are_a_subset_of_sidcs_echelons(self):

        from MilitaryCartographyTools.military_symbology.sidc import ECHELONS

        self.assertTrue(
            set(ECHELON_LABELS).issubset(set(ECHELONS))
        )

        self.assertEqual(
            set(ECHELONS) - set(ECHELON_LABELS),
            {"unspecified"}
        )
