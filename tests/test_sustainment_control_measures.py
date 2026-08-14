# -*- coding: utf-8 -*-

"""
Tests for military_symbology/sustainment_control_measures.py -
Table H-XXII, Mini-Phase H19.

Military Cartography Tools
"""

import base64
import re

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsProject)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.sustainment_control_measures import (
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_DESIGNATION_SLOTS,
    POINT_ENTITY_LABELS,
    TABLE_H_XXII_NOT_A_SYMBOL,
    add_sustainment_points_layer,
    create_sustainment_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# milsymbol's unknown-icon fallback - a stable fragment of the path it
# draws when handed a SIDC it cannot resolve. Present iff the symbol
# did NOT render.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


class TestSustainmentVocabulary(QgisTestCase):

    def test_the_sixteen_codes_match_the_table(self):

        self.assertEqual(len(POINT_ENTITY_CODES), 16)

        self.assertEqual(set(POINT_ENTITY_LABELS), set(POINT_ENTITY_CODES))

        # Table H-XXII's own 3201xx-3216xx block, read off the printed
        # CONTROL MEASURE column.
        self.assertEqual(
            set(POINT_ENTITY_CODES.values()),
            {
                "320100", "320200", "320300", "320400", "320500",
                "320600", "320700", "320800", "320900", "321000",
                "321100", "321200", "321300", "321400", "321500",
                "321600",
            }
        )


    def test_the_seventeenth_row_is_recorded_as_not_a_symbol(self):

        # 16 built + 1 parent row = the table's own 17. Recorded rather
        # than dropped, so the arithmetic can be checked against the
        # printed table without re-reading it.
        self.assertEqual(set(TABLE_H_XXII_NOT_A_SYMBOL), {"320000"})

        self.assertEqual(
            len(POINT_ENTITY_CODES) + len(TABLE_H_XXII_NOT_A_SYMBOL),
            17
        )


    def test_every_entity_is_registered_in_sidc(self):

        for entity, code in POINT_ENTITY_CODES.items():

            self.assertEqual(
                ENTITIES["control_measure"].get(entity), code, entity
            )


class TestSustainmentPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_layer_builds_without_echelon_or_headquarters(self):

        layer = create_sustainment_points_layer()

        self.assertTrue(layer.isValid())

        fields = {field.name() for field in layer.fields()}

        self.assertNotIn("echelon", fields)
        self.assertNotIn("headquarters", fields)

        # Field T, which every row of the table carries.
        self.assertIn("unique_designation", fields)


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


    def test_no_two_entities_draw_the_same_glyph(self):

        drawn = {}

        for entity in POINT_ENTITY_LABELS:

            svg = base64.b64decode(
                QgsExpression(
                    "mct_sidc_svg(mct_build_sidc('friend', '{}', "
                    "'control_measure', 'unspecified', 'present', "
                    "false))".format(entity)
                ).evaluate()[len("base64:"):]
            ).decode("utf-8")

            self.assertNotIn(
                svg, drawn,
                f"{entity} draws the same glyph as {drawn.get(svg)}"
            )

            drawn[svg] = entity


    def _render(self, entity, text=None, slot=None):

        """The SVG mct_sidc_svg returns for one entity, decoded."""

        arguments = (
            "mct_build_sidc('friend', '{}', 'control_measure', "
            "'unspecified', 'present', false)".format(entity)
        )

        if text is not None:

            arguments += ", '{}', '{}'".format(
                text,
                slot or POINT_DESIGNATION_SLOTS.get(
                    entity, "uniqueDesignation"
                )
            )

        expression = QgsExpression(f"mct_sidc_svg({arguments})")

        path = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def test_the_designation_goes_to_field_t1_not_field_t(self):

        # Table H-XXII draws the designation INSIDE the lower part of
        # the box (the "T1" box on every template; "4077" under "AXP",
        # "MNSE" under "ASP" in the standard's own examples), not in
        # the Field T box outside it. Passing a slot an icon does not
        # define draws NOTHING, silently, which is why this asserts on
        # the rendered SVG.
        #
        # (100, 30) is milsymbol's own T1 anchor here and (150, -30)
        # its Field T one, both read off the rendered markup.
        self.assertEqual(len(POINT_DESIGNATION_SLOTS), 15)

        for entity in POINT_DESIGNATION_SLOTS:

            with self.subTest(entity=entity):

                svg = self._render(entity, "4077")

                designation = re.search(
                    r'<text[^>]*>4077</text>', svg
                ).group(0)

                self.assertIn('x="100"', designation)
                self.assertNotIn('x="150"', designation)


    def test_ambulance_exchange_point_can_draw_no_designation_at_all(self):

        # Not an oversight, and not fixable here: its own template has
        # a T1 box and the standard's own example fills it with "4077",
        # but milsymbol defines no text option for this icon - neither
        # T nor T1 - so nothing reaches it. Pinned so the day milsymbol
        # grows one, this test fails and says so.
        self.assertNotIn(
            "ambulance_exchange_point", POINT_DESIGNATION_SLOTS
        )

        for slot in ("uniqueDesignation", "uniqueDesignation1"):

            with self.subTest(slot=slot):

                self.assertNotIn(
                    "4077",
                    self._render("ambulance_exchange_point", "4077", slot)
                )


    def test_adding_the_layer_inserts_exactly_one(self):

        layer = add_sustainment_points_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)), 1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        first = add_sustainment_points_layer(self.iface)

        self.assertIsNone(add_sustainment_points_layer(self.iface))

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
        self.assertEqual(len(self.iface.messageBar().calls), 1)
