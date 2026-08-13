# -*- coding: utf-8 -*-

"""
Tests for military_symbology/cbrn_defense.py - Table H-XXI,
Mini-Phase H18 (points only; see that module's own docstring for the
nine area/line rows it deliberately leaves unbuilt).

Military Cartography Tools
"""

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.cbrn_defense import (
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    SHARED_GLYPH_CODES,
    TABLE_H_XXI_REMAINING,
    add_cbrn_defense_points_layer,
    create_cbrn_defense_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

from qgis.core import QgsCoordinateReferenceSystem, QgsExpression, QgsProject

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestCbrnVocabulary(QgisTestCase):

    def test_all_eighteen_point_codes_are_covered(self):

        self.assertEqual(len(POINT_ENTITY_CODES), 18)

        self.assertEqual(
            set(POINT_ENTITY_LABELS), set(POINT_ENTITY_CODES)
        )

        # The table's own 281xxx point block, contiguous apart from the
        # sub-codes the standard itself skips.
        self.assertEqual(
            set(POINT_ENTITY_CODES.values()),
            {
                "281300", "281301", "281400", "281401",
                "281500", "281600", "281700", "281701",
                "281800", "281801", "281802", "281803", "281804",
                "281805", "281806", "281807", "281808", "281809",
            }
        )


    def test_every_entity_is_registered_in_sidc(self):

        for entity, code in POINT_ENTITY_CODES.items():

            with self.subTest(entity=entity):

                self.assertEqual(
                    ENTITIES["control_measure"][entity], code
                )


    def test_the_nine_unbuilt_rows_are_recorded_not_forgotten(self):

        # The whole table is 27 rows; 18 are built here and the other
        # nine are areas/lines. Recording them explicitly is what keeps
        # "not built yet" from looking like "missed".
        self.assertEqual(len(TABLE_H_XXI_REMAINING), 9)

        self.assertEqual(
            len(POINT_ENTITY_CODES) + len(TABLE_H_XXI_REMAINING), 27
        )

        # None of the unbuilt rows is also claimed as built.
        self.assertEqual(
            set(TABLE_H_XXI_REMAINING) & set(POINT_ENTITY_CODES.values()),
            set()
        )


class TestCbrnPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_layer_builds_and_offers_all_eighteen(self):

        layer = create_cbrn_defense_points_layer()

        self.assertTrue(layer.isValid())

        fields = {field.name() for field in layer.fields()}

        self.assertNotIn("echelon", fields)
        self.assertNotIn("headquarters", fields)


    def test_every_entity_renders_a_real_glyph(self):

        # This table added 14 entities to sidc.py at once, so the
        # "present in sidc.py but renders as the unknown icon" defect
        # had 14 chances to slip in.
        for entity, code in POINT_ENTITY_CODES.items():

            with self.subTest(entity=entity):

                sidc = QgsExpression(
                    "mct_build_sidc('friend', '{}', 'control_measure',"
                    " 'unspecified', 'present', false)".format(entity)
                ).evaluate()

                self.assertEqual(len(sidc), 20, sidc)
                self.assertTrue(sidc.isdigit(), sidc)
                self.assertEqual(sidc[10:16], code)

                svg = QgsExpression(
                    "mct_sidc_svg('{}', '', '', 'rgb(0,0,0)', 1.0)"
                    .format(sidc)
                ).evaluate()

                self.assertTrue(str(svg).startswith("base64:"))


    def test_no_two_entities_draw_the_same_glyph_except_the_known_pair(self):

        # Nuclear Event (281500) and Nuclear Fallout Producing Event
        # (281600) are two codes the standard distinguishes but
        # milsymbol draws identically. Pinned so it reads as a known
        # fact about the standard rather than a duplication defect -
        # and so any OTHER accidental collision still fails loudly.
        import base64

        rendered = {}

        for entity, code in POINT_ENTITY_CODES.items():

            sidc = QgsExpression(
                "mct_build_sidc('friend', '{}', 'control_measure',"
                " 'unspecified', 'present', false)".format(entity)
            ).evaluate()

            svg = QgsExpression(
                "mct_sidc_svg('{}', '', '', 'rgb(0,0,0)', 1.0)".format(sidc)
            ).evaluate()

            markup = base64.b64decode(str(svg)[len("base64:"):])

            rendered.setdefault(markup, []).append(code)

        collisions = {
            tuple(sorted(codes))
            for codes in rendered.values() if len(codes) > 1
        }

        self.assertEqual(collisions, {tuple(sorted(SHARED_GLYPH_CODES))})


    def test_the_four_events_left_the_shared_points_layer(self):

        from MilitaryCartographyTools.military_symbology.control_measure_points import (
            _ENTITY_LABELS as _SHARED,
        )

        self.assertEqual(
            set(POINT_ENTITY_LABELS) & set(_SHARED), set()
        )


class TestCbrnLayerInsertion(QgisTestCase):

    """
    Actually CALL add_cbrn_defense_points_layer(iface).

    See test_field_fortification.py's own class of the same shape for
    why: both H17 and H18 shipped their add_* entry point calling the
    wrong helper with the wrong arity, and no test in either module
    ever ran the function the menu item is wired to.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_adding_the_points_layer_inserts_exactly_one(self):

        layer = add_cbrn_defense_points_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)),
            1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        first = add_cbrn_defense_points_layer(self.iface)

        self.assertIsNone(add_cbrn_defense_points_layer(self.iface))

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)

        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(len(self.iface.messageBar().calls), 1)
