# -*- coding: utf-8 -*-

"""
Tests for military_symbology/cbrn_defense.py - Table H-XXI,
Mini-Phase H18: the table's 18 points and its 7 contaminated areas.
Two rows remain unbuilt - see that module's own TABLE_H_XXI_REMAINING.

Military Cartography Tools
"""

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.cbrn_defense import (
    AREAS_LAYER_NAME,
    _area_glyph_sidc_expression,
    AREA_GLYPH_ENTITIES,
    AREA_MEASURE_TYPE_CODES,
    AREA_MEASURE_TYPE_LABELS,
    POINTS_LAYER_NAME,
    POINT_DESIGNATION_SLOTS,
    POINT_MARKER_SIZE_SCALES,
    POINT_ENTITY_CODES,
    POINT_ENTITY_LABELS,
    SHARED_GLYPH_CODES,
    TABLE_H_XXI_REMAINING,
    add_cbrn_contaminated_areas_layer,
    add_cbrn_defense_points_layer,
    create_cbrn_contaminated_areas_layer,
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
                       QgsExpressionContextUtils, QgsFeature, QgsGeometry,
                       QgsLinePatternFillSymbolLayer, QgsMapSettings,
                       QgsMaskMarkerSymbolLayer, QgsProject,
                       QgsSimpleLineSymbolLayer, QgsSymbolLayer,
                       QgsVectorLayerUtils)

from qgis.PyQt.QtCore import QSize

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


    def test_the_two_unbuilt_rows_are_recorded_not_forgotten(self):

        # The whole table is 27 rows: 18 points, 7 contaminated areas,
        # and the two that remain. Recording them explicitly is what
        # keeps "not built yet" from looking like "missed".
        self.assertEqual(len(TABLE_H_XXI_REMAINING), 2)

        self.assertEqual(
            len(POINT_ENTITY_CODES)
            + len(AREA_MEASURE_TYPE_CODES)
            + len(TABLE_H_XXI_REMAINING),
            27
        )

        self.assertEqual(
            set(TABLE_H_XXI_REMAINING),
            {"272100", "272200"}
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

        # Upper-cased per H.5.4, and INSIDE the box - Field T1, which
        # is where every 2818xx template draws it ("1/2COY", "4CBRN" in
        # the standard's own examples). This asserted the opposite until
        # 2026-08-14, with a comment saying so: the designation was in
        # Field T, outside and to the right. Corrected across Tables
        # H-XXI, H-XXII and H-XXIII together, all three being the same
        # box symbol with the same T1 box.
        self.assertIn(">V2</text>", svg)

        placed = re.search(r'<text x="([\d.]+)"[^>]*>V2</text>', svg)

        self.assertEqual(float(placed.group(1)), 100.0)


    def test_only_the_decontamination_points_moved_to_field_t1(self):

        # The eight EVENTS are a different icon family - a wide
        # inverted triangle, not the box - and milsymbol gives them one
        # text position only. Nothing to move, and a slot they do not
        # define would draw nothing at all.
        self.assertEqual(len(POINT_DESIGNATION_SLOTS), 10)

        for entity, code in POINT_ENTITY_CODES.items():

            with self.subTest(entity=entity):

                self.assertEqual(
                    entity in POINT_DESIGNATION_SLOTS,
                    code.startswith("2818")
                )

        for entity in ("chemical_event", "nuclear_event"):

            with self.subTest(entity=entity):

                svg = render_symbol_svg(
                    build_sidc(
                        "friend", entity, "control_measure",
                        "unspecified", "present", False
                    ),
                    {"uniqueDesignation1": "V2"}
                )

                self.assertNotIn(">V2</text>", svg)


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


# The blobby area the standard's own template pictures draw, as a
# ring of offsets in degrees around a local origin.
_TEMPLATE_AREA_WKT = (
    "POLYGON((0.000 0.000, 0.060 0.010, 0.100 -0.010, 0.120 -0.050,"
    " 0.080 -0.090, 0.020 -0.100, -0.030 -0.070, -0.040 -0.030,"
    " 0.000 0.000))"
)


class TestCbrnContaminatedAreaVocabulary(QgisTestCase):

    def test_all_seven_area_codes_are_covered(self):

        self.assertEqual(len(AREA_MEASURE_TYPE_CODES), 7)

        self.assertEqual(
            set(AREA_MEASURE_TYPE_LABELS), set(AREA_MEASURE_TYPE_CODES)
        )

        self.assertEqual(
            set(AREA_MEASURE_TYPE_CODES.values()),
            {
                "271700", "271701", "271800", "271801",
                "271900", "272000", "272001",
            }
        )

    def test_every_area_borrows_a_real_event_entity(self):

        # The whole construction rests on the area's glyph being the
        # matching EVENT point's own icon - so every value here has to
        # be a real control-measure entity, not a plausible-looking
        # string.
        self.assertEqual(
            set(AREA_GLYPH_ENTITIES), set(AREA_MEASURE_TYPE_CODES)
        )

        for measure_type, entity in AREA_GLYPH_ENTITIES.items():

            self.assertIn(
                entity, ENTITIES["control_measure"], measure_type
            )

            self.assertIn(entity, POINT_ENTITY_CODES, measure_type)

    def test_milsymbol_draws_nothing_for_the_area_codes_themselves(self):

        # The reason the glyph is addressed by the event's entity and
        # not the area's. If milsymbol ever gains these codes this test
        # fails, which is the right time to reconsider the indirection.
        blank = render_symbol_svg(
            build_sidc(
                "friend", "chemical_event", symbol_set="control_measure"
            )[:10] + "9999990000"
        )

        for code in AREA_MEASURE_TYPE_CODES.values():

            sidc = build_sidc(
                "friend", "chemical_event", symbol_set="control_measure"
            )

            drawn = render_symbol_svg(sidc[:10] + code + sidc[16:])

            self.assertEqual(len(drawn), len(blank), code)

    def test_each_toxic_industrial_material_area_gains_a_t(self):

        # The "T" under the letter is the only thing separating a Toxic
        # Industrial Material area from its plain sibling, and it comes
        # free from the event icon rather than being added here - so it
        # is worth pinning that it actually arrives.
        for measure_type, entity in AREA_GLYPH_ENTITIES.items():

            svg = render_symbol_svg(
                build_sidc(
                    "friend", entity, symbol_set="control_measure"
                )
            )

            letters = re.findall(r">([^<>]{1,4})</text>", svg)

            if measure_type.endswith("_tim"):

                self.assertEqual(len(letters), 2, measure_type)
                self.assertEqual(letters[1], "T", measure_type)

            else:

                self.assertEqual(len(letters), 1, measure_type)


class TestCbrnContaminatedAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        military_symbology_functions.register()

        self.project = QgsProject.instance()
        self.project.setCrs(WGS84)

        self.layer = create_cbrn_contaminated_areas_layer()

    def tearDown(self):

        self.project.removeAllMapLayers()

        military_symbology_functions.unregister()

        super().tearDown()

    def test_the_layer_builds_and_offers_all_seven(self):

        self.assertTrue(self.layer.isValid())
        self.assertEqual(self.layer.name(), AREAS_LAYER_NAME)

        rules = self.layer.renderer().rootRule().children()

        self.assertEqual(
            {rule.label() for rule in rules},
            set(AREA_MEASURE_TYPE_LABELS)
        )

    def test_the_fill_is_yellow_hatching_and_the_glyph_masks_it(self):

        symbol = self.layer.renderer().rootRule().children()[0].symbol()

        hatch = symbol.symbolLayer(0)

        self.assertIsInstance(hatch, QgsLinePatternFillSymbolLayer)

        # The colour lives on the sub-symbol's own line layer - setting
        # it on the pattern-fill layer is silently ignored by QGIS.
        self.assertEqual(
            hatch.subSymbol().symbolLayer(0).color().name(), "#ffff00"
        )

        self.assertIsInstance(
            symbol.symbolLayer(1), QgsSimpleLineSymbolLayer
        )

        glyph = symbol.symbolLayer(2).subSymbol()

        self.assertIsInstance(
            glyph.symbolLayer(0), QgsMaskMarkerSymbolLayer
        )

        # The mask cuts the hatch specifically, by the stable id the
        # hatch layer was given.
        self.assertEqual(
            [
                reference.symbolLayerIdV2()
                for reference in glyph.symbolLayer(0).masks()
            ],
            ["cbrn_contaminated_area_hatch"]
        )

    def test_the_glyph_stays_clear_of_the_outline_by_three_millimetres(self):

        # The point of the whole size expression, measured rather than
        # asserted on the expression's own text: evaluate the real
        # size against a real feature in a real map context, then check
        # the glyph's furthest corner against the polygon's own edge.
        feature = QgsFeature(self.layer.fields())

        geometry = QgsGeometry.fromWkt(_TEMPLATE_AREA_WKT)
        geometry.translate(77.0, 28.0)

        feature.setGeometry(geometry)
        feature.setAttribute("measure_type", "chemical")
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("status", "present")

        self.layer.dataProvider().addFeatures([feature])
        self.layer.updateExtents()

        self.project.addMapLayer(self.layer)

        settings = QgsMapSettings()
        settings.setLayers([self.layer])
        settings.setOutputSize(QSize(800, 800))
        settings.setOutputDpi(96)
        settings.setDestinationCrs(WGS84)

        extent = self.layer.extent()
        extent.grow(0.02)
        settings.setExtent(extent)

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.globalScope())
        context.appendScope(
            QgsExpressionContextUtils.projectScope(self.project)
        )
        context.appendScope(
            QgsExpressionContextUtils.mapSettingsScope(settings)
        )
        context.appendScope(
            QgsExpressionContextUtils.layerScope(self.layer)
        )
        context.setFeature(next(self.layer.getFeatures()))

        size_property = (
            self.layer.renderer()
            .rootRule()
            .children()[0]
            .symbol()
            .symbolLayer(2)
            .subSymbol()
            .symbolLayer(1)
            .dataDefinedProperties()
            .property(QgsSymbolLayer.Property.Size)
        )

        size_mm = size_property.valueAsDouble(context, 0.0)[0]

        self.assertGreater(size_mm, 10.0)

        # Millimetres per degree, the same way the size expression got
        # them.
        millimetres_per_degree = QgsExpression(
            "mct_inscribed_radius_mm($geometry, @map_extent, @map_scale)"
        ).evaluate(context) / _inscribed_radius_degrees(geometry)

        # The glyph's furthest point from its own centre - the top
        # corners of the triangle, at hypot(60, 55) + half the stroke
        # out of a 158-unit-wide box.
        corner_mm = size_mm * (((60.0 ** 2 + 55.0 ** 2) ** 0.5) + 1.5) / 158.0

        corner_degrees = corner_mm / millimetres_per_degree

        centre = QgsExpression(
            "mct_inscribed_centre($geometry)"
        ).evaluate(context).asPoint()

        boundary = QgsGeometry(geometry.constGet().boundary())

        for angle in range(0, 360, 5):

            import math

            corner = QgsGeometry.fromPointXY(
                type(centre)(
                    centre.x() + corner_degrees * math.cos(math.radians(angle)),
                    centre.y() + corner_degrees * math.sin(math.radians(angle))
                )
            )

            self.assertTrue(
                geometry.contains(corner),
                f"the glyph's own corner circle leaves the area at {angle}"
            )

            gap_mm = (
                boundary.distance(corner) * millimetres_per_degree
            )

            self.assertGreaterEqual(
                round(gap_mm, 3), 3.0,
                f"only {gap_mm:.2f} mm of clearance at {angle} degrees"
            )


def _inscribed_radius_degrees(geometry):

    """
    The same quantity mct_inscribed_radius_mm() measures, in map units
    - recomputed independently here so the test is not simply asking
    the code under test to confirm itself.
    """

    import math

    bounding_box = geometry.boundingBox()

    precision = max(bounding_box.width(), bounding_box.height()) / 200.0

    pole, _ = geometry.poleOfInaccessibility(precision)

    nearest = QgsGeometry(geometry.constGet().boundary()).nearestPoint(pole)

    return math.hypot(
        nearest.asPoint().x() - pole.asPoint().x(),
        nearest.asPoint().y() - pole.asPoint().y()
    )


class TestCbrnAreasLayerInsertion(QgisTestCase):

    def setUp(self):

        super().setUp()

        military_symbology_functions.register()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()

    def tearDown(self):

        QgsProject.instance().removeAllMapLayers()

        military_symbology_functions.unregister()

        super().tearDown()

    def test_adding_the_areas_layer_inserts_exactly_one(self):

        add_cbrn_contaminated_areas_layer(self.iface)

        layers = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(layers), 1)

        add_cbrn_contaminated_areas_layer(self.iface)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)), 1
        )


# milsymbol's own unknown-icon fallback is an inverted "?" - this is a
# stable fragment of the path it draws, the same marker four other test
# modules in this suite already watch for.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


class TestCbrnAreaGlyphSurvivesTheLayersOwnDefaults(QgisTestCase):

    """
    The unknown-glyph bug, fourth occurrence - reported live on
    2026-08-15 as "glyphs are again breaking in qgis, old problem",
    with the inverted "?" drawn in place of every contaminated area's
    triangle.

    An AREAS layer's affiliation vocabulary has a fifth value,
    "unspecified" (meaning "draw it black"), which is also the field's
    own DEFAULT. It is not a SIDC standard identity, so feeding it
    straight to mct_build_sidc() returns a KeyError message where a
    SIDC should be and milsymbol falls back to its unknown icon.

    **The test that shipped alongside the bug made the same mistake
    the two before it did**: it built its feature with
    affiliation="friend" hardcoded, so the layer's own default was
    never exercised, and the offscreen render it was checked against
    was hand-fed too. Everything here goes through
    QgsVectorLayerUtils.createFeature(), which is what QGIS itself
    calls when the user digitizes - so the defaults are the subject,
    not an incidental detail.
    """

    def setUp(self):

        super().setUp()

        military_symbology_functions.register()

        self.project = QgsProject.instance()
        self.project.setCrs(WGS84)

        self.layer = create_cbrn_contaminated_areas_layer()

        self.project.addMapLayer(self.layer)

    def tearDown(self):

        self.project.removeAllMapLayers()

        military_symbology_functions.unregister()

        super().tearDown()

    def _glyph_svg(self, **attributes):

        geometry = QgsGeometry.fromWkt(_TEMPLATE_AREA_WKT)
        geometry.translate(77.0, 28.0)

        feature = QgsVectorLayerUtils.createFeature(self.layer, geometry)

        for name, value in attributes.items():
            feature.setAttribute(name, value)

        context = QgsExpressionContext()
        context.appendScopes(
            QgsExpressionContextUtils.globalProjectLayerScopes(self.layer)
        )
        context.setFeature(feature)

        path = QgsExpression(_area_glyph_sidc_expression()).evaluate(context)

        self.assertTrue(
            isinstance(path, str) and path.startswith("base64:"),
            f"the glyph path is not a rendered symbol at all: {path!r}"
        )

        return base64.b64decode(path.split("base64:", 1)[1]).decode("utf-8")

    def test_the_layers_own_default_affiliation_is_the_fifth_value(self):

        # If this ever stops being true the test below stops testing
        # anything, so it is pinned rather than assumed.
        geometry = QgsGeometry.fromWkt(_TEMPLATE_AREA_WKT)
        geometry.translate(77.0, 28.0)

        feature = QgsVectorLayerUtils.createFeature(self.layer, geometry)

        self.assertEqual(feature["affiliation"], "unspecified")

    def test_no_measure_type_draws_the_unknown_icon_from_defaults(self):

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                svg = self._glyph_svg(measure_type=measure_type)

                self.assertNotIn(
                    _MILSYMBOL_UNKNOWN_ICON_MARK, svg, measure_type
                )

    def test_no_affiliation_the_form_offers_draws_the_unknown_icon(self):

        from MilitaryCartographyTools.military_symbology._control_measure_shared import (
            AFFILIATION_LABELS,
        )

        for affiliation in AFFILIATION_LABELS:

            for measure_type in AREA_MEASURE_TYPE_LABELS:

                with self.subTest(affiliation=affiliation,
                                  measure_type=measure_type):

                    svg = self._glyph_svg(
                        affiliation=affiliation,
                        measure_type=measure_type,
                    )

                    self.assertNotIn(
                        _MILSYMBOL_UNKNOWN_ICON_MARK,
                        svg,
                        f"{affiliation}/{measure_type}"
                    )

    def test_the_fifth_value_draws_the_glyph_black(self):

        # "Unspecified (black)" has to actually be black, and by
        # monoColor rather than by friend happening to render black.
        svg = self._glyph_svg(affiliation="unspecified")

        self.assertIn("#000000", svg)

    def test_hostile_still_draws_red(self):

        # The one identity milsymbol does draw differently - so the
        # mapping must not have flattened every area to one colour.
        svg = self._glyph_svg(affiliation="hostile")

        self.assertIn("rgb(255, 0, 0)", svg)

    def test_the_glyph_is_the_real_triangle_whatever_the_defaults(self):

        # The triangle path itself, which is what the maintainer
        # actually saw missing.
        svg = self._glyph_svg()

        self.assertIn("-60,-110 120,0 z", svg)
