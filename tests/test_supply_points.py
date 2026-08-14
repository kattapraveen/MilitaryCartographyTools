# -*- coding: utf-8 -*-

"""
Tests for military_symbology/supply_points.py - Table H-XXIII,
Mini-Phase H20 (points only).

Military Cartography Tools
"""

import base64
import re

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsFeature, QgsProject, QgsSymbolLayer)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.supply_points import (
    add_supply_routes_lines_layer,
    create_supply_routes_lines_layer,
    LINES_LAYER_NAME,
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_CODES,
    AREA_MEASURE_TYPE_LABELS,
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    add_sustainment_areas_layer,
    create_sustainment_areas_layer,
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    POINT_DESIGNATION_SLOTS,
    SUPPLY_CLASS_FIELD,
    SUPPLY_CLASS_LABELS,
    SHARED_GLYPH_CODES,
    TABLE_H_XXIII_REMAINING,
    add_supply_points_layer,
    create_supply_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# milsymbol's unknown-icon fallback - a stable fragment of the path it
# draws when handed a SIDC it cannot resolve. Present iff the symbol
# did NOT render.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


class TestSupplyPointVocabulary(QgisTestCase):

    def test_the_eighteen_point_codes_match_the_table(self):

        self.assertEqual(len(POINT_ENTITY_CODES), 18)

        self.assertEqual(set(POINT_ENTITY_LABELS), set(POINT_ENTITY_CODES))

        # General Supply Point, its sixteen classes, and Medical Supply
        # Point - one contiguous 3217xx block plus 321800.
        self.assertEqual(
            set(POINT_ENTITY_CODES.values()),
            {"321700"}
            | {"3217%02d" % n for n in range(1, 17)}
            | {"321800"}
        )


    def test_the_nato_and_us_classes_stay_distinct(self):

        # They share roman numerals and mean different things - the
        # NATO rows cite STANAG 2961, the US rows do not - so a key or
        # label that dropped the prefix would silently merge two
        # vocabularies.
        nato = {e for e in POINT_ENTITY_CODES if "nato" in e}
        us = {e for e in POINT_ENTITY_CODES if "_us_" in e}

        self.assertEqual(len(nato), 6)
        self.assertEqual(len(us), 10)
        self.assertEqual(nato & us, set())

        for entity in nato:
            self.assertTrue(POINT_ENTITY_LABELS[entity].startswith("NATO "))

        for entity in us:
            self.assertTrue(POINT_ENTITY_LABELS[entity].startswith("US "))


    def test_every_row_of_the_table_is_accounted_for(self):

        # 18 points + 8 supply routes + 7 sustainment areas + 4 still
        # unbuilt = the table's own 37. The routes and areas were built
        # 2026-08-14 and left the unbuilt list then; this arithmetic is
        # what stops one going missing between the two.
        self.assertEqual(len(TABLE_H_XXIII_REMAINING), 4)

        self.assertEqual(
            len(POINT_ENTITY_CODES)
            + len(LINE_MEASURE_TYPE_CODES)
            + len(AREA_MEASURE_TYPE_CODES)
            + len(TABLE_H_XXIII_REMAINING),
            37
        )

        built = (
            set(POINT_ENTITY_CODES.values())
            | set(LINE_MEASURE_TYPE_CODES.values())
            | set(AREA_MEASURE_TYPE_CODES.values())
        )

        self.assertEqual(built & set(TABLE_H_XXIII_REMAINING), set())


    def test_every_entity_is_registered_in_sidc(self):

        for entity, code in POINT_ENTITY_CODES.items():

            self.assertEqual(
                ENTITIES["control_measure"].get(entity), code, entity
            )


class TestSupplyPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _render(self, entity, text=None, slot=None):

        """The SVG mct_sidc_svg returns for one entity, decoded."""

        arguments = (
            "mct_build_sidc('friend', '{}', 'control_measure', "
            "'unspecified', 'present', false)".format(entity)
        )

        if text is not None:

            arguments += ", '{}', '{}'".format(
                text, slot or POINT_DESIGNATION_SLOTS.get(
                    entity, "uniqueDesignation"
                )
            )

        expression = QgsExpression(f"mct_sidc_svg({arguments})")

        path = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def test_the_layer_builds_without_echelon_or_headquarters(self):

        layer = create_supply_points_layer()

        self.assertTrue(layer.isValid())

        fields = {field.name() for field in layer.fields()}

        self.assertNotIn("echelon", fields)
        self.assertNotIn("headquarters", fields)

        # Field T, which every row of the table carries.
        self.assertIn("unique_designation", fields)


    def test_the_designation_goes_to_field_t1_not_field_t(self):

        # Table H-XXIII draws the designation INSIDE the lower part of
        # the supply box (the "T1" box on every template; "1AD",
        # "3SUST" in the standard's own examples), not in the Field T
        # box outside it. milsymbol exposes that position as
        # `uniqueDesignation1`, and passing it to an icon that does not
        # define the slot draws NOTHING AT ALL, silently - which is why
        # this asserts on the rendered SVG rather than on the map.
        #
        # (100, 20) is milsymbol's own T1 anchor and (150, -30) its
        # Field T one, both read off the rendered markup.
        for entity in POINT_DESIGNATION_SLOTS:

            with self.subTest(entity=entity):

                svg = self._render(entity, "1AD")

                self.assertIn("1AD", svg)

                designation = re.search(
                    r'<text[^>]*>1AD</text>', svg
                ).group(0)

                self.assertIn('x="100"', designation)
                self.assertNotIn('x="150"', designation)


    def test_the_multiple_class_point_draws_both_of_its_own_fields(self):

        # 321706 is the one icon here milsymbol defines NO text option
        # for - not T, not T1 - so BOTH its amplifiers are drawn by
        # this plugin, at positions lifted from the siblings milsymbol
        # does define (321701-321705 for the class numeral, 321700 for
        # T1). Without that, its box drew bare whatever was typed.
        entity = "supply_point_nato_multiple_class"

        for slot in ("uniqueDesignation", "uniqueDesignation1"):

            with self.subTest(slot=slot):

                self.assertNotIn(
                    "ISAF", self._render(entity, "ISAF", slot)
                )

        svg = self._render(entity, "ISAF")

        self.assertIn("ISAF", svg)

        self.assertEqual(POINT_DESIGNATION_SLOTS[entity], "mctFieldT1")

        # And the class numbers, in the A field above it.
        with_class = base64.b64decode(
            QgsExpression(
                "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                "'control_measure', 'unspecified', 'present', false), "
                "'ISAF', 'mctFieldT1', '', '', 'I/III/V', 'mctFieldA')"
                .format(entity)
            ).evaluate()[len("base64:"):]
        ).decode("utf-8")

        class_text = re.search(
            r'<text[^>]*>I/III/V</text>', with_class
        ).group(0)

        designation = re.search(
            r'<text[^>]*>ISAF</text>', with_class
        ).group(0)

        # Both centred in the box, the class ABOVE the designation.
        self.assertIn('x="100"', class_text)
        self.assertIn('x="100"', designation)

        self.assertLess(
            float(re.search(r'y="(-?[\d.]+)"', class_text).group(1)),
            float(re.search(r'y="(-?[\d.]+)"', designation).group(1))
        )


    def test_a_long_class_combination_is_shrunk_to_fit_the_box(self):

        entity = "supply_point_nato_multiple_class"

        def class_font_size(text):

            svg = base64.b64decode(
                QgsExpression(
                    "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                    "'control_measure', 'unspecified', 'present', "
                    "false), '', '', '', '', '{}', 'mctFieldA')"
                    .format(entity, text)
                ).evaluate()[len("base64:"):]
            ).decode("utf-8")

            element = re.search(
                r'<text[^>]*>{}</text>'.format(re.escape(text)), svg
            ).group(0)

            return float(
                re.search(r'font-size="([\d.]+)"', element).group(1)
            )

        # "I" fits at the sibling icons' own 45 and is left alone; a
        # three-class combination does not and comes down.
        self.assertEqual(class_font_size("I"), 45.0)

        self.assertLess(class_font_size("I/III/V"), 45.0)

        self.assertLess(
            class_font_size("III/IV/V"), class_font_size("I/III/V")
        )


    def test_the_supply_class_dropdown_offers_what_the_template_holds(self):

        # The template's own A field reads A/A1/A2 - three sub-fields,
        # so at most three classes. Every combination of one, two or
        # three of the five in ascending order, plus ALL: 26 options,
        # and deliberately no four-class one.
        self.assertEqual(len(SUPPLY_CLASS_LABELS), 26)

        self.assertIn("ALL", SUPPLY_CLASS_LABELS)

        self.assertIn("I/III/V", SUPPLY_CLASS_LABELS)

        self.assertNotIn("I/II/III/IV", SUPPLY_CLASS_LABELS)

        for combination in SUPPLY_CLASS_LABELS:

            if combination == "ALL":
                continue

            classes = combination.split("/")

            self.assertLessEqual(len(classes), 3, combination)

            self.assertEqual(len(set(classes)), len(classes), combination)


    def test_the_supply_class_field_exists_and_defaults_to_all(self):

        layer = create_supply_points_layer()

        self.assertIn(
            SUPPLY_CLASS_FIELD["name"],
            [field.name() for field in layer.fields()]
        )

        index = layer.fields().indexOf(SUPPLY_CLASS_FIELD["name"])

        self.assertEqual(
            layer.defaultValueDefinition(index).expression(), "'ALL'"
        )

        setup = layer.editorWidgetSetup(index)

        self.assertEqual(setup.type(), "ValueMap")

        self.assertEqual(len(setup.config()["map"]), 26)


    def test_only_the_multiple_class_point_draws_the_supply_class(self):

        # The field is on the whole layer - QGIS has no per-value field
        # visibility worth the complexity - so the expression is what
        # keeps the other seventeen from drawing it.
        layer = create_supply_points_layer()

        symbol_layer = layer.renderer().symbol().symbolLayer(0)

        properties = symbol_layer.dataDefinedProperties()

        expression = properties.property(
            QgsSymbolLayer.Property.Name
        ).expressionString()

        self.assertIn("'mctFieldA'", expression)

        for entity, expected in (
            ("supply_point_nato_multiple_class", "I/III/V"),
            ("general_supply_point", ""),
            ("supply_point_us_class_i", ""),
        ):

            with self.subTest(entity=entity):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("entity", entity)
                feature.setAttribute("affiliation", "friend")
                feature.setAttribute("status", "present")
                feature.setAttribute("supply_class", "I/III/V")

                context = layer.createExpressionContext()
                context.setFeature(feature)

                path, ok = properties.valueAsString(
                    QgsSymbolLayer.Property.Name, context
                )

                self.assertTrue(ok)

                svg = base64.b64decode(
                    path[len("base64:"):]
                ).decode("utf-8")

                if expected:
                    self.assertIn(expected, svg)
                else:
                    self.assertNotIn("I/III/V", svg)


    def test_the_us_classes_keep_field_t_because_they_have_no_t1(self):

        # Not an oversight: none of 321707-321716 defines
        # `uniqueDesignation1` at all, so Field T is the only text
        # position those ten icons have. Reversing this would draw
        # nothing rather than moving anything, so it is pinned here.
        us_classes = [
            entity for entity in POINT_ENTITY_LABELS
            if entity.startswith("supply_point_us_class_")
        ]

        self.assertEqual(len(us_classes), 10)

        for entity in us_classes:

            with self.subTest(entity=entity):

                self.assertNotIn(entity, POINT_DESIGNATION_SLOTS)

                self.assertNotIn(
                    "1AD", self._render(entity, "1AD", "uniqueDesignation1")
                )

                self.assertIn(
                    "1AD", self._render(entity, "1AD")
                )


    def test_every_entity_renders_a_real_glyph(self):

        # The defect class this project has hit repeatedly: an entity
        # whose SIDC does not resolve still returns a perfectly
        # well-formed base64 path, drawing milsymbol's unknown icon.
        for entity in POINT_ENTITY_LABELS:

            expression = QgsExpression(
                "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                "'control_measure', 'unspecified', 'present', false))".format(
                    entity
                )
            )

            path = expression.evaluate()

            self.assertFalse(
                expression.hasEvalError(), expression.evalErrorString()
            )

            svg = base64.b64decode(
                path[len("base64:"):]
            ).decode("utf-8")

            self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg, entity)


    def test_no_two_entities_draw_the_same_glyph_except_the_known_pair(self):

        # NATO Multiple Supply Class Point (321706) really does draw
        # the plain supply-point box, same as General Supply Point
        # (321700) - its box carries no icon, only a user-typed A field
        # ("I/III/V" in the table's own example). Asserted as the ONLY
        # collision so the known fact cannot hide an accidental one.
        drawn = {}
        collisions = set()

        for entity in POINT_ENTITY_LABELS:

            svg = base64.b64decode(
                QgsExpression(
                    "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                    "'control_measure', 'unspecified', 'present', "
                    "false))".format(entity)
                ).evaluate()[len("base64:"):]
            ).decode("utf-8")

            if svg in drawn:
                collisions.add(
                    frozenset(
                        (POINT_ENTITY_CODES[entity],
                         POINT_ENTITY_CODES[drawn[svg]])
                    )
                )

            drawn[svg] = entity

        self.assertEqual(collisions, {frozenset(SHARED_GLYPH_CODES)})


    def test_adding_the_layer_inserts_exactly_one(self):

        layer = add_supply_points_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)), 1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        first = add_supply_points_layer(self.iface)

        self.assertIsNone(add_supply_points_layer(self.iface))

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
        self.assertEqual(len(self.iface.messageBar().calls), 1)


class TestSupplyRoutesLinesLayer(QgisTestCase):

    """
    Table H-XXIII's own eight supply routes (330300-330403).

    Eight codes but ONE construction: the MSR and ASR halves differ
    only in the abbreviation, and the three traffic variants only in
    which arrows ride above the line. These tests are written against
    that, so a new variant that breaks the pattern fails loudly.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _symbol(self, layer, measure_type):

        rule = next(
            rule for rule in layer.renderer().rootRule().children()
            if rule.filterExpression()
            == f'"measure_type" = \'{measure_type}\''
        )

        return rule.symbol()


    def test_the_eight_codes_match_the_table(self):

        self.assertEqual(
            set(LINE_MEASURE_TYPE_CODES.values()),
            {
                "330300", "330301", "330302", "330303",
                "330400", "330401", "330402", "330403",
            }
        )

        self.assertEqual(
            set(LINE_MEASURE_TYPE_LABELS), set(LINE_MEASURE_TYPE_CODES)
        )


    def test_each_variant_carries_the_arrows_the_table_draws(self):

        layer = create_supply_routes_lines_layer()

        # Symbol layer 0 is the road itself; the rest are arrows.
        for measure_type, expected in (
            ("msr", 0),
            ("asr", 0),
            ("msr_one_way", 1),
            ("asr_one_way", 1),
            ("msr_two_way", 2),
            ("msr_alternating", 1),
        ):

            with self.subTest(measure_type=measure_type):

                symbol = self._symbol(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), expected + 1)


    def test_two_way_puts_the_forward_arrow_on_top(self):

        # The standard's own example ("MSR SUMMER") draws the arrow
        # WITH the direction of travel above the one against it. The
        # first build had them the other way round.
        layer = create_supply_routes_lines_layer()

        symbol = self._symbol(layer, "msr_two_way")

        arrows = []

        for index in range(1, symbol.symbolLayerCount()):

            marker_line = symbol.symbolLayer(index)

            expression = marker_line.subSymbol().symbolLayer(
                0
            ).dataDefinedProperties().property(
                QgsSymbolLayer.Property.Name
            ).expressionString()

            arrows.append((marker_line.offset(), expression))

        # A negative offset is to the LEFT of travel, which is above
        # the line - so the more negative one is the higher.
        inner, outer = sorted(arrows, key=lambda arrow: -arrow[0])

        self.assertIn("'backward'", inner[1])
        self.assertIn("'forward'", outer[1])

        self.assertLess(outer[0], inner[0])


    def test_the_label_clears_however_many_arrows_are_stacked(self):

        layer = create_supply_routes_lines_layer()

        offsets = {}

        for rule in layer.labeling().rootRule().children():

            settings = rule.settings()

            offsets[rule.description()] = settings.yOffset

        # Every label sits ABOVE the line, and the more arrows a
        # variant stacks the further out its own label has to go.
        for measure_type, offset in offsets.items():
            self.assertLess(offset, 0.0, measure_type)

        self.assertLess(offsets["msr_two_way"], offsets["msr_one_way"])
        self.assertLess(offsets["msr_one_way"], offsets["msr"])


    def test_the_label_is_the_abbreviation_plus_field_t(self):

        layer = create_supply_routes_lines_layer()

        settings = layer.labeling().rootRule().children()[0].settings()

        expression = QgsExpression(settings.fieldName)

        for measure_type, designation, expected in (
            ("msr", "CAMEL", "MSR CAMEL"),
            ("asr_two_way", "winter", "ASR WINTER"),
            ("msr_alternating", "", "MSR"),
        ):

            with self.subTest(measure_type=measure_type):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("measure_type", measure_type)
                feature.setAttribute("unique_designation", designation)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                self.assertEqual(expression.evaluate(context), expected)


    def test_the_alternating_glyph_keeps_a_shaft_either_side_of_alt(self):

        # The first build derived the text size from the glyph's own
        # length, so lengthening the assembly enlarged the word too and
        # the heads stayed pressed against it. The size is explicit now.
        import base64
        import re

        svg = base64.b64decode(
            QgsExpression(
                "mct_supply_route_arrow_svg('rgb(0,0,0)', 20, 0.4, "
                "'alternating', 'ALT', 3.4)"
            ).evaluate()[len("base64:"):]
        ).decode("utf-8")

        self.assertIn(">ALT</text>", svg)

        shaft = re.search(
            r"M (-?[\d.]+),0 L (-?[\d.]+),0 M (-?[\d.]+),0 L (-?[\d.]+),0",
            svg
        )

        left_start, left_end, right_start, right_end = (
            float(value) for value in shaft.groups()
        )

        # A real gap in the middle for the word...
        self.assertLess(left_end, right_start)

        # ...and real shaft outside it, on both sides.
        self.assertGreater(left_end - left_start, 1.0)
        self.assertGreater(right_end - right_start, 1.0)


    def test_adding_the_layer_inserts_exactly_one(self):

        self.assertIsNotNone(add_supply_routes_lines_layer(self.iface))

        self.assertIsNone(add_supply_routes_lines_layer(self.iface))

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(LINES_LAYER_NAME)), 1
        )


class TestSustainmentAreasLayer(QgisTestCase):

    """
    Table H-XXIII's own seven sustainment areas (310100-310700).

    All seven share one construction; what differs is only what the
    caption says and whether it carries Field T. Both of those were
    read off the templates rather than derived from the measure's name,
    because the obvious derivation is wrong twice - see _AREA_CAPTIONS.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _label(self, layer, measure_type, designation=""):

        settings = layer.labeling().settings()

        expression = QgsExpression(settings.fieldName)

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)
        feature.setAttribute("unique_designation", designation)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_the_seven_codes_match_the_table(self):

        self.assertEqual(
            set(AREA_MEASURE_TYPE_CODES.values()),
            {"310100", "310200", "310300",
             "310400", "310500", "310600", "310700"}
        )

        self.assertEqual(
            set(AREA_MEASURE_TYPE_LABELS), set(AREA_MEASURE_TYPE_CODES)
        )


    def test_the_captions_are_the_templates_own_lettering(self):

        # The support areas abbreviate; the holding areas spell their
        # name out on two lines. "DHA"/"EPWHA"/"RHA" appear nowhere in
        # the standard and would have been an invention.
        layer = create_sustainment_areas_layer()

        for measure_type, expected in (
            ("detainee_holding_area", "DETAINEE\nHOLDING AREA"),
            ("epw_holding_area", "EPW\nHOLDING AREA"),
            ("refugee_holding_area", "REFUGEE\nHOLDING AREA"),
            ("farp", "FARP"),
            ("regimental_support_area", "RSA"),
            ("brigade_support_area", "BSA"),
            ("division_support_area", "DSA"),
        ):

            with self.subTest(measure_type=measure_type):

                self.assertEqual(self._label(layer, measure_type), expected)


    def test_only_the_four_with_a_t_box_take_a_designation(self):

        # The three support areas are drawn bare in both the TEMPLATE
        # and EXAMPLE columns - no T box at all - so a designation typed
        # on one must not appear.
        layer = create_sustainment_areas_layer()

        for measure_type, expected in (
            ("detainee_holding_area", "DETAINEE\nHOLDING AREA\nGB"),
            ("farp", "FARP\n2AVN"),
            ("brigade_support_area", "BSA"),
            ("division_support_area", "DSA"),
        ):

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._label(layer, measure_type, "gb"
                                if measure_type == "detainee_holding_area"
                                else "2AVN"),
                    expected
                )


    def test_a_blank_designation_leaves_no_trailing_line(self):

        # Otherwise the caption ends in an empty line and centres
        # visibly high inside the area.
        layer = create_sustainment_areas_layer()

        self.assertEqual(
            self._label(layer, "farp", ""), "FARP"
        )


    def test_the_layer_is_a_polygon_layer_with_the_expected_fields(self):

        layer = create_sustainment_areas_layer()

        self.assertTrue(layer.isValid())

        self.assertEqual(
            [field.name() for field in layer.fields()],
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2",
            ]
        )


    def test_adding_the_layer_inserts_exactly_one(self):

        self.assertIsNotNone(add_sustainment_areas_layer(self.iface))

        self.assertIsNone(add_sustainment_areas_layer(self.iface))

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)), 1
        )
