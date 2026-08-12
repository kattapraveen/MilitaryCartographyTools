# -*- coding: utf-8 -*-

"""
Tests for military_symbology/target_control_measures.py - the Target
Control Measures line/area layers (Table H-XVII, Mini-Phase H12),
styled via a QgsRuleBasedRenderer keyed on "measure_type". See that
module's own docstring for what's already covered by the pre-existing
point vocabulary and for what's skipped (Rectangular Target - Single
Target, AEGIS only).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsMarkerLineSymbolLayer,
    QgsProject,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.military_symbology.target_control_measures import (
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    LINES_LAYER_NAME,
    LINE_MEASURE_TYPE_LABELS,
    POINTS_LAYER_NAME,
    POINT_ENTITY_LABELS,
    add_target_control_measures_areas_layer,
    add_target_control_measures_lines_layer,
    add_target_control_measures_points_layer,
    create_target_control_measures_areas_layer,
    create_target_control_measures_lines_layer,
    create_target_control_measures_points_layer,
)
from MilitaryCartographyTools.military_symbology.control_measure_points import (
    _ENTITY_LABELS as _CONTROL_MEASURE_POINT_ENTITY_LABELS,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES


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


class TestCreateTargetControlMeasuresLinesLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _label_rules(self, layer):

        """
        Both layers moved from QgsVectorLayerSimpleLabeling to
        QgsRuleBasedLabeling 2026-08-12, when their measure types
        stopped sharing one placement - so there is no single
        layer.labeling().settings() any more. Two rules each, in the
        order appended.

        NOTE settings() returns BY VALUE - hold it rather than
        chaining, or the temporary's C++ object can be collected
        mid-expression and segfault the interpreter.
        """

        root = layer.labeling().rootRule()

        children = root.children()

        self.assertEqual(len(children), 2)

        return children


    def _evaluate_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = self._label_rules(layer)[0].settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_target_control_measures_lines_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "length_km",
            ]
        )


    def test_is_a_line_layer(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Line"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_target_control_measures_lines_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in LINE_MEASURE_TYPE_LABELS
            }
        )


    def test_every_line_type_has_end_ticks(self):

        layer = create_target_control_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 3)

                for i in (1, 2):

                    self.assertIsInstance(
                        symbol.symbolLayer(i),
                        QgsMarkerLineSymbolLayer
                    )


    def test_linear_target_label_is_the_bare_designation(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "linear_target", unique_designation="la2961"
            ),
            "LA2961"
        )

        self.assertEqual(
            self._evaluate_label(layer, "linear_target"),
            ""
        )


    def test_linear_smoke_target_label_appends_smoke(self):

        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "linear_smoke_target", unique_designation="vb1910"
            ),
            "VB1910\nSMOKE"
        )

        # A blank designation stays a blank LINE rather than
        # collapsing the label to one line - see below.
        self.assertEqual(
            self._evaluate_label(layer, "linear_smoke_target"),
            " \nSMOKE"
        )


    def test_final_protective_fire_carries_a_designation_like_smoke(self):

        # 2026-08-12: FPF had no designation at all - it was a bare
        # fixed "FPF". The maintainer asked for one, "same rules as
        # smoke target", which its own example confirms ("QC1968" above
        # the line, "FPF" below).
        layer = create_target_control_measures_lines_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "final_protective_fire", unique_designation="qc1968"
            ),
            "QC1968\nFPF"
        )

        self.assertEqual(
            self._evaluate_label(layer, "final_protective_fire"),
            " \nFPF"
        )


    def test_a_blank_designation_stays_a_blank_line(self):

        # The maintainer's own report on Linear Smoke Target: "in case
        # user does not provide any unique designation, the render
        # overlaps the lines, so maybe default to a ' ' fixed blank
        # space?". Both straddling types draw a two-line label whose
        # first line sits above the line and second below - the OnLine
        # placement flag centres the whole block on the line. Drop the
        # empty first line and the label collapses to ONE line, which
        # OnLine then centres ON the line, striking it through. Keeping
        # a single space preserves the two-line shape.
        layer = create_target_control_measures_lines_layer()

        for measure_type, fixed in (
            ("linear_smoke_target", "SMOKE"),
            ("final_protective_fire", "FPF"),
        ):

            with self.subTest(measure_type=measure_type):

                for designation in (None, ""):

                    label = self._evaluate_label(
                        layer, measure_type, unique_designation=designation
                    )

                    self.assertEqual(label, f" \n{fixed}")
                    self.assertEqual(len(label.split("\n")), 2)


    def test_linear_target_sits_above_the_line_others_straddle_it(self):

        # "Linear target - unique designation should be above the line
        # not on it". Its label is a SINGLE line, and the shared OnLine
        # default centres a single line ON the line - so it needs
        # AboveLine. The other two straddle deliberately (designation
        # above, SMOKE/FPF below), so they keep OnLine.
        layer = create_target_control_measures_lines_layer()

        above_rule, straddling_rule = self._label_rules(layer)

        self.assertEqual(
            above_rule.filterExpression(),
            '"measure_type" = \'linear_target\''
        )

        above_settings = above_rule.settings()

        self.assertEqual(above_settings.placement, Qgis.LabelPlacement.Line)
        self.assertEqual(
            above_settings.lineSettings().placementFlags(),
            Qgis.LabelLinePlacementFlag.AboveLine
        )

        self.assertEqual(
            straddling_rule.filterExpression(),
            '"measure_type" = \'linear_smoke_target\''
            ' OR "measure_type" = \'final_protective_fire\''
        )

        straddling_settings = straddling_rule.settings()

        self.assertEqual(
            straddling_settings.lineSettings().placementFlags(),
            Qgis.LabelLinePlacementFlag.OnLine
        )


    def test_lines_follow_the_shared_status_field(self):

        layer = create_target_control_measures_lines_layer()

        for measure_type in LINE_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)
                base_line = symbol.symbolLayer(0)

                self.assertTrue(
                    base_line.dataDefinedProperties().hasProperty(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )


    def test_line_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_target_control_measures_lines_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        symbol = _rule_symbol_for(layer, "linear_target")
        stroke_layer = symbol.symbolLayer(0)

        for affiliation, hex_color in expected.items():

            with self.subTest(affiliation=affiliation):

                color, ok = _resolve_stroke_color(stroke_layer, layer, affiliation)

                self.assertTrue(ok)
                self.assertEqual(color.name(), hex_color)


    def test_length_km_default_value_recalculates_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_target_control_measures_lines_layer()

            idx = layer.fields().indexOf("length_km")

            self.assertTrue(
                layer.defaultValueDefinition(idx).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestCreateTargetControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _label_rules(self, layer):

        """
        Both layers moved from QgsVectorLayerSimpleLabeling to
        QgsRuleBasedLabeling 2026-08-12, when their measure types
        stopped sharing one placement - so there is no single
        layer.labeling().settings() any more. Two rules each, in the
        order appended.

        NOTE settings() returns BY VALUE - hold it rather than
        chaining, or the temporary's C++ object can be collected
        mid-expression and segfault the interpreter.
        """

        root = layer.labeling().rootRule()

        children = root.children()

        self.assertEqual(len(children), 2)

        return children


    def _evaluate_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = self._label_rules(layer)[0].settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_target_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_target_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_area_target_and_series_labels_are_bare_designations(self):

        layer = create_target_control_measures_areas_layer()

        for measure_type in ("area_target", "series_or_group_of_targets"):

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation="pc9008"
                    ),
                    "PC9008"
                )


    def test_smoke_label_appends_smoke(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "smoke", unique_designation="dt4877"
            ),
            "DT4877\nSMOKE"
        )

        self.assertEqual(
            self._evaluate_label(layer, "smoke"),
            "SMOKE"
        )


    def test_bomb_area_label_is_fixed(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_label(layer, "bomb_area"),
            "BOMB"
        )


    def test_fire_support_area_label_prefixes_fsa(self):

        layer = create_target_control_measures_areas_layer()

        self.assertEqual(
            self._evaluate_label(
                layer, "fire_support_area", unique_designation="green"
            ),
            "FSA GREEN"
        )

        self.assertEqual(
            self._evaluate_label(layer, "fire_support_area"),
            "FSA"
        )


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_target_control_measures_areas_layer()

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


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_target_control_measures_areas_layer()

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


class TestAddTargetControlMeasuresLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_lines_layer_is_created_and_added(self):

        layer = add_target_control_measures_lines_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_created_and_added(self):

        layer = add_target_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_lines_layer_is_never_replaced_if_it_already_exists(self):

        first = add_target_control_measures_lines_layer(self.iface)

        result = add_target_control_measures_lines_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_target_control_measures_lines_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], LINES_LAYER_NAME)


class TestCreateTargetControlMeasuresPointsLayer(QgisTestCase):

    """
    Table H-XVII's own nine point entries, moved here 2026-08-12 out of
    the shared control_measure_points.py layer.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()


    def test_has_the_expected_fields(self):

        layer = create_target_control_measures_points_layer()

        self.assertEqual(
            [field.name() for field in layer.fields()],
            ["affiliation", "entity", "status", "unique_designation"]
        )


    def test_covers_the_tables_own_point_codes(self):

        # Pinned against the standard's own codes, not the dict itself.
        # 240600/250000 are the two parent rows (template "N/A") and are
        # correctly absent.
        # 240603 Target-Recorded is deliberately absent: marked
        # "(AEGIS Only)" in its own cell, and this project ships no
        # AEGIS-only symbols. Removed 2026-08-12 by the sweep that also
        # took out Airfield (131900).
        self.assertEqual(
            {
                ENTITIES["control_measure"][entity]
                for entity in POINT_ENTITY_LABELS
            },
            {
                "240601", "240602", "240900",
                "250100", "250200", "250300", "250400", "250500",
            }
        )

        self.assertNotIn("target_recorded", POINT_ENTITY_LABELS)
        self.assertNotIn("target_recorded", ENTITIES["control_measure"])


    def test_fire_support_station_is_offered_and_renders(self):

        # Reported as "missing". It was neither missing from sidc.py nor
        # broken - it was hard to find in a flat ~44-entry shared
        # dropdown and drew small (see the size test below). Pinned
        # explicitly so a future curation pass can't quietly drop it.
        self.assertIn("fire_support_station", POINT_ENTITY_LABELS)

        self.assertEqual(
            ENTITIES["control_measure"]["fire_support_station"], "240900"
        )

        layer = create_target_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", "fire_support_station")
        feature.setAttribute("status", "present")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_fire_support_station_is_resized_and_re_anchored_on_its_x(self):

        # Its "FSS" text sits OUTSIDE the X, to the right, so the
        # viewBox is 158 wide where its siblings' are 108 - and QGIS
        # reads a marker's size as its WIDTH, so the X drew at about
        # two-thirds their scale. The same asymmetry also puts the X's
        # own centre (x=100, measured off the rendered path) 25 units
        # left of the viewBox centre QGIS anchors on, hence the offset.
        layer = create_target_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        sizes = {}
        offsets = {}

        for entity in POINT_ENTITY_LABELS:

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", entity)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            size, ok = svg_layer.dataDefinedProperties().valueAsDouble(
                QgsSymbolLayer.Property.Size, context, 0.0
            )
            self.assertTrue(ok)
            sizes[entity] = size

            offset, ok = svg_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.Offset, context, ""
            )
            self.assertTrue(ok)
            offsets[entity] = offset

        self.assertAlmostEqual(
            sizes.pop("fire_support_station"), 8.0 * 158.0 / 108.0, places=4
        )
        self.assertEqual(set(sizes.values()), {8.0})

        fss_x, fss_y = offsets.pop("fire_support_station").split(",")

        self.assertAlmostEqual(
            float(fss_x), 8.0 * (158.0 / 108.0) * (25.0 / 158.0), places=3
        )
        self.assertEqual(float(fss_y), 0.0)

        self.assertEqual(set(offsets.values()), {"0,0"})


    def test_only_the_box_and_cone_points_anchor_at_their_tip(self):

        # Firing/Hide/Launch/Reload/Survey Control Point share the
        # box+cone construction whose anchor is the tip at the bottom
        # (viewBox 56 -64 88 168, identical to Point of Departure's).
        # The four target/station icons are centred.
        layer = create_target_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        anchors = {}

        for entity in POINT_ENTITY_LABELS:

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", entity)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            value, ok = svg_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.VerticalAnchor, context, ""
            )

            self.assertTrue(ok)
            anchors[entity] = value

        self.assertEqual(
            {e for e, a in anchors.items() if a == "bottom"},
            {
                "firing_point", "hide_point", "launch_point",
                "reload_point", "survey_control_point",
            }
        )

        self.assertEqual(
            {e for e, a in anchors.items() if a == "center"},
            {
                "point_target", "nuclear_target",
                "fire_support_station",
            }
        )


    def test_every_entity_resolves_to_a_real_rendered_symbol(self):

        layer = create_target_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        for entity in POINT_ENTITY_LABELS:

            with self.subTest(entity=entity):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("affiliation", "friend")
                feature.setAttribute("entity", entity)
                feature.setAttribute("status", "present")

                context = layer.createExpressionContext()
                context.setFeature(feature)

                path, ok = svg_layer.dataDefinedProperties().valueAsString(
                    QgsSymbolLayer.Property.Name, context, ""
                )

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


    def test_the_target_family_left_the_shared_points_layer(self):

        self.assertEqual(
            set(POINT_ENTITY_LABELS)
            & set(_CONTROL_MEASURE_POINT_ENTITY_LABELS),
            set()
        )


    def test_points_layer_is_created_and_added(self):

        layer = add_target_control_measures_points_layer(FakeIface())

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)),
            1
        )
