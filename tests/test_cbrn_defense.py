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
    POINT_MARKER_SIZE_SCALES,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    SHARED_GLYPH_CODES,
    TABLE_H_XXI_REMAINING,
    add_cbrn_defense_points_layer,
    create_cbrn_defense_points_layer,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    ENTITIES,
    build_sidc,
)
from MilitaryCartographyTools.military_symbology.symbol_engine import (
    render_symbol_svg,
)

import base64
import re

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsExpressionContext, QgsExpressionContextScope,
                       QgsFeature, QgsProject, QgsSymbolLayer)

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


class TestCbrnSmokeTestFixes(QgisTestCase):

    """Table H-XXI's own two 2026-08-13 smoke-test findings."""

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _svg_layer(self, layer):

        return layer.renderer().symbol().symbolLayer(0)


    def test_the_eight_events_are_drawn_thirty_percent_larger(self):

        # "all points are too small to be readable, can we increase the
        # size by 30%? - 281300/301/400/401/500/600/700/701" - the eight
        # events, whose milsymbol boxes are wide and low (158x118) where
        # the decontamination points' are narrow and tall (88x168).
        layer = create_cbrn_defense_points_layer()

        expression = self._svg_layer(layer).dataDefinedProperties().property(
            QgsSymbolLayer.Property.Size
        ).expressionString()

        self.assertTrue(expression)

        for entity in POINT_ENTITY_LABELS:

            context = QgsExpressionContext()

            scope = QgsExpressionContextScope()
            scope.setVariable("entity", entity)

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", entity)
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("status", "present")

            context = layer.createExpressionContext()
            context.setFeature(feature)

            size = QgsExpression(expression).evaluate(context)

            if POINT_ENTITY_CODES[entity].startswith("2818"):

                # Decontamination points are untouched.
                self.assertAlmostEqual(size, 8.0, places=4, msg=entity)

            else:

                self.assertAlmostEqual(size, 8.0 * 1.30, places=4, msg=entity)


    def test_only_the_eight_event_codes_are_scaled(self):

        self.assertEqual(
            {POINT_ENTITY_CODES[e] for e in POINT_MARKER_SIZE_SCALES},
            {
                "281300", "281301", "281400", "281401",
                "281500", "281600", "281700", "281701",
            }
        )


    def test_the_unique_designation_reaches_the_symbol(self):

        # The field was on the layer and collected in the attribute
        # table, but the shared point-layer builder never passed it into
        # mct_sidc_svg - so nothing drew it. Same defect class the
        # maintainer found on three other Points layers on 2026-08-10.
        layer = create_cbrn_defense_points_layer()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("entity", "decontamination_point_operational")
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("status", "present")
        feature.setAttribute("unique_designation", "v2")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        path, ok = self._svg_layer(layer).dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)

        svg = base64.b64decode(path[len("base64:"):]).decode("utf-8")

        # Upper-cased per H.5.4, and to the RIGHT of the box, which is
        # where the template puts Field T - milsymbol's own
        # uniqueDesignation1 slot would have put it inside the box,
        # which is the template's T1.
        self.assertIn(">V2</text>", svg)

        placed = re.search(r'<text x="([\d.]+)"[^>]*>V2</text>', svg)

        self.assertGreater(float(placed.group(1)), 140.0)


    def test_an_empty_designation_leaves_the_icon_alone(self):

        layer = create_cbrn_defense_points_layer()

        svgs = []

        for designation in (None, ""):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", "decontamination_point")
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("status", "present")
            feature.setAttribute("unique_designation", designation)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            path, ok = self._svg_layer(
                layer
            ).dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.Name, context, ""
            )

            self.assertTrue(ok)

            svgs.append(
                base64.b64decode(path[len("base64:"):]).decode("utf-8")
            )

        self.assertEqual(svgs[0], svgs[1])

        # ...and both are exactly what the icon renders with no
        # designation asked for at all. ("<text" alone would not do:
        # the icon's own "DCN" is text too.)
        self.assertEqual(
            svgs[0],
            render_symbol_svg(
                build_sidc(
                    "friend",
                    "decontamination_point",
                    symbol_set="control_measure",
                    echelon="unspecified",
                    status="present",
                )
            )
        )


class TestCbrnIconSizeIsHeldStill(QgisTestCase):

    """
    "now the symbol size is reducing when the Field T is added -
    inconsistent from a UI point of view. can we have the size of the
    main symbol remaining same?"
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _drawn_icon_scale(self, layer, entity, designation):

        """
        Millimetres of page per milsymbol icon unit - the thing that
        has to stay constant. Marker size is in mm and QGIS fits it to
        the SVG's WIDTH, so this is size / width, both taken from the
        renderer's own evaluated properties rather than restated.
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


    def test_the_icon_keeps_its_size_whatever_the_designation(self):

        layer = create_cbrn_defense_points_layer()

        for entity in ("chemical_event", "decontamination_point"):

            scales = [
                self._drawn_icon_scale(layer, entity, designation)
                for designation in (None, "", "A", "LONGER", "A VERY LONG ONE")
            ]

            for scale in scales[1:]:

                self.assertAlmostEqual(scale, scales[0], places=6, msg=entity)


    def test_the_thirty_percent_event_bump_survives_a_designation(self):

        # The two size adjustments compose: an event is drawn 30%
        # larger than the same icon would be at the layer's plain
        # marker size, designation or not.
        #
        # Note what this is NOT: 30% is applied to the MARKER SIZE, not
        # to the drawn scale relative to the decontamination points.
        # Those still come out larger, because milsymbol boxes them
        # 88 wide against the events' 158 - closing that gap entirely
        # would take about 80%, which is recorded in cbrn_defense.py as
        # the maintainer's to revisit.
        layer = create_cbrn_defense_points_layer()

        plain_event_width = QgsExpression(
            "mct_sidc_svg_width('{}')".format(
                build_sidc(
                    "friend",
                    "chemical_event",
                    symbol_set="control_measure",
                    echelon="unspecified",
                    status="present",
                )
            )
        ).evaluate(QgsExpressionContext())

        expected = 1.30 * 8.0 / plain_event_width

        for designation in ("", "LONGER"):

            self.assertAlmostEqual(
                self._drawn_icon_scale(layer, "chemical_event", designation),
                expected,
                places=6,
                msg=designation,
            )
