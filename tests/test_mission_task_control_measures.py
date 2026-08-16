# -*- coding: utf-8 -*-

"""
Tests for military_symbology/mission_task_control_measures.py -
Table H-XXIV, Mini-Phase H21 (points only).

Military Cartography Tools
"""

import base64

import re

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsExpressionContext, QgsFeature, QgsProject,
                       QgsSymbolLayer)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.mission_task_control_measures import (
    POINTS_LAYER_NAME,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    POINT_MARKER_SIZE_SCALES,
    LINE_MEASURE_TYPE_CODES,
    LINE_MEASURE_TYPE_LABELS,
    TABLE_H_XXIV_REMAINING,
    add_mission_task_points_layer,
    create_mission_task_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# milsymbol's unknown-icon fallback - a stable fragment of the path it
# draws when handed a SIDC it cannot resolve. Present iff the symbol
# did NOT render.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


class TestMissionTaskVocabulary(QgisTestCase):

    def test_only_the_three_point_tasks_are_built(self):

        # Destroy, Interdict and Neutralize are the only rows of Table
        # H-XXIV whose DRAW RULES ask for ONE anchor point and a
        # centred glyph. Every other row is a multi-anchor arrow or
        # bracket, and milsymbol has an icon for none of them.
        self.assertEqual(
            POINT_ENTITY_CODES,
            {
                "destroy_point": "340900",
                "interdict_point": "341400",
                "neutralize_point": "341600",
            }
        )


    def test_the_twenty_six_unbuilt_rows_are_recorded_not_forgotten(self):

        # 3 points + 26 others = the table's own 29.
        # 3 points + 7 line tasks + 19 still unbuilt = the table's own
        # 29 rows. This arithmetic is what keeps a row from going
        # missing between builds - and what caught the remaining list
        # still claiming the seven built lines were unbuilt.
        self.assertEqual(len(TABLE_H_XXIV_REMAINING), 19)

        self.assertEqual(
            len(POINT_ENTITY_CODES)
            + len(LINE_MEASURE_TYPE_CODES)
            + len(TABLE_H_XXIV_REMAINING),
            29
        )

        # Nothing is claimed as both built and unbuilt.
        self.assertEqual(
            set(LINE_MEASURE_TYPE_CODES.values())
            & set(TABLE_H_XXIV_REMAINING),
            set()
        )

        self.assertEqual(
            set(POINT_ENTITY_CODES.values()) & set(TABLE_H_XXIV_REMAINING),
            set()
        )


    def test_the_task_names_that_clash_are_keyed_by_code_everywhere(self):

        # Several mission tasks share a NAME with an obstacle effect or
        # maneuver control measure that has its own different code and
        # drawn form - conflating the two is a defect this project has
        # been reported for once already. Both the built record and the
        # unbuilt one are keyed by CODE, so the two can never be
        # matched up by name alone.
        #
        # Block, Disrupt and Fix have SHIPPED as mission tasks now, so
        # they belong to the built record; the rest are still unbuilt.
        # Every one has to appear in exactly one of the two.
        for name in ("Block", "Breach", "Bypass", "Canalize", "Disrupt",
                     "Fix", "Penetrate", "Seize", "Withdraw"):

            built = name in LINE_MEASURE_TYPE_LABELS.values()

            unbuilt = name in TABLE_H_XXIV_REMAINING.values()

            self.assertTrue(
                built or unbuilt,
                f"{name} is recorded neither as built nor as unbuilt"
            )

            self.assertFalse(
                built and unbuilt,
                f"{name} is recorded as both built and unbuilt"
            )



    def test_every_entity_is_registered_in_sidc(self):

        for entity, code in POINT_ENTITY_CODES.items():

            self.assertEqual(
                ENTITIES["control_measure"].get(entity), code, entity
            )


class TestMissionTaskPointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_the_layer_builds_without_echelon_or_headquarters(self):

        layer = create_mission_task_points_layer()

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


    def test_adding_the_layer_inserts_exactly_one(self):

        layer = add_mission_task_points_layer(self.iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)), 1
        )


    def test_a_second_add_warns_instead_of_replacing(self):

        first = add_mission_task_points_layer(self.iface)

        self.assertIsNone(add_mission_task_points_layer(self.iface))

        matching = QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())
        self.assertEqual(len(self.iface.messageBar().calls), 1)


class TestMissionTaskMarkerSize(QgisTestCase):

    """
    "mission task points - increase size by 30% like cbrn events."

    All three icons are a wide, low 208x128 - the widest box in the
    whole control-measure set - and QGIS sizes an SVG marker by its
    WIDTH, so they drew at about 42% of a supply point's scale.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _drawn_icon_scale(self, layer, entity, designation=""):

        """
        Millimetres of page per milsymbol icon unit - size / width,
        both taken from the renderer's own evaluated properties rather
        than restated.
        """

        feature = QgsFeature(layer.fields())
        feature.setAttribute("entity", entity)
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("status", "present")
        feature.setAttribute("unique_designation", designation)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        properties = layer.renderer().symbol().symbolLayer(
            0
        ).dataDefinedProperties()

        size, ok = properties.valueAsDouble(
            QgsSymbolLayer.Property.Size, context, 0.0
        )

        self.assertTrue(ok)

        path, ok = properties.valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)

        markup = base64.b64decode(
            path[len("base64:"):]
        ).decode("utf-8")

        width = float(
            re.search(r'viewBox="\S+ \S+ (\S+) \S+"', markup).group(1)
        )

        return size / width


    def test_all_three_are_scaled_and_nothing_else_is(self):

        self.assertEqual(set(POINT_MARKER_SIZE_SCALES), set(POINT_ENTITY_CODES))

        self.assertEqual(set(POINT_MARKER_SIZE_SCALES.values()), {1.30})


    def test_each_icon_is_drawn_thirty_percent_larger(self):

        layer = create_mission_task_points_layer()

        for entity in POINT_ENTITY_LABELS:

            plain_width = QgsExpression(
                "mct_sidc_svg_width('{}')".format(
                    QgsExpression(
                        "mct_build_sidc('friend', '{}', 'control_measure', "
                        "'unspecified', 'present', false)".format(entity)
                    ).evaluate()
                )
            ).evaluate(QgsExpressionContext())

            self.assertAlmostEqual(
                self._drawn_icon_scale(layer, entity),
                1.30 * 8.0 / plain_width,
                places=6,
                msg=entity,
            )


    def test_the_bump_survives_a_designation(self):

        # It has to compose with the amplifier compensation, which
        # scales the marker the other way to hold the icon still.
        layer = create_mission_task_points_layer()

        for entity in POINT_ENTITY_LABELS:

            scales = [
                self._drawn_icon_scale(layer, entity, designation)
                for designation in ("", "A", "LONGER")
            ]

            for scale in scales[1:]:

                self.assertAlmostEqual(scale, scales[0], places=6, msg=entity)
