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


    def test_the_nineteen_unbuilt_rows_are_recorded_not_forgotten(self):

        # 18 points + 19 areas/lines = the table's own 37.
        self.assertEqual(len(TABLE_H_XXIII_REMAINING), 19)

        self.assertEqual(
            len(POINT_ENTITY_CODES) + len(TABLE_H_XXIII_REMAINING), 37
        )

        self.assertEqual(
            set(POINT_ENTITY_CODES.values()) & set(TABLE_H_XXIII_REMAINING),
            set()
        )


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
