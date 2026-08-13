# -*- coding: utf-8 -*-

"""
Tests for military_symbology/supply_points.py - Table H-XXIII,
Mini-Phase H20 (points only).

Military Cartography Tools
"""

import base64

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsProject)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.supply_points import (
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
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


    def test_the_layer_builds_without_echelon_or_headquarters(self):

        layer = create_supply_points_layer()

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
