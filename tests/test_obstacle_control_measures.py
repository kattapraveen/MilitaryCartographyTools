# -*- coding: utf-8 -*-

"""
Tests for military_symbology/obstacle_control_measures.py - Table
H-XIX, Mini-Phase H15/H16.

This module currently holds the batch-B0 AUDIT only; no layers or
symbols are built yet. So these tests pin the inventory itself, which
is what every later batch reads from - see that module's own docstring.

Military Cartography Tools
"""

import math

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
    AREA,
    BLACK,
    GREEN,
    LINE,
    OUTLINE_GREEN_TEXT_BLACK,
    PARENT,
    POINT,
    POINTS_LAYER_NAME,
    POINT_ENTITY_LABELS,
    TABLE_H_XIX_INVENTORY,
    add_obstacle_control_measures_points_layer,
    buildable_inventory,
    create_obstacle_control_measures_points_layer,
    inventory_for_batch,
)
from MilitaryCartographyTools.military_symbology.control_measure_points import (
    _ENTITY_LABELS as _CONTROL_MEASURE_POINT_ENTITY_LABELS,
)
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES

from qgis.core import (QgsCoordinateReferenceSystem, QgsExpression,
                       QgsFeature, QgsProject, QgsSymbolLayer)

from .qgis_test_case import FakeIface

WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


# Every code row on printed pages 573-603, extracted from the standard
# itself. Kept here as a literal rather than derived from the inventory
# under test, so the inventory is checked AGAINST the table rather than
# against itself - the failure mode that let H-XVIII's Terminally
# Guided Munition Footprint go missing behind a self-agreeing count.
_TABLE_CODES = (
    [f"2701{n:02d}" for n in (0,)] +
    ["270100", "270200", "270300", "270400"] +
    ["270500", "270501", "270502", "270503", "270504"] +
    ["270600", "270601", "270602", "270603"] +
    ["270700", "270701", "270702", "270703", "270704", "270705",
     "270706", "270707"] +
    ["270800", "270900", "270901", "271000"] +
    ["271100"] +
    ["271200", "271201", "271202", "271203", "271204"] +
    ["271300", "271400", "271500", "271600"] +
    ["280000", "280100", "280200", "280201", "280300", "280400",
     "280500", "280600", "280700", "280800"] +
    ["281900", "281901", "281902", "281903"] +
    ["282000", "282001", "282002", "282003"] +
    ["290000", "290100"] +
    ["290200", "290201", "290202", "290203", "290204"] +
    ["290300", "290301", "290302", "290303", "290304", "290305",
     "290306", "290307", "290308", "290309"] +
    ["290400", "290500", "290600", "290700", "290800"]
)


class TestTableHXIXInventory(QgisTestCase):

    def test_covers_every_code_row_the_table_lists(self):

        expected = set(_TABLE_CODES)

        # "2701 00" from the list comprehension above is 271000, already
        # present - guard against the literal drifting into a duplicate
        # or a typo that silently shrinks the expected set.
        self.assertEqual(len(expected), 75)

        self.assertEqual(set(TABLE_H_XIX_INVENTORY), expected)


    def test_does_not_reach_into_neighbouring_tables(self):

        # The 28xxxx/29xxxx prefixes are shared with Table H-XX (Field
        # Fortification) and Table H-XXI (CBRN). Scoping by prefix
        # instead of by page range would pull these in silently, so
        # each is named explicitly.
        for code, owner in (
            ("280900", "H-XX Shelter"),
            ("281000", "H-XX Shelter Above Ground"),
            ("281100", "H-XX Below Ground Shelter"),
            ("281200", "H-XX Fort"),
            ("281300", "H-XXI Chemical Event"),
            ("281400", "H-XXI Biological Event"),
            ("281500", "H-XXI Nuclear Event"),
            ("281700", "H-XXI Radiological"),
            ("281808", "H-XXI decontamination site family"),
        ):

            with self.subTest(code=code, owner=owner):

                self.assertNotIn(code, TABLE_H_XIX_INVENTORY)


    def test_every_entry_has_a_usable_geometry_class(self):

        for code, entry in TABLE_H_XIX_INVENTORY.items():

            with self.subTest(code=code):

                self.assertIn(entry["geometry"], (AREA, LINE, POINT, PARENT))
                self.assertTrue(entry["name"])
                self.assertTrue(entry["batch"])
                self.assertIsInstance(entry["verified"], bool)
                self.assertIn(
                    entry["colour"], (GREEN, BLACK, OUTLINE_GREEN_TEXT_BLACK)
                )
                self.assertIsInstance(entry["field_t"], bool)


    def test_parent_rows_are_excluded_from_buildable_work(self):

        # Heading rows whose template column reads "N/A" - nothing to
        # draw. Ten of the 75.
        parents = {
            code for code, entry in TABLE_H_XIX_INVENTORY.items()
            if entry["geometry"] == PARENT
        }

        self.assertEqual(
            parents,
            {
                "270500",  # Obstacle Effects
                "270600",  # Obstacle Bypass
                "270700",  # Minefield
                "271200",  # Roadblocks, Craters and Blown Bridges
                "280000",  # Protection Points
                "281900",  # Tetrahedrons, Dragons Teeth
                "282000",  # Vertical Obstructions
                "290000",  # Protection Lines
                "290200",  # Antitank Obstacles
                "290300",  # Wire Obstacles
            }
        )

        self.assertEqual(len(buildable_inventory()), 75 - 10)

        for entry in buildable_inventory().values():

            self.assertNotEqual(entry["geometry"], PARENT)


    def test_every_buildable_entry_is_owned_by_exactly_one_batch(self):

        batches = ("B1", "B2", "B3", "B4", "B5", "B6", "B7")

        owned = {}

        for batch in batches:

            for code in inventory_for_batch(batch):

                self.assertNotIn(code, owned, f"{code} claimed twice")
                owned[code] = batch

        self.assertEqual(set(owned), set(buildable_inventory()))


    def test_the_geometry_findings_that_contradicted_the_batch_plan(self):

        # Each of these was read off its own template picture and
        # overturned what the family/prefix implied. Pinned so a later
        # batch cannot quietly revert to the wrong assumption.

        # Most minefields are fixed-size POINTS ("requires one anchor
        # point... Size/Shape: Static"), not polygons.
        for code in ("270701", "270702", "270703", "270704", "270705"):

            self.assertEqual(TABLE_H_XIX_INVENTORY[code]["geometry"], POINT)

        # Only these two of the family are freeform areas.
        for code in ("270706", "270707"):

            self.assertEqual(TABLE_H_XIX_INVENTORY[code]["geometry"], AREA)

        # The one 28xxxx code that is a line, not a point.
        self.assertEqual(TABLE_H_XIX_INVENTORY["282003"]["geometry"], LINE)
        self.assertEqual(TABLE_H_XIX_INVENTORY["282003"]["name"], "Overhead Wire")

        # Abatis sits under the "Protection Points" heading but is a
        # LINE - "requires at least two anchor points... to define the
        # line". B0 classified it by that heading and got it wrong; the
        # maintainer's own audit caught it.
        self.assertEqual(TABLE_H_XIX_INVENTORY["280100"]["geometry"], LINE)

        # 290400 is Mine Cluster. B0 read the PDF's "Une Cluste1" as
        # "Line Cluster" - a name taken from mangled OCR.
        self.assertEqual(TABLE_H_XIX_INVENTORY["290400"]["name"], "Mine Cluster")

        # Both were listed as "symbol/point" in the maintainer's audit
        # but their templates need two and three anchor points; settled
        # 2026-08-12 as LINES. Pinned so B4 cannot drift back.
        self.assertEqual(TABLE_H_XIX_INVENTORY["290400"]["geometry"], LINE)
        self.assertEqual(TABLE_H_XIX_INVENTORY["290500"]["geometry"], LINE)

        # The PDF text layer renders 271500 as "~~ry", which reads as
        # Ferry. It is Ford Easy; Ferry is 290700.
        self.assertEqual(TABLE_H_XIX_INVENTORY["271500"]["name"], "Ford Easy")
        self.assertEqual(TABLE_H_XIX_INVENTORY["290700"]["name"], "Ferry")


    def test_colour_follows_the_maintainers_audit(self):

        # The table-wide default is green; these are the entries the
        # 2026-08-12 audit named as exceptions. Pinned by name because
        # a wrong colour here is invisible in a headless test and only
        # shows up on a printed map.
        black = {
            code for code, entry in TABLE_H_XIX_INVENTORY.items()
            if entry["colour"] == BLACK
        }

        self.assertEqual(
            black,
            {
                "270601",  # Obstacle Bypass Easy
                "270602",  # Obstacle Bypass Difficult
                "270603",  # Obstacle Bypass Impossible
                "271100",  # Bridge or Gap
                "271000",  # UXO Area
                "290203",  # Antitank Ditch Reinforced with Antitank Mines
                "290204",  # Antitank Wall
                "290600",  # Lane
            }
        )

        # "OT" in the audit's own shorthand - outline green, text black.
        outline_green = {
            code for code, entry in TABLE_H_XIX_INVENTORY.items()
            if entry["colour"] == OUTLINE_GREEN_TEXT_BLACK
        }

        self.assertEqual(
            outline_green,
            {"270100", "270200", "270300", "270400", "290100"}
        )


    def test_field_t_follows_the_maintainers_audit(self):

        required = {
            code for code, entry in TABLE_H_XIX_INVENTORY.items()
            if entry["field_t"]
        }

        self.assertEqual(
            required,
            {
                "270100",  # Obstacle Belt
                "270200",  # Obstacle Zone
                "270300",  # Obstacle Free Zone
                "270400",  # Obstacle Restricted Zone
                "271100",  # Bridge or Gap
                "290100",  # Obstacle Line
                "280800",  # Engineer Regulating Point
                "282001",  # Tower, Low
                "282002",  # Tower, High
            }
        )


class TestObstaclePointsLayer(QgisTestCase):

    """Batch B1 - Table H-XIX's own protection points."""

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()


    def test_offers_exactly_the_point_entries_b1_owns(self):

        # Driven from the inventory rather than restated, so a batch
        # boundary moving in B0 cannot silently desync from the layer.
        expected = {
            entry["name"]: code
            for code, entry in inventory_for_batch("B1").items()
        }

        self.assertEqual(len(POINT_ENTITY_LABELS), len(expected))

        for entity in POINT_ENTITY_LABELS:

            self.assertIn(entity, ENTITIES["control_measure"])


    def test_excludes_the_two_28xxxx_codes_that_are_lines(self):

        # Abatis (280100) and Overhead Wire (282003) carry 28xxxx codes
        # but are lines - they belong to B4 and B7. Abatis deliberately
        # stays on the shared Control Measure Points layer until B4
        # builds its line version, so it does not disappear from every
        # dropdown in between.
        codes = {
            ENTITIES["control_measure"][entity]
            for entity in POINT_ENTITY_LABELS
        }

        self.assertNotIn("280100", codes)
        self.assertNotIn("282003", codes)

        self.assertIn("abatis", _CONTROL_MEASURE_POINT_ENTITY_LABELS)


    def test_the_relocated_points_left_the_shared_layer(self):

        overlap = set(POINT_ENTITY_LABELS) & set(
            _CONTROL_MEASURE_POINT_ENTITY_LABELS
        )

        self.assertEqual(overlap, set())


    def test_has_a_per_feature_colour_field_defaulting_to_green(self):

        # "user should have the ability to change colour to black if he
        # wants to" - so colour is per FEATURE, not per measure type.
        layer = create_obstacle_control_measures_points_layer()

        self.assertEqual(
            [field.name() for field in layer.fields()],
            ["affiliation", "entity", "status", "colour", "unique_designation"]
        )

        idx = layer.fields().indexOf("colour")

        self.assertEqual(
            layer.defaultValueDefinition(idx).expression(), "'green'"
        )

        self.assertEqual(
            set(layer.editorWidgetSetup(idx).config()["map"].values()),
            {"green", "black"}
        )


    def test_colour_reaches_the_rendered_icon_via_monocolor(self):

        # milsymbol owns a point icon's colour and applies H.5.3's
        # affiliation rule, so the obstacle points cannot take the
        # data-defined colour the hand-built lines and areas use. Its
        # own monoColor option recolours the whole icon instead. Checked
        # by decoding the rendered SVG, not by trusting the expression.
        import base64

        layer = create_obstacle_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        def rendered(colour):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("affiliation", "friend")
            feature.setAttribute("entity", "antipersonnel_mine")
            feature.setAttribute("status", "present")
            feature.setAttribute("colour", colour)

            context = layer.createExpressionContext()
            context.setFeature(feature)

            path, ok = svg_layer.dataDefinedProperties().valueAsString(
                QgsSymbolLayer.Property.Name, context, ""
            )

            self.assertTrue(ok)

            return base64.b64decode(path[len("base64:"):]).decode("utf-8")

        self.assertIn("rgb(0,155,0)", rendered("green"))
        self.assertNotIn("rgb(0,155,0)", rendered("black"))
        self.assertIn("rgb(0,0,0)", rendered("black"))


    def test_every_entity_resolves_to_a_real_rendered_symbol(self):

        layer = create_obstacle_control_measures_points_layer()

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        for entity in POINT_ENTITY_LABELS:

            with self.subTest(entity=entity):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("affiliation", "friend")
                feature.setAttribute("entity", entity)
                feature.setAttribute("status", "present")
                feature.setAttribute("colour", "green")

                context = layer.createExpressionContext()
                context.setFeature(feature)

                path, ok = svg_layer.dataDefinedProperties().valueAsString(
                    QgsSymbolLayer.Property.Name, context, ""
                )

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


    def test_points_layer_is_created_and_added(self):

        layer = add_obstacle_control_measures_points_layer(FakeIface())

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(POINTS_LAYER_NAME)), 1
        )


    def test_towers_get_a_real_label_because_milsymbol_has_no_slot(self):

        # Both Towers require a unique designation per the audit, and
        # milsymbol has NO text slot for either icon - probed all six of
        # its text options against both codes, none accepted, and their
        # rendered SVG has no <text> element to hang one on. So the
        # designation needs a PAL label beside the icon, unlike every
        # other Points layer in this pass.
        #
        # Engineer Regulating Point also requires one but DOES accept
        # uniqueDesignation, so it must NOT be labelled here or it would
        # show the designation twice.
        layer = create_obstacle_control_measures_points_layer()

        settings = layer.labeling().settings()

        expression = QgsExpression(settings.fieldName)

        def label_for(entity):

            feature = QgsFeature(layer.fields())
            feature.setAttribute("entity", entity)
            feature.setAttribute("unique_designation", "n7")

            context = layer.createExpressionContext()
            context.setFeature(feature)

            return expression.evaluate(context)

        self.assertEqual(label_for("tower_low"), "N7")
        self.assertEqual(label_for("tower_high"), "N7")

        self.assertEqual(label_for("engineer_regulating_point"), "")
        self.assertEqual(label_for("antipersonnel_mine"), "")


# milsymbol's own unknown-icon fallback is an inverted "?" - this is a
# stable fragment of the path it draws for it. Present in the rendered
# SVG iff milsymbol could not resolve the SIDC it was handed.
#
# Needed because a "does it render?" assertion on the base64 PATH alone
# cannot see this failure: mct_build_sidc() returns its KeyError MESSAGE
# as a string when a component is invalid, mct_sidc_svg() hands that to
# milsymbol, milsymbol falls back to the unknown icon, and the result is
# still a perfectly well-formed `base64:` path. That is exactly how the
# 2026-08-12 "every obstacle point renders as unknown" bug got past a
# green test suite - see _POINT_AFFILIATION_LABELS' own comment.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


def _decoded_icon_svg(layer, feature):

    """The actual SVG a feature renders to, decoded from its base64 path."""

    import base64

    svg_layer = layer.renderer().symbol().symbolLayer(0)

    context = layer.createExpressionContext()
    context.setFeature(feature)

    path, ok = svg_layer.dataDefinedProperties().valueAsString(
        QgsSymbolLayer.Property.Name, context, ""
    )

    assert ok and path.startswith("base64:"), path

    return base64.b64decode(path[len("base64:"):]).decode("utf-8")


class TestPointsLayerDefaultsProduceRealSymbols(QgisTestCase):

    """
    Guards the failure the maintainer's own live smoke test caught on
    2026-08-12: every point placed on this layer drew milsymbol's
    unknown icon, because the layer reused the LINES/AREAS affiliation
    helper, whose default ("unspecified") is deliberately not a SIDC
    standard identity at all.

    The lesson generalises past that one field, so these tests drive the
    layer's OWN configured defaults rather than restating them - a
    future default that is not in the SIDC vocabulary fails here without
    anyone having to remember to update the test.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _feature_from_layer_defaults(self, layer):

        feature = QgsFeature(layer.fields())

        context = layer.createExpressionContext()

        for field in layer.fields():

            idx = layer.fields().indexOf(field.name())

            expression = layer.defaultValueDefinition(idx).expression()

            if not expression:
                continue

            feature.setAttribute(
                field.name(), QgsExpression(expression).evaluate(context)
            )

        return feature


    def test_affiliation_default_is_a_real_sidc_standard_identity(self):

        from MilitaryCartographyTools.military_symbology.sidc import AFFILIATIONS

        layer = create_obstacle_control_measures_points_layer()

        idx = layer.fields().indexOf("affiliation")

        default = QgsExpression(
            layer.defaultValueDefinition(idx).expression()
        ).evaluate(layer.createExpressionContext())

        self.assertIn(default, AFFILIATIONS)


    def test_the_affiliation_dropdown_offers_only_valid_identities(self):

        # "Unspecified (black)" is a real, useful fifth value for the
        # hand-drawn lines/areas layers, where affiliation only picks a
        # Qt colour. It cannot appear on a milsymbol-rendered POINTS
        # layer, where the same field becomes SIDC digit 4.
        from MilitaryCartographyTools.military_symbology.sidc import AFFILIATIONS
        from MilitaryCartographyTools.military_symbology import (
            obstacle_control_measures,
        )

        for affiliation in obstacle_control_measures._POINT_AFFILIATION_LABELS:

            with self.subTest(affiliation=affiliation):

                self.assertIn(affiliation, AFFILIATIONS)


    def test_a_feature_built_from_the_layers_defaults_renders_a_real_icon(self):

        # The exact path a freshly digitized point takes: touch no
        # dropdown, let every field take the layer's own default.
        layer = create_obstacle_control_measures_points_layer()

        feature = self._feature_from_layer_defaults(layer)

        svg = _decoded_icon_svg(layer, feature)

        self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg)


    def test_no_entity_renders_as_the_unknown_icon(self):

        # The stronger form of
        # test_every_entity_resolves_to_a_real_rendered_symbol, which
        # only checked that SOME base64 path came back.
        layer = create_obstacle_control_measures_points_layer()

        for entity in POINT_ENTITY_LABELS:

            with self.subTest(entity=entity):

                feature = self._feature_from_layer_defaults(layer)
                feature.setAttribute("entity", entity)

                svg = _decoded_icon_svg(layer, feature)

                self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg)


    def test_every_offered_dropdown_combination_renders_a_real_icon(self):

        # Full sweep of what the attribute form actually lets a user
        # pick - the smoke test the maintainer ran by hand, automated.
        from MilitaryCartographyTools.military_symbology import (
            obstacle_control_measures,
        )

        layer = create_obstacle_control_measures_points_layer()

        for affiliation in obstacle_control_measures._POINT_AFFILIATION_LABELS:

            for status in obstacle_control_measures._POINT_STATUS_LABELS:

                for entity in POINT_ENTITY_LABELS:

                    for colour in (GREEN, BLACK):

                        feature = QgsFeature(layer.fields())
                        feature.setAttribute("affiliation", affiliation)
                        feature.setAttribute("entity", entity)
                        feature.setAttribute("status", status)
                        feature.setAttribute("colour", colour)

                        svg = _decoded_icon_svg(layer, feature)

                        self.assertNotIn(
                            _MILSYMBOL_UNKNOWN_ICON_MARK,
                            svg,
                            f"{affiliation}/{status}/{entity}/{colour}"
                        )


class TestObstacleAreasLayer(QgisTestCase):

    """
    Batch B2 - Table H-XIX's own 8 area rows. See
    obstacle_control_measures.py's own B2 section for the construction
    findings these pin.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_offers_exactly_the_area_entries_b2_and_b3_own(self):

        # The Areas layer spans two batches: all of B2, plus the two
        # minefield codes B3 draws as freeform areas rather than as the
        # static box its other five use (270706/270707). Asserted as
        # that union rather than loosened to a subset, so an area
        # arriving on this layer from nowhere still fails.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            AREA_MEASURE_TYPE_CODES,
            AREA_MEASURE_TYPE_LABELS,
        )

        self.assertEqual(
            set(AREA_MEASURE_TYPE_CODES),
            set(AREA_MEASURE_TYPE_LABELS)
        )

        dynamic_minefield_codes = {"270706", "270707"}

        self.assertTrue(
            dynamic_minefield_codes.issubset(set(inventory_for_batch("B3")))
        )

        self.assertEqual(
            set(AREA_MEASURE_TYPE_CODES.values()),
            set(inventory_for_batch("B2")) | dynamic_minefield_codes
        )


    def test_excludes_the_two_parent_rows_in_its_own_page_range(self):

        # 270500 (Obstacle Effects) and 270700 (Minefields) are heading
        # rows whose own template cell reads "N/A" - a code-prefix scope
        # would drag them in as if they were symbols.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            AREA_MEASURE_TYPE_CODES,
        )

        built = set(AREA_MEASURE_TYPE_CODES.values())

        for parent_code in ("270500", "270700"):

            self.assertNotIn(parent_code, built)


    def test_colour_default_follows_the_audit_per_measure_type(self):

        # B2 is the first batch with MIXED colour defaults, and the
        # default expression is DERIVED from the inventory rather than
        # restated - so this checks the derivation, not a copy of it.
        from MilitaryCartographyTools.military_symbology import (
            obstacle_control_measures as module,
        )

        layer = module.create_obstacle_control_measures_areas_layer()

        idx = layer.fields().indexOf("colour")

        expression = QgsExpression(
            layer.defaultValueDefinition(idx).expression()
        )

        for measure_type, expected in (
            ("obstacle_belt", GREEN),
            ("obstacle_restricted_zone", GREEN),
            ("mined_area", GREEN),
            ("uxo_area", BLACK),
        ):

            with self.subTest(measure_type=measure_type):

                feature = QgsFeature(layer.fields())
                feature.setAttribute("measure_type", measure_type)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                self.assertEqual(expression.evaluate(context), expected)


    def test_every_measure_type_has_its_own_renderer_rule(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            AREA_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_areas_layer,
        )

        layer = create_obstacle_control_measures_areas_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertEqual(labels, set(AREA_MEASURE_TYPE_LABELS))


    def test_only_the_two_carved_zones_serrate_inward(self):

        # The maintainer's own catch against the template pictures:
        # Belt and Zone spike outward, Free Zone and Restricted Zone
        # cut their teeth inward. Read off the real geometry
        # expressions so a future edit cannot flip one silently.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_areas_layer,
        )

        layer = create_obstacle_control_measures_areas_layer()

        inward = set()

        for rule in layer.renderer().rootRule().children():

            for index in range(rule.symbol().symbolLayerCount()):

                symbol_layer = rule.symbol().symbolLayer(index)

                expression = getattr(
                    symbol_layer, "geometryExpression", lambda: ""
                )()

                if "mct_serrate_outline" in expression and "false" in expression:
                    inward.add(rule.label())

        self.assertEqual(
            inward,
            {"obstacle_free_zone", "obstacle_restricted_zone"}
        )


    def test_areas_layer_is_created_and_added(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            AREAS_LAYER_NAME,
            add_obstacle_control_measures_areas_layer,
        )

        iface = FakeIface()

        layer = add_obstacle_control_measures_areas_layer(iface)

        self.assertIsNotNone(layer)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)),
            1
        )


class TestSerratedOutline(QgisTestCase):

    """
    The sawtooth construction behind the four obstacle zones, tested on
    plain point lists - the same way _crenellated_ring_points() is,
    and for the same reason: the geometry is the part that can be wrong
    without any test noticing.
    """

    def _square(self):

        from qgis.core import QgsPointXY

        return [
            QgsPointXY(0, 0),
            QgsPointXY(10, 0),
            QgsPointXY(10, 10),
            QgsPointXY(0, 10),
        ]


    def test_emits_one_apex_per_tooth(self):

        from MilitaryCartographyTools.expressions.military_symbology_functions import (
            _serrated_ring_points,
        )

        points = _serrated_ring_points(self._square(), 8)

        # start + (ground, apex, tooth_end) per tooth
        self.assertEqual(len(points), 1 + 8 * 3)


    def test_apexes_sit_exactly_one_step_off_the_ring(self):

        from qgis.core import QgsGeometry
        from MilitaryCartographyTools.expressions.military_symbology_functions import (
            _serrated_ring_points,
        )

        square = self._square()

        ring = QgsGeometry.fromPolylineXY(square + [square[0]])

        step = ring.length() / (8 * 2)

        offsets = {
            round(ring.distance(QgsGeometry.fromPointXY(point)), 6)
            for point in _serrated_ring_points(square, 8)
        }

        self.assertEqual(offsets, {0.0, round(step, 6)})


    def test_teeth_point_outward_or_inward_on_request(self):

        from qgis.core import QgsGeometry
        from MilitaryCartographyTools.expressions.military_symbology_functions import (
            _serrated_ring_points,
        )

        square = self._square()

        polygon = QgsGeometry.fromPolygonXY([square + [square[0]]])

        ring = QgsGeometry.fromPolylineXY(square + [square[0]])

        def apexes(outward):

            return [
                point
                for point in _serrated_ring_points(square, 8, outward)
                if ring.distance(QgsGeometry.fromPointXY(point)) > 1e-9
            ]

        for point in apexes(True):

            self.assertFalse(
                polygon.contains(QgsGeometry.fromPointXY(point))
            )

        for point in apexes(False):

            self.assertTrue(
                polygon.contains(QgsGeometry.fromPointXY(point))
            )


    def test_direction_is_independent_of_ring_winding(self):

        # Winding order is not normalised anywhere in this project, and
        # a hand-digitized polygon can arrive either way round - so the
        # outward test must not depend on it.
        from qgis.core import QgsGeometry
        from MilitaryCartographyTools.expressions.military_symbology_functions import (
            _serrated_ring_points,
        )

        square = self._square()
        reversed_square = list(reversed(square))

        for ring_points in (square, reversed_square):

            polygon = QgsGeometry.fromPolygonXY(
                [ring_points + [ring_points[0]]]
            )

            ring = QgsGeometry.fromPolylineXY(
                ring_points + [ring_points[0]]
            )

            for point in _serrated_ring_points(ring_points, 8):

                if ring.distance(QgsGeometry.fromPointXY(point)) > 1e-9:

                    self.assertFalse(
                        polygon.contains(QgsGeometry.fromPointXY(point))
                    )


class TestMineTypes(QgisTestCase):

    """
    Batch B3's mine-type mechanism, shared by Mined Area's own Field A
    and by the whole minefield family - see the module's own B3 section
    for why this is a FIELD rather than extra measure types.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_every_mine_type_maps_to_a_b1_point_entity(self):

        # The glyphs are batch B1's own icons, not new artwork - and
        # they are the three the standard's own examples draw in the A
        # field. If B1's vocabulary ever loses one, this fails rather
        # than silently rendering milsymbol's unknown icon.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINE_TYPE_LABELS,
            POINT_ENTITY_LABELS,
            _MINE_TYPE_ENTITIES,
            _MINE_TYPE_SEQUENCE,
        )

        self.assertEqual(set(_MINE_TYPE_SEQUENCE), set(MINE_TYPE_LABELS))

        for entity in _MINE_TYPE_ENTITIES.values():

            self.assertIn(entity, POINT_ENTITY_LABELS)

        for sequence in _MINE_TYPE_SEQUENCE.values():

            for member in sequence:

                self.assertIn(member, _MINE_TYPE_ENTITIES)


    def test_only_the_combined_type_draws_two_glyphs(self):

        # The maintainer's rule for areas: "just one symbol each of the
        # selected mines is adequate".
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _MINE_TYPE_SEQUENCE,
        )

        for mine_type, sequence in _MINE_TYPE_SEQUENCE.items():

            with self.subTest(mine_type=mine_type):

                expected = 2 if mine_type == "antipersonnel_antitank" else 1

                self.assertEqual(len(sequence), expected)


    def test_default_mine_type_is_a_real_option(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            DEFAULT_MINE_TYPE,
            MINE_TYPE_LABELS,
        )

        self.assertIn(DEFAULT_MINE_TYPE, MINE_TYPE_LABELS)


    def test_mined_area_glyph_resolves_to_a_real_icon(self):

        import base64

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINE_TYPE_LABELS,
            create_obstacle_control_measures_areas_layer,
        )

        layer = create_obstacle_control_measures_areas_layer()

        expression = QgsExpression(
            _mine_glyph_expression_for(layer, "mined_area")
        )

        for mine_type in MINE_TYPE_LABELS:

            with self.subTest(mine_type=mine_type):

                # Built from the layer's OWN defaults, then only the
                # mine type varied. Hardcoding affiliation="friend"
                # here is what let the glyphs ship broken: the Areas
                # layer defaults it to "unspecified", which is not a
                # SIDC standard identity, so every glyph rendered as
                # milsymbol's unknown icon in real use while this test
                # stayed green. Same mistake, and same shape, as the
                # original B1 points bug.
                feature = QgsFeature(layer.fields())

                context = layer.createExpressionContext()

                for field in layer.fields():

                    default = layer.defaultValueDefinition(
                        layer.fields().indexOf(field.name())
                    ).expression()

                    if default:
                        feature.setAttribute(
                            field.name(),
                            QgsExpression(default).evaluate(context)
                        )

                feature.setAttribute("measure_type", "mined_area")
                feature.setAttribute("mine_type", mine_type)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                path = expression.evaluate(context)

                self.assertTrue(path.startswith("base64:"), path)

                svg = base64.b64decode(
                    path[len("base64:"):]
                ).decode("utf-8")

                # Not merely "a path came back" - milsymbol's unknown
                # icon is a well-formed base64 path too.
                self.assertNotIn("94.8206,78.1372", svg)


def _mine_glyph_expression_for(layer, measure_type):

    """The A field's first glyph expression, read off the real symbol."""

    for rule in layer.renderer().rootRule().children():

        if rule.label() != measure_type:
            continue

        symbol = rule.symbol()

        for index in range(symbol.symbolLayerCount()):

            sub_symbol = symbol.symbolLayer(index).subSymbol()

            if sub_symbol is None:
                continue

            for sub_index in range(sub_symbol.symbolLayerCount()):

                properties = sub_symbol.symbolLayer(
                    sub_index
                ).dataDefinedProperties()

                if properties.isActive(QgsSymbolLayer.Property.Name):

                    return properties.property(
                        QgsSymbolLayer.Property.Name
                    ).expressionString()

    raise AssertionError(f"no mine glyph found for {measure_type}")


class TestMinefieldsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_covers_every_minefield_code_in_the_table(self):

        # Five codes over four measure types: Completed and Planned are
        # ONE type split by `status`, per the maintainer's audit.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINEFIELD_MEASURE_TYPE_CODES,
            MINEFIELD_MEASURE_TYPE_LABELS,
        )

        self.assertEqual(
            set(MINEFIELD_MEASURE_TYPE_CODES),
            set(MINEFIELD_MEASURE_TYPE_LABELS)
        )

        covered = {
            code
            for codes in MINEFIELD_MEASURE_TYPE_CODES.values()
            for code in codes
        }

        self.assertEqual(
            covered,
            {"270701", "270702", "270703", "270704", "270705"}
        )

        self.assertEqual(
            MINEFIELD_MEASURE_TYPE_CODES["minefield"],
            ("270701", "270702")
        )


    def test_the_whole_b3_batch_is_built_across_the_two_layers(self):

        # B3's own inventory slice, split between the Minefields layer
        # (the static boxes) and the Areas layer (the two dynamic ones).
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            AREA_MEASURE_TYPE_CODES,
            MINEFIELD_MEASURE_TYPE_CODES,
        )

        built = {
            code
            for codes in MINEFIELD_MEASURE_TYPE_CODES.values()
            for code in codes
        } | set(AREA_MEASURE_TYPE_CODES.values())

        self.assertTrue(
            set(inventory_for_batch("B3")).issubset(built),
            set(inventory_for_batch("B3")) - built
        )


    def test_affiliation_vocabulary_is_the_points_one(self):

        # The box is hand-built, but the mine glyphs inside it are real
        # milsymbol icons, so `affiliation` DOES reach build_sidc().
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_minefields_layer,
        )
        from MilitaryCartographyTools.military_symbology.sidc import AFFILIATIONS

        layer = create_obstacle_control_measures_minefields_layer()

        idx = layer.fields().indexOf("affiliation")

        offered = layer.editorWidgetSetup(idx).config().get("map", {})

        if isinstance(offered, list):
            stored = [v for entry in offered for v in entry.values()]
        else:
            stored = list(offered.values())

        for value in stored:

            self.assertIn(value, AFFILIATIONS)


    def test_combined_mine_type_alternates_along_the_box(self):

        # "in case of line features - alternating mines is a must" -
        # the box's three glyphs alternate rather than repeating.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _MINE_TYPE_ENTITIES,
            _minefield_glyph_sidc_expression,
        )

        antipersonnel = _MINE_TYPE_ENTITIES["antipersonnel"]
        antitank = _MINE_TYPE_ENTITIES["antitank"]

        first = _minefield_glyph_sidc_expression(0)
        second = _minefield_glyph_sidc_expression(1)
        third = _minefield_glyph_sidc_expression(2)

        for expression, expected in (
            (first, antipersonnel),
            (second, antitank),
            (third, antipersonnel),
        ):

            combined_clause = (
                "WHEN \"mine_type\" = 'antipersonnel_antitank'"
                f" THEN '{expected}'"
            )

            self.assertIn(combined_clause, expression)


    def test_eny_sits_on_the_box_side_not_clear_of_it(self):

        # The maintainer's own B3 correction: "the ENY is on the
        # vertical lines, not outside the lines". So the offset is
        # EXACTLY half the box width - no clearance gap - and the box
        # is masked so its side breaks through the text.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _MASKED_MINEFIELD_BOX_LAYER_ID,
            _MINEFIELD_ENEMY_BOX_WIDTH_MM,
            create_obstacle_control_measures_minefields_layer,
        )

        layer = create_obstacle_control_measures_minefields_layer()

        offsets = set()

        masked_ids = set()

        for rule in layer.labeling().rootRule().children():

            # Each accessor held in its OWN variable. QgsPalLayerSettings
            # .settings()/.format() return BY VALUE, and chaining off
            # them (settings.format().mask()...) lets the temporary's
            # C++ object be collected mid-expression - which segfaulted
            # the interpreter when this very test was first written
            # that way.
            settings = rule.settings()

            offsets.add(round(settings.xOffset, 6))

            text_format = settings.format()

            mask = text_format.mask()

            for masked_layer in mask.maskedSymbolLayers():

                masked_ids.add(masked_layer.symbolLayerIdV2())

        self.assertIn(_MASKED_MINEFIELD_BOX_LAYER_ID, masked_ids)

        half_width = round(_MINEFIELD_ENEMY_BOX_WIDTH_MM * 0.5, 6)

        self.assertIn(half_width, offsets)
        self.assertIn(-half_width, offsets)


    def test_the_enemy_variants_draw_a_wider_box(self):

        # Needed so "ENY" riding the sides does not reach in over the
        # outer mine glyphs - caught by render at the standard width.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _MINEFIELD_BOX_WIDTH_MM,
            _MINEFIELD_ENEMY_BOX_WIDTH_MM,
            _MINEFIELD_ENEMY_TYPES,
            create_obstacle_control_measures_minefields_layer,
        )

        self.assertGreater(
            _MINEFIELD_ENEMY_BOX_WIDTH_MM, _MINEFIELD_BOX_WIDTH_MM
        )

        layer = create_obstacle_control_measures_minefields_layer()

        for rule in layer.renderer().rootRule().children():

            box = rule.symbol().symbolLayer(0)

            expression = box.dataDefinedProperties().property(
                QgsSymbolLayer.Property.Width
            ).expressionString()

            feature = QgsFeature(layer.fields())
            feature.setAttribute("measure_type", rule.label())

            context = layer.createExpressionContext()
            context.setFeature(feature)

            expected = (
                _MINEFIELD_ENEMY_BOX_WIDTH_MM
                if rule.label() in _MINEFIELD_ENEMY_TYPES
                else _MINEFIELD_BOX_WIDTH_MM
            )

            with self.subTest(measure_type=rule.label()):

                self.assertAlmostEqual(
                    QgsExpression(expression).evaluate(context),
                    expected,
                    places=6
                )


    def test_mine_glyphs_carry_the_same_thicker_stroke_as_b1(self):

        # "the anti-personnel mine's ears ... as well as unknown mine
        # ... increase their stroke width in line with B1". These draw
        # at 5mm against a B1 marker's 8mm, so a thin stroke reads
        # fainter still.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _THICKER_STROKE_FACTOR,
            _mine_glyph_sidc_expression,
            _minefield_glyph_sidc_expression,
        )

        for expression in (
            _mine_glyph_sidc_expression(0),
            _minefield_glyph_sidc_expression(0),
        ):

            self.assertIn(str(_THICKER_STROKE_FACTOR), expression)


    def test_minefields_layer_is_created_and_added(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINEFIELDS_LAYER_NAME,
            add_obstacle_control_measures_minefields_layer,
        )

        iface = FakeIface()

        self.assertIsNotNone(
            add_obstacle_control_measures_minefields_layer(iface)
        )

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(MINEFIELDS_LAYER_NAME)),
            1
        )


class TestB1SmokeTestFollowUps(QgisTestCase):

    """
    The four adjustments the maintainer asked for after smoke-testing
    B1 and B2 (2026-08-12), pinned so a later edit cannot quietly undo
    them.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _rendered_svg(self, layer, entity):

        import base64

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", entity)
        feature.setAttribute("status", "present")
        feature.setAttribute("colour", GREEN)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def _rendered_size(self, layer, entity):

        svg_layer = layer.renderer().symbol().symbolLayer(0)

        feature = QgsFeature(layer.fields())
        feature.setAttribute("entity", entity)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        size, ok = svg_layer.dataDefinedProperties().valueAsDouble(
            QgsSymbolLayer.Property.Size, context, 0.0
        )

        self.assertTrue(ok)

        return size


    def test_named_entities_render_a_thicker_stroke(self):

        import re

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            POINT_ENTITY_LABELS,
            _THICKER_STROKE_ENTITIES,
            _THICKER_STROKE_FACTOR,
            create_obstacle_control_measures_points_layer,
        )

        layer = create_obstacle_control_measures_points_layer()

        for entity in POINT_ENTITY_LABELS:

            with self.subTest(entity=entity):

                svg = self._rendered_svg(layer, entity)

                widths = {
                    float(width)
                    for width in re.findall(r'stroke-width="([\d.]+)"', svg)
                }

                if entity in _THICKER_STROKE_ENTITIES:

                    # milsymbol's own base stroke for these icons is 3.
                    self.assertIn(3.0 * _THICKER_STROKE_FACTOR, widths)

                else:

                    self.assertNotIn(3.0 * _THICKER_STROKE_FACTOR, widths)


    def test_directional_mine_is_scaled_to_match_its_plain_sibling(self):

        # QGIS sizes an SVG marker by WIDTH, so the wider viewBox has to
        # be compensated for the CIRCLE to come out the same size. The
        # ratio is asserted against the real rendered viewBoxes rather
        # than against the hardcoded constant, so it stays true if
        # milsymbol's own artwork changes.
        import re

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_points_layer,
        )

        layer = create_obstacle_control_measures_points_layer()

        def view_box_width(entity):

            svg = self._rendered_svg(layer, entity)

            return float(
                re.search(r'viewBox="[^"]*?([\d.]+) [\d.]+"', svg).group(1)
            )

        plain_width = view_box_width("antipersonnel_mine")
        directional_width = view_box_width("antipersonnel_mine_directional")

        self.assertGreater(directional_width, plain_width)

        expected_ratio = directional_width / plain_width

        actual_ratio = (
            self._rendered_size(layer, "antipersonnel_mine_directional")
            / self._rendered_size(layer, "antipersonnel_mine")
        )

        self.assertAlmostEqual(actual_ratio, expected_ratio, places=6)


    def test_towers_render_30_percent_larger(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_points_layer,
        )

        layer = create_obstacle_control_measures_points_layer()

        baseline = self._rendered_size(layer, "antipersonnel_mine")

        for entity in ("tower_low", "tower_high"):

            with self.subTest(entity=entity):

                self.assertAlmostEqual(
                    self._rendered_size(layer, entity) / baseline,
                    1.3,
                    places=6
                )


    def test_mine_indicator_offers_only_the_standards_own_values(self):

        # Field H is not free text: the standard's own Note gives it
        # exactly "S" and "+S" (or nothing at all).
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINE_INDICATOR_LABELS,
        )

        self.assertEqual(set(MINE_INDICATOR_LABELS), {"", "S", "+S"})


    def test_mine_indicator_is_a_dropdown_on_both_layers(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_areas_layer,
            create_obstacle_control_measures_minefields_layer,
        )

        for factory in (
            create_obstacle_control_measures_areas_layer,
            create_obstacle_control_measures_minefields_layer,
        ):

            layer = factory()

            index = layer.fields().indexOf("mine_indicator")

            with self.subTest(layer=layer.name()):

                self.assertEqual(
                    layer.editorWidgetSetup(index).type(),
                    "ValueMap"
                )

                # And it names itself, which is what the maintainer's
                # "what is this field for?" actually needed.
                self.assertIn("Field H", layer.fields().at(index).alias())


    def test_tower_designation_sits_at_the_top_of_the_glyph(self):

        # "the number in towers should be aligned with the top not
        # center of glyph" - a NEGATIVE yOffset is what raises a label
        # here, and it is derived from the tower's own drawn height so
        # it tracks the size multiplier rather than drifting off it.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _POINTS_DEFAULT_MARKER_SIZE_MM,
            _POINT_SIZE_MULTIPLIERS,
            create_obstacle_control_measures_points_layer,
        )

        layer = create_obstacle_control_measures_points_layer()

        settings = layer.labeling().settings()

        self.assertLess(settings.yOffset, 0)

        tower_height = (
            _POINTS_DEFAULT_MARKER_SIZE_MM
            * _POINT_SIZE_MULTIPLIERS["tower_low"]
            * (98.0 / 108.0)
        )

        self.assertAlmostEqual(
            settings.yOffset, -tower_height * 0.38, places=6
        )

class TestScaleSvgStrokeWidth(QgisTestCase):

    def test_multiplies_every_stroke_width(self):

        from MilitaryCartographyTools.military_symbology.symbol_engine import (
            scale_svg_stroke_width,
        )

        svg = '<path stroke-width="3"/><path stroke-width="8"/>'

        self.assertEqual(
            scale_svg_stroke_width(svg, 1.8),
            '<path stroke-width="5.4"/><path stroke-width="14.4"/>'
        )


    def test_a_factor_of_one_or_none_leaves_the_svg_untouched(self):

        from MilitaryCartographyTools.military_symbology.symbol_engine import (
            scale_svg_stroke_width,
        )

        svg = '<path stroke-width="3"/>'

        self.assertEqual(scale_svg_stroke_width(svg, 1), svg)
        self.assertEqual(scale_svg_stroke_width(svg, None), svg)



class TestEveryMilsymbolGlyphOnHandBuiltLayers(QgisTestCase):

    """
    Cross-layer guard for the defect that shipped twice: a layer whose
    hand-built symbology EMBEDS milsymbol glyphs, where some field
    feeding build_sidc() carries a value that is legitimate for the
    hand-built part but not a SIDC value.

    First time it was the Points layer's affiliation default (B1).
    Second time it was the same field on the AREAS layer, which
    correctly defaults to "unspecified" for its own outline and then
    passed that straight into the mine glyphs' SIDC - so Mined Area and
    Dynamic Depiction drew "?" for every mine.

    The lesson is not "check affiliation". It is that these layers must
    be rendered FROM THEIR OWN DEFAULTS and the result inspected, since
    a broken SIDC still yields a perfectly well-formed base64 path.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _feature_from_defaults(self, layer, **overrides):

        feature = QgsFeature(layer.fields())

        context = layer.createExpressionContext()

        for field in layer.fields():

            default = layer.defaultValueDefinition(
                layer.fields().indexOf(field.name())
            ).expression()

            if default:
                feature.setAttribute(
                    field.name(), QgsExpression(default).evaluate(context)
                )

        for name, value in overrides.items():
            feature.setAttribute(name, value)

        return feature


    def _glyph_paths(self, layer, feature):

        """Every data-defined SVG path any symbol layer resolves to."""

        context = layer.createExpressionContext()
        context.setFeature(feature)

        renderer = layer.renderer()

        symbols = [
            rule.symbol() for rule in renderer.rootRule().children()
        ]

        paths = []

        def walk(symbol):

            for index in range(symbol.symbolLayerCount()):

                symbol_layer = symbol.symbolLayer(index)

                properties = symbol_layer.dataDefinedProperties()

                if properties.isActive(QgsSymbolLayer.Property.Name):

                    value, ok = properties.valueAsString(
                        QgsSymbolLayer.Property.Name, context, ""
                    )

                    if ok and value.startswith("base64:"):
                        paths.append(value)

                sub_symbol = symbol_layer.subSymbol()

                if sub_symbol is not None:
                    walk(sub_symbol)

        for symbol in symbols:
            walk(symbol)

        return paths


    def _assert_no_unknown_glyph(self, layer, feature, label):

        import base64

        paths = self._glyph_paths(layer, feature)

        self.assertTrue(paths, f"{label}: no milsymbol glyph resolved at all")

        for path in paths:

            svg = base64.b64decode(path[len("base64:"):]).decode("utf-8")

            self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg, label)


    def test_areas_layer_mine_glyphs_survive_its_own_defaults(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINE_TYPE_LABELS,
            create_obstacle_control_measures_areas_layer,
        )

        layer = create_obstacle_control_measures_areas_layer()

        for measure_type in (
            "mined_area", "minefield_dynamic", "minefield_dynamic_dummy"
        ):

            for mine_type in MINE_TYPE_LABELS:

                with self.subTest(measure_type=measure_type,
                                  mine_type=mine_type):

                    feature = self._feature_from_defaults(
                        layer,
                        measure_type=measure_type,
                        mine_type=mine_type,
                    )

                    self._assert_no_unknown_glyph(
                        layer, feature, f"{measure_type}/{mine_type}"
                    )


    def test_minefields_layer_glyphs_survive_its_own_defaults(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            MINEFIELD_MEASURE_TYPE_LABELS,
            MINE_TYPE_LABELS,
            create_obstacle_control_measures_minefields_layer,
        )

        layer = create_obstacle_control_measures_minefields_layer()

        for measure_type in MINEFIELD_MEASURE_TYPE_LABELS:

            for mine_type in MINE_TYPE_LABELS:

                with self.subTest(measure_type=measure_type,
                                  mine_type=mine_type):

                    feature = self._feature_from_defaults(
                        layer,
                        measure_type=measure_type,
                        mine_type=mine_type,
                    )

                    self._assert_no_unknown_glyph(
                        layer, feature, f"{measure_type}/{mine_type}"
                    )


    def test_glyphs_survive_every_affiliation_the_form_offers(self):

        # The Areas layer legitimately offers "unspecified" - it is the
        # lines/areas vocabulary and its outline needs the fifth value.
        # The glyphs must be immune to it, not merely lucky.
        from MilitaryCartographyTools.military_symbology._control_measure_shared import (
            AFFILIATION_LABELS,
        )
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_areas_layer,
        )

        layer = create_obstacle_control_measures_areas_layer()

        for affiliation in AFFILIATION_LABELS:

            with self.subTest(affiliation=affiliation):

                feature = self._feature_from_defaults(
                    layer,
                    measure_type="mined_area",
                    affiliation=affiliation,
                )

                self._assert_no_unknown_glyph(layer, feature, affiliation)


class TestScatterPoints(QgisTestCase):

    """
    mct_scatter_points() - the mine placement for dynamic minefields,
    replacing QgsRandomMarkerFillSymbolLayer after the maintainer's
    "should not touch the perimeter, should not touch each other".
    """

    def setUp(self):

        super().setUp()

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _polygon(self):

        from qgis.core import QgsGeometry, QgsPointXY

        corners = [
            QgsPointXY(0, 0),
            QgsPointXY(100, 0),
            QgsPointXY(100, 70),
            QgsPointXY(0, 70),
        ]

        return QgsGeometry.fromPolygonXY([corners + [corners[0]]])


    def _scatter(self, geometry, count=7, gap=0.26, inset=0.14,
                 modulus=1, remainder=0):

        # Evaluated through QgsExpression rather than called directly:
        # @qgsfunction replaces the Python function with a
        # QgsPyExpressionFunction, which is not callable.
        expression = QgsExpression(
            "mct_scatter_points(geom_from_wkt('{}'), {}, {}, {}, {}, {})".format(
                geometry.asWkt(), count, gap, inset, modulus, remainder
            )
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_points_stay_clear_of_the_perimeter(self):

        import math

        from qgis.core import QgsGeometry

        polygon = self._polygon()

        boundary = QgsGeometry.fromPolylineXY(polygon.asPolygon()[0])

        inset = 0.14 * math.sqrt(polygon.area())

        for point in self._scatter(polygon).asMultiPoint():

            self.assertGreaterEqual(
                boundary.distance(QgsGeometry.fromPointXY(point)),
                inset * 0.9
            )


    def test_points_stay_clear_of_each_other(self):

        import math

        polygon = self._polygon()

        minimum_gap = 0.26 * math.sqrt(polygon.area())

        points = self._scatter(polygon).asMultiPoint()

        for first in range(len(points)):

            for second in range(first + 1, len(points)):

                self.assertGreaterEqual(
                    points[first].distance(points[second]),
                    minimum_gap
                )


    def test_the_same_shape_always_scatters_the_same_way(self):

        # QGIS re-evaluates this on every pan and zoom; an unseeded
        # scatter would crawl across the screen.
        polygon = self._polygon()

        first = self._scatter(polygon).asWkt()
        second = self._scatter(polygon).asWkt()

        self.assertEqual(first, second)


    def test_different_shapes_scatter_differently(self):

        from qgis.core import QgsGeometry, QgsPointXY

        other = [
            QgsPointXY(500, 500),
            QgsPointXY(600, 500),
            QgsPointXY(600, 570),
            QgsPointXY(500, 570),
        ]

        shifted = QgsGeometry.fromPolygonXY([other + [other[0]]])

        self.assertNotEqual(
            self._scatter(self._polygon()).asWkt(),
            self._scatter(shifted).asWkt()
        )


    def test_the_two_alternating_passes_partition_one_placement(self):

        # The combined mine type draws the SAME scatter twice, taking
        # alternate points - so the two halves are disjoint and, taken
        # together, are exactly the single-pass placement. Two
        # independent scatters could not guarantee they missed each
        # other.
        polygon = self._polygon()

        whole = [
            point.asWkt()
            for point in self._scatter(polygon).asMultiPoint()
        ]

        evens = [
            point.asWkt()
            for point in self._scatter(
                polygon, modulus=2, remainder=0
            ).asMultiPoint()
        ]

        odds = [
            point.asWkt()
            for point in self._scatter(
                polygon, modulus=2, remainder=1
            ).asMultiPoint()
        ]

        self.assertEqual(set(evens) & set(odds), set())

        self.assertEqual(sorted(evens + odds), sorted(whole))


    def test_a_sliver_gets_fewer_mines_rather_than_no_symbol(self):

        from qgis.core import QgsGeometry, QgsPointXY

        sliver = [
            QgsPointXY(0, 0),
            QgsPointXY(200, 0),
            QgsPointXY(200, 2),
            QgsPointXY(0, 2),
        ]

        geometry = QgsGeometry.fromPolygonXY([sliver + [sliver[0]]])

        result = self._scatter(geometry)

        self.assertFalse(result.isEmpty())


class TestDecoyChevronSpan(QgisTestCase):

    """
    One chevron function, two spans - pinned because widening it for
    the Dummy Dynamic area could silently widen the two Decoy Mined
    Area variants too, whose template keeps theirs well inside the
    boundary.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _chevron_width(self, half_span_fraction=None):

        from qgis.core import QgsGeometry, QgsPointXY

        corners = [
            QgsPointXY(0, 0),
            QgsPointXY(100, 0),
            QgsPointXY(100, 60),
            QgsPointXY(0, 60),
        ]

        polygon = QgsGeometry.fromPolygonXY([corners + [corners[0]]])

        arguments = "geom_from_wkt('{}')".format(polygon.asWkt())

        if half_span_fraction is not None:
            arguments += ", {}".format(half_span_fraction)

        expression = QgsExpression(f"mct_decoy_chevron({arguments})")

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result.boundingBox().width()


    def test_the_default_span_stays_well_inside_the_shape(self):

        # 0.24 either side of centre - the two Decoy Mined Area
        # variants draw their chevron INSIDE the boundary.
        self.assertAlmostEqual(self._chevron_width(), 100 * 0.48, places=6)


    def test_the_dummy_dynamic_span_matches_the_area_width(self):

        # "the chevron above should ideally extend to the horizontal
        # extent of the area" - the maintainer, on the Dummy Dynamic,
        # whose chevron sits ABOVE the shape rather than inside it.
        self.assertAlmostEqual(self._chevron_width(0.5), 100.0, places=6)


    def test_only_the_dummy_dynamic_asks_for_the_full_span(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_areas_layer,
        )

        layer = create_obstacle_control_measures_areas_layer()

        widened = set()

        for rule in layer.renderer().rootRule().children():

            symbol = rule.symbol()

            for index in range(symbol.symbolLayerCount()):

                expression = getattr(
                    symbol.symbolLayer(index), "geometryExpression",
                    lambda: ""
                )()

                if "mct_decoy_chevron($geometry, 0.5)" in expression:
                    widened.add(rule.label())

        self.assertEqual(widened, {"minefield_dynamic_dummy"})


class TestWireObstacles(QgisTestCase):

    """
    Batch B4's wire family (290301-290309) - nine measure types sharing
    ONE symbol, with the glyph and the line chosen by expression.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_excludes_the_wire_obstacles_parent_row(self):

        # 290300's own template cell reads "N/A" - a heading, not a
        # symbol. The exact trap the module docstring warns about.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            WIRE_MEASURE_TYPE_CODES,
        )

        self.assertNotIn("290300", set(WIRE_MEASURE_TYPE_CODES.values()))


    def test_covers_every_wire_code_the_table_lists(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            WIRE_MEASURE_TYPE_CODES,
            WIRE_MEASURE_TYPE_LABELS,
        )

        self.assertEqual(
            set(WIRE_MEASURE_TYPE_CODES), set(WIRE_MEASURE_TYPE_LABELS)
        )

        self.assertEqual(
            set(WIRE_MEASURE_TYPE_CODES.values()),
            {f"2903{n:02d}" for n in range(1, 10)}
        )


    def test_no_two_wire_types_look_alike(self):

        # Two pairs shipped IDENTICAL in the first build and only a
        # render caught it. The signature is the whole construction -
        # glyph, spacing and which lines run through it - because that
        # is exactly what the manual varies between these nine.
        # Covers EVERY line obstacle, not just the wire nine - the
        # toothed family shares the same construction, so it is the
        # same invariant and the same way of getting it wrong.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_SPECS,
            LINE_MEASURE_TYPE_LABELS,
        )

        self.assertEqual(
            set(_WIRE_SPECS) | {
                "abatis", "antitank_ditch_reinforced", "mine_cluster",
                "trip_wire", "block", "disrupt", "fix", "turn",
                "obstacle_bypass_easy", "obstacle_bypass_difficult",
                "obstacle_bypass_impossible", "bridge_or_gap",
                "roadblock_planned", "roadblock_readiness_1",
                "roadblock_readiness_2", "roadblock_complete",
            },
            set(LINE_MEASURE_TYPE_LABELS)
        )

        signatures = {}

        for measure_type, spec in _WIRE_SPECS.items():

            signature = (spec.glyph, spec.gap, tuple(spec.lines))

            self.assertNotIn(
                signature, signatures,
                f"{measure_type} is identical to {signatures.get(signature)}"
            )

            signatures[signature] = measure_type


    def test_the_specs_match_the_manual_as_the_maintainer_read_it(self):

        # Transcribed from the maintainer's own description, which is
        # the source of truth for these nine - the first build guessed
        # the shapes from the template pictures and got several wrong.
        #
        # Lines are offsets in half-glyph-heights: 0 through the middle,
        # +1 along the bottom, -1 along the top.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_SPECS,
        )

        expected = {
            "unspecified_wire_obstacle": ("cross", 1.5, ()),
            "single_fence": ("cross", 4.0, (0,)),
            "double_fence": ("double_cross", 3.0, (0,)),
            "double_apron_fence": ("cross", 1.5, (0,)),
            "low_wire_fence": ("cross", 1.5, (1,)),
            "high_wire_fence": ("cross", 1.5, (-1, 1)),
            "single_concertina": ("oval", 1.5, (1,)),
            "double_strand_concertina": ("oval", 1.5, (0, 1)),
            "triple_strand_concertina": ("oval", 1.5, (-1, 1)),
        }

        # Scoped to the nine WIRE types: this asserts the maintainer's
        # own transcription of the manual, and the toothed obstacles
        # that later joined _WIRE_SPECS came from the standard's own
        # templates instead.
        self.assertEqual(
            {
                name: (spec.glyph, spec.gap, tuple(spec.lines))
                for name, spec in _WIRE_SPECS.items()
                if name in expected
            },
            expected
        )


    def test_which_obstacles_draw_no_straight_line(self):

        # Three kinds have no separate line layer, for two different
        # reasons: Unspecified Wire Obstacle has no line at all in the
        # standard, while the two ditches and the wall ARE their line -
        # the triangles' bases and the sawtooth's flats form it.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_SPECS,
        )

        without_lines = {
            name for name, spec in _WIRE_SPECS.items() if not spec.lines
        }

        self.assertEqual(
            without_lines,
            {
                "unspecified_wire_obstacle",
                "antitank_ditch_under_construction",
                "antitank_ditch_completed",
                "antitank_wall",
                "obstacle_line",
            }
        )


    def test_the_tiling_obstacles_overlap_to_avoid_hairline_joins(self):

        # Both ditches and the antitank wall butt their glyphs edge to
        # edge to form one continuous profile. At exactly one glyph
        # width apart they leave a visible hairline at every join.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_GLYPH_SIZE_MM,
            _WIRE_SPECS,
            _WIRE_TILE_OVERLAP_MM,
        )

        self.assertGreater(_WIRE_TILE_OVERLAP_MM, 0)

        tiling = {
            name for name, spec in _WIRE_SPECS.items() if spec.gap == 0
        }

        self.assertEqual(
            tiling,
            {
                "antitank_ditch_under_construction",
                "antitank_ditch_completed",
                "antitank_wall",
                "obstacle_line",
            }
        )

        self.assertLess(_WIRE_TILE_OVERLAP_MM, _WIRE_GLYPH_SIZE_MM * 0.25)


    def test_the_paired_glyph_is_drawn_wide_enough_to_stay_square(self):

        # QGIS sizes an SVG marker by WIDTH, and double_cross holds two
        # crosses plus the gap between them - so without the multiplier
        # each of its crosses would render smaller than its siblings'.
        # Asserted as DERIVED from the pair gap, because an earlier
        # version wrote the viewBox width and the multiplier as two
        # separate literals and they disagreed the moment the maintainer
        # changed the spacing.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_GLYPH_WIDTH_MULTIPLIERS,
            _WIRE_PAIR_GAP,
        )

        self.assertEqual(_WIRE_PAIR_GAP, 0.25)

        self.assertAlmostEqual(
            _WIRE_GLYPH_WIDTH_MULTIPLIERS.get("double_cross"),
            2 + _WIRE_PAIR_GAP
        )


    def test_every_wire_symbol_builds(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertEqual(labels, set(LINE_MEASURE_TYPE_LABELS))


    def test_the_line_always_extends_beyond_the_glyphs(self):

        # "the line should always be longer or extend beyond the Xs or
        # 0s". Guaranteed by running the glyphs along a TRIMMED copy of
        # the line, not by offsetAlongLine - that insets the first glyph
        # only, and a render caught Single Fence still ending flush
        # because markers land at fixed intervals from the start.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_END_TRIM,
            _WIRE_SPECS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertGreater(_WIRE_END_TRIM, 0)

        layer = create_obstacle_control_measures_lines_layer()

        for rule in layer.renderer().rootRule().children():

            symbol = rule.symbol()

            expressions = [
                getattr(
                    symbol.symbolLayer(index), "geometryExpression",
                    lambda: ""
                )()
                for index in range(symbol.symbolLayerCount())
            ]

            trimmed = [e for e in expressions if "line_substring" in e]

            if rule.label() not in _WIRE_SPECS:
                continue

            with self.subTest(measure_type=rule.label()):

                if _WIRE_SPECS[rule.label()].lines:
                    # Has a line to overhang the glyphs, so the glyph
                    # series must be trimmed back from both ends.
                    self.assertEqual(len(trimmed), 1)
                else:
                    # No line at all - nothing to overhang, so the
                    # glyphs keep the full geometry.
                    self.assertEqual(trimmed, [])


    def test_the_gap_scale_tunes_spacing_without_rewriting_the_specs(self):

        # The maintainer asked to reduce every gap by 40% after seeing
        # the render. Applied as one factor so _WIRE_SPECS stays a
        # faithful transcription of their description of the manual -
        # test_the_specs_match_the_manual_as_the_maintainer_read_it
        # still asserts the untouched numbers.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_GAP_SCALE,
            _WIRE_GLYPH_SIZE_MM,
            _WIRE_GLYPH_WIDTH_MULTIPLIERS,
            _WIRE_SPECS,
            _WIRE_TILE_OVERLAP_MM,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertAlmostEqual(_WIRE_GAP_SCALE, 0.6)

        layer = create_obstacle_control_measures_lines_layer()

        for rule in layer.renderer().rootRule().children():

            # Abatis has no _WireSpec - it is a single hump, not a
            # repeating glyph.
            if rule.label() not in _WIRE_SPECS:
                continue

            spec = _WIRE_SPECS[rule.label()]

            symbol = rule.symbol()

            marker_lines = []

            for index in range(symbol.symbolLayerCount()):

                sub_symbol = symbol.symbolLayer(index).subSymbol()

                if sub_symbol is None:
                    continue

                for sub_index in range(sub_symbol.symbolLayerCount()):

                    candidate = sub_symbol.symbolLayer(sub_index)

                    if hasattr(candidate, "interval"):
                        marker_lines.append(candidate)

            self.assertEqual(len(marker_lines), 1, rule.label())

            width_multiplier = (
                _WIRE_GLYPH_WIDTH_MULTIPLIERS.get(spec.glyph, 1.0)
            )

            expected = (
                _WIRE_GLYPH_SIZE_MM * width_multiplier
                + spec.gap * _WIRE_GAP_SCALE * _WIRE_GLYPH_SIZE_MM
            )

            if spec.gap == 0:
                # Tiling glyphs overlap a sliver to close the hairline
                # a butt join leaves - see
                # test_the_tiling_obstacles_overlap_to_avoid_hairline_joins.
                expected -= _WIRE_TILE_OVERLAP_MM

            with self.subTest(measure_type=rule.label()):

                self.assertAlmostEqual(
                    marker_lines[0].interval(), expected, places=6
                )


    def test_the_toothed_obstacles_reuse_the_wire_construction(self):

        # Abatis, both antitank ditches and the antitank wall are the
        # same thing as the wire family - a line carrying a repeating
        # glyph - so they are built by the same code rather than by a
        # parallel mechanism that would drift from it.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            TOOTHED_MEASURE_TYPE_CODES,
            TOOTHED_MEASURE_TYPE_LABELS,
            _WIRE_SPECS,
        )

        self.assertEqual(
            set(TOOTHED_MEASURE_TYPE_CODES),
            set(TOOTHED_MEASURE_TYPE_LABELS)
        )

        for measure_type in TOOTHED_MEASURE_TYPE_LABELS:

            self.assertIn(measure_type, LINE_MEASURE_TYPE_CODES)

            # Abatis is the exception: a SINGLE hump just after the
            # first anchor point, then straight line - not a repeating
            # glyph at all, so it has its own builder rather than a
            # _WireSpec. The maintainer's own correction.
            # Abatis (a single kink) and the reinforced ditch (two
            # interleaved glyph series) each need their own builder -
            # neither is one glyph at one interval.
            if measure_type in ("abatis", "antitank_ditch_reinforced"):
                self.assertNotIn(measure_type, _WIRE_SPECS)
            else:
                self.assertIn(measure_type, _WIRE_SPECS)

        self.assertEqual(
            set(TOOTHED_MEASURE_TYPE_CODES.values()),
            {"280100", "290100", "290201", "290202", "290203", "290204"}
        )


    def test_the_two_ditches_differ_only_by_their_fill(self):

        # Under Construction is hollow, Completed is solid - that is
        # the whole difference in the standard's own templates.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _WIRE_SPECS,
        )

        under = _WIRE_SPECS["antitank_ditch_under_construction"]
        completed = _WIRE_SPECS["antitank_ditch_completed"]

        self.assertEqual(under.gap, completed.gap)
        self.assertEqual(under.lines, completed.lines)

        self.assertEqual(under.glyph, "ditch_tooth")
        self.assertEqual(completed.glyph, "ditch_tooth_filled")

        # Both TILE - the triangles' bases are the line, so there is no
        # separate line layer and no gap between them. The maintainer's
        # own correction; the first build drew spaced teeth standing
        # off a drawn line, which is a different symbol entirely.
        self.assertEqual(under.gap, 0.0)
        self.assertEqual(under.lines, ())


class TestMineClusterObstacle(QgisTestCase):

    """
    Mine Cluster (290400) - "user clicks two points, connect it with a
    dashed line, make a semi-circle over it, radius 1/3... of the line
    connecting the two points" - the maintainer's own construction,
    corrected twice the same day: the height fraction (1/3, not the
    standard's own printed 1/2), then the span itself ("the user...
    expects the mine cluster to span that much, not reduce" - so the
    dome now touches both clicked points exactly, as a half-ellipse
    rather than a true semicircle; see mct_mine_cluster_arc's own
    docstring for the full reasoning).
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _arc(self, wkt, height_fraction=None, segments=None):

        from qgis.core import QgsGeometry

        arguments = "geom_from_wkt('{}')".format(
            QgsGeometry.fromWkt(wkt).asWkt()
        )

        if height_fraction is not None:
            arguments += ", {}".format(height_fraction)

        if segments is not None:
            arguments += ", {}".format(segments)

        expression = QgsExpression(f"mct_mine_cluster_arc({arguments})")

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_default_height_is_a_third_of_the_line_not_half(self):

        # The maintainer's own correction: "radius 1/3 and not 1/2 of
        # the line connecting the two points" - now the dome's HEIGHT,
        # not a true semicircle's radius (see class docstring).
        arc = self._arc("LINESTRING(0 0, 300 0)")

        box = arc.boundingBox()

        self.assertAlmostEqual(box.height(), 300 * (1.0 / 3.0), places=6)


    def test_the_arc_touches_both_clicked_points_exactly(self):

        # "the user... expects the mine cluster to span that much, not
        # reduce" - the dome's own horizontal extent must match the
        # full PT1-PT2 line, not a fraction of it.
        arc = self._arc("LINESTRING(0 0, 300 0)")

        vertices = arc.asPolyline()

        # Parametrized starting at the PT2 end (theta == 0) and
        # finishing at the PT1 end (theta == pi).
        self.assertAlmostEqual(vertices[0].x(), 300, places=6)
        self.assertAlmostEqual(vertices[0].y(), 0, places=6)

        self.assertAlmostEqual(vertices[-1].x(), 0, places=6)
        self.assertAlmostEqual(vertices[-1].y(), 0, places=6)

        # The apex, at the arc's own midpoint, is directly above the
        # line's own midpoint at exactly the height fraction.
        apex = vertices[len(vertices) // 2]

        self.assertAlmostEqual(apex.x(), 150, places=2)
        self.assertAlmostEqual(apex.y(), 300 * (1.0 / 3.0), places=2)


    def test_a_custom_height_fraction_is_honoured(self):

        arc = self._arc("LINESTRING(0 0, 100 0)", height_fraction=0.2)

        self.assertAlmostEqual(arc.boundingBox().height(), 20, places=6)

        # The touching-endpoints behaviour is independent of height.
        vertices = arc.asPolyline()

        self.assertAlmostEqual(vertices[0].x(), 100, places=6)
        self.assertAlmostEqual(vertices[-1].x(), 0, places=6)


    def test_diagonal_line_still_bulges_perpendicular_to_it(self):

        # A line at 45 degrees - the arc must bulge perpendicular to
        # the LINE's own direction, not to a map axis.
        arc = self._arc("LINESTRING(0 0, 300 300)")

        length = (300 ** 2 + 300 ** 2) ** 0.5

        height = length * (1.0 / 3.0)

        vertices = arc.asPolyline()

        apex = vertices[len(vertices) // 2]

        midpoint_x, midpoint_y = 150, 150

        # Perpendicular offset from the line's own midpoint, not from
        # the origin.
        offset = ((apex.x() - midpoint_x) ** 2
                  + (apex.y() - midpoint_y) ** 2) ** 0.5

        self.assertAlmostEqual(offset, height, places=4)

        # Still touches the endpoints even off-axis.
        self.assertAlmostEqual(vertices[0].x(), 300, places=4)
        self.assertAlmostEqual(vertices[0].y(), 300, places=4)
        self.assertAlmostEqual(vertices[-1].x(), 0, places=4)
        self.assertAlmostEqual(vertices[-1].y(), 0, places=4)


    def test_mine_cluster_is_offered_on_the_lines_layer(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(LINE_MEASURE_TYPE_CODES["mine_cluster"], "290400")
        self.assertEqual(LINE_MEASURE_TYPE_LABELS["mine_cluster"], "Mine Cluster")

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("mine_cluster", labels)


    def test_mine_cluster_symbol_has_a_plain_line_and_a_generated_arc(self):

        # The straight portion is the feature's own RAW geometry now -
        # no trimming - so it needs no generator; only the arc does.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _mine_cluster_symbol,
        )

        from qgis.core import (
            QgsGeometryGeneratorSymbolLayer, QgsSimpleLineSymbolLayer
        )

        symbol = _mine_cluster_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 2)

        self.assertIsInstance(
            symbol.symbolLayer(0), QgsSimpleLineSymbolLayer
        )
        self.assertIsInstance(
            symbol.symbolLayer(1), QgsGeometryGeneratorSymbolLayer
        )

        self.assertIn(
            "mct_mine_cluster_arc($geometry,",
            symbol.symbolLayer(1).geometryExpression()
        )


    def test_the_straight_line_is_drawn_at_its_full_clicked_length(self):

        # No line_substring trimming any more (regression guard for the
        # rejected "trim the line" fix) - the straight layer is a plain
        # QgsSimpleLineSymbolLayer with no geometry expression at all,
        # so it necessarily draws the feature's own digitized geometry
        # as-is, full length.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _mine_cluster_symbol,
        )

        symbol = _mine_cluster_symbol()

        self.assertFalse(
            hasattr(symbol.symbolLayer(0), "geometryExpression")
        )


    def test_the_line_and_arc_share_the_same_endpoints(self):

        # The claim the above only implies: evaluate the arc against a
        # real feature and check its own endpoints coincide with the
        # feature's raw PT1/PT2, not a shrunk or extended version.
        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_lines_layer,
        )

        layer = create_obstacle_control_measures_lines_layer()

        feature = QgsFeature(layer.fields())

        feature.setGeometry(
            QgsGeometry.fromPolylineXY(
                [QgsPointXY(0, 0), QgsPointXY(300, 0)]
            )
        )

        feature.setAttribute("measure_type", "mine_cluster")
        feature.setAttribute("colour", "green")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        arc = QgsExpression(
            "mct_mine_cluster_arc($geometry, {})".format(1.0 / 3.0)
        ).evaluate(context)

        arc_vertices = arc.asPolyline()

        arc_ends = {
            round(arc_vertices[0].x(), 6), round(arc_vertices[-1].x(), 6)
        }

        self.assertEqual(arc_ends, {0.0, 300.0})


    def test_both_layers_of_the_symbol_are_dashed_regardless_of_status(self):

        # Fixed iconography, not the H.5.1.1.3 present/planned rule -
        # the same "always dashed" treatment as Maritime's own Bearing
        # Line, Acoustic (Ambiguous) and the Decoy chevrons. A CUSTOM
        # dash pattern, not the bare Qt default, since the maintainer
        # asked for the dashes 40% longer and the gaps 50% wider.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _MINE_CLUSTER_DASH_MM,
            _MINE_CLUSTER_GAP_MM,
            _mine_cluster_symbol,
        )

        symbol = _mine_cluster_symbol()

        straight = symbol.symbolLayer(0)

        arc_inner = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        for label, inner in (("straight", straight), ("arc", arc_inner)):

            with self.subTest(symbol_layer=label):

                self.assertTrue(inner.useCustomDashPattern())

                self.assertEqual(
                    list(inner.customDashVector()),
                    [_MINE_CLUSTER_DASH_MM, _MINE_CLUSTER_GAP_MM]
                )

                self.assertFalse(
                    inner.dataDefinedProperties().isActive(
                        QgsSymbolLayer.Property.StrokeStyle
                    )
                )


    def test_the_dash_pattern_is_qts_own_default_scaled_by_the_maintainers_ask(self):

        # Traceability: +40% dash, +50% gap, off Qt's OWN DashLine
        # default ([4, 2] pen widths) - not off some other round number
        # this project invented.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _AREA_OUTLINE_WIDTH_MM,
            _MINE_CLUSTER_DASH_MM,
            _MINE_CLUSTER_GAP_MM,
        )

        self.assertAlmostEqual(
            _MINE_CLUSTER_DASH_MM, _AREA_OUTLINE_WIDTH_MM * 4.0 * 1.4,
            places=9
        )
        self.assertAlmostEqual(
            _MINE_CLUSTER_GAP_MM, _AREA_OUTLINE_WIDTH_MM * 2.0 * 1.5,
            places=9
        )


    def test_mine_cluster_arc_evaluates_against_a_real_feature(self):

        # A minimal end-to-end check: build the real Lines layer, give
        # it a genuine two-point feature and confirm the generator's
        # own expression - exactly what the geometry generator symbol
        # layer evaluates on every repaint - produces a real, non-empty
        # arc rather than erroring or returning nothing.
        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_lines_layer,
        )

        layer = create_obstacle_control_measures_lines_layer()

        feature = QgsFeature(layer.fields())

        feature.setGeometry(
            QgsGeometry.fromPolylineXY(
                [QgsPointXY(0, 0), QgsPointXY(300, 0)]
            )
        )

        feature.setAttribute("measure_type", "mine_cluster")
        feature.setAttribute("colour", "green")

        expression = QgsExpression(
            "mct_mine_cluster_arc($geometry, {})".format(1.0 / 3.0)
        )

        context = layer.createExpressionContext()
        context.setFeature(feature)

        arc = expression.evaluate(context)

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )
        self.assertFalse(arc.isEmpty())

        self.assertAlmostEqual(
            arc.boundingBox().height(), 300 * (1.0 / 3.0), places=6
        )


class TestTripWireObstacle(QgisTestCase):

    """
    Trip Wire (290500) - rebuilt 2026-08-13 from the maintainer's own
    dictated construction (their exact words are quoted in
    mct_trip_wire_geometry's own docstring), replacing an earlier
    3-anchor-point reading of the standard's own template picture.
    Two anchor points now: PT1, PT2.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _parts(self, pt1, pt2, segments=None):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2)]
        ).asWkt()

        arguments = "geom_from_wkt('{}')".format(wkt)

        if segments is not None:
            arguments += ", {}".format(segments)

        expression = QgsExpression(f"mct_trip_wire_geometry({arguments})")

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        return result.asMultiPolyline()


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        one_point = QgsGeometry.fromPolylineXY([QgsPointXY(0, 0)])

        expression = QgsExpression(
            "mct_trip_wire_geometry(geom_from_wkt('{}'))".format(
                one_point.asWkt()
            )
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), one_point.asWkt())


    def test_returns_three_parts_main_line_and_two_crossbars(self):

        parts = self._parts((0, 0), (10, 0))

        self.assertEqual(len(parts), 3)


    def test_main_line_starts_at_pt1_and_the_arc_ends_the_path(self):

        parts = self._parts((0, 0), (10, 0))

        main_line_and_arc = parts[0]

        self.assertAlmostEqual(main_line_and_arc[0].x(), 0)
        self.assertAlmostEqual(main_line_and_arc[0].y(), 0)

        # PT2 itself is the arc's own start point, so it must appear on
        # the path exactly where the straight run ends.
        self.assertAlmostEqual(main_line_and_arc[1].x(), 10)
        self.assertAlmostEqual(main_line_and_arc[1].y(), 0)


    def test_arc_ends_a_quarter_turn_anticlockwise_at_one_fifth_radius(self):

        # The maintainer's own numbers: radius = PT1-PT2 distance / 5,
        # 90 degrees anticlockwise, starting tangent to the main line's
        # own direction of travel. Verified against the module's own
        # hand-derived worked example (PT1=(0,0), PT2=(10,0) ->
        # centre=(10,2), end=(12,2)), not just "some plausible curve".
        parts = self._parts((0, 0), (10, 0))

        main_line_and_arc = parts[0]

        end = main_line_and_arc[-1]

        self.assertAlmostEqual(end.x(), 12, places=6)
        self.assertAlmostEqual(end.y(), 2, places=6)


    def test_crossbar_near_pt1_sits_at_one_seventh_symmetric_half_length(self):

        # "both the horizontal lines are on one side of the line
        # connecting pt1 and 2, they should be on both sides" - each
        # crossbar now runs the dictated length to EACH side of the
        # main line, not just one.
        parts = self._parts((0, 0), (14, 0))

        crossbar = parts[1]

        # 1/7 of 14 = 2, the base point on the main line.
        self.assertAlmostEqual((crossbar[0].x() + crossbar[1].x()) / 2, 2)
        self.assertAlmostEqual((crossbar[0].y() + crossbar[1].y()) / 2, 0)

        # Perpendicular, length 0.5 * 14 = 7 to EACH side.
        ys = sorted(point.y() for point in crossbar)

        self.assertAlmostEqual(ys[0], -7, places=6)
        self.assertAlmostEqual(ys[1], 7, places=6)

        for point in crossbar:
            self.assertAlmostEqual(point.x(), 2, places=6)


    def test_crossbar_at_midpoint_has_one_point_two_times_length_each_side(self):

        parts = self._parts((0, 0), (10, 0))

        crossbar = parts[2]

        self.assertAlmostEqual((crossbar[0].x() + crossbar[1].x()) / 2, 5)
        self.assertAlmostEqual((crossbar[0].y() + crossbar[1].y()) / 2, 0)

        # Perpendicular, length 1.2 * 10 = 12 to EACH side.
        ys = sorted(point.y() for point in crossbar)

        self.assertAlmostEqual(ys[0], -12, places=6)
        self.assertAlmostEqual(ys[1], 12, places=6)


    def test_only_the_arc_is_one_sided_not_the_crossbars(self):

        # The maintainer's own correction named "both the horizontal
        # lines" specifically - the arc was left as-is, still on one
        # side (the main line's own left, standard CCW sense).
        parts = self._parts((0, 0), (10, 0))

        main_line_and_arc, crossbar_1, crossbar_2 = parts

        self.assertTrue(all(point.y() >= 0 for point in main_line_and_arc))

        for crossbar in (crossbar_1, crossbar_2):

            ys = [point.y() for point in crossbar]

            self.assertLess(min(ys), 0)
            self.assertGreater(max(ys), 0)


    def test_construction_rotates_with_the_main_lines_own_direction(self):

        # Not hard-coded to a horizontal PT1-PT2 - a vertical line's
        # crossbars/arc must rotate right along with it.
        parts = self._parts((0, 0), (0, 10))

        main_line_and_arc, crossbar_1, crossbar_2 = parts

        end = main_line_and_arc[-1]

        # Centre = PT2 + r*n where n = u rotated 90 CCW; u=(0,1) here,
        # n=(-1,0). radius=2. end = PT2 + r*(n+u) = (0,10)+2*(-1,1)
        # = (-2,12).
        self.assertAlmostEqual(end.x(), -2, places=6)
        self.assertAlmostEqual(end.y(), 12, places=6)

        # Crossbar at the midpoint should now run along +/-x, not +/-y.
        xs = sorted(point.x() for point in crossbar_2)

        self.assertAlmostEqual(xs[0], -12, places=6)
        self.assertAlmostEqual(xs[1], 12, places=6)

        for point in crossbar_2:
            self.assertAlmostEqual(point.y(), 5, places=6)


    def test_trip_wire_is_offered_on_the_lines_layer(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(LINE_MEASURE_TYPE_CODES["trip_wire"], "290500")
        self.assertEqual(LINE_MEASURE_TYPE_LABELS["trip_wire"], "Trip Wire")

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("trip_wire", labels)


    def test_trip_wire_symbol_is_one_generated_geometry_layer(self):

        from qgis.core import QgsGeometryGeneratorSymbolLayer

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _trip_wire_symbol,
        )

        symbol = _trip_wire_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 1)

        self.assertIsInstance(
            symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer
        )

        self.assertIn(
            "mct_trip_wire_geometry($geometry)",
            symbol.symbolLayer(0).geometryExpression()
        )


    def test_trip_wire_follows_status_unlike_mine_cluster(self):

        # No "always dashed" note on Trip Wire's own draw rules -
        # ordinary present/planned styling, the same as the rest of
        # the wire family and unlike Mine Cluster's fixed dash.
        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _trip_wire_symbol,
        )

        symbol = _trip_wire_symbol()

        inner_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            inner_line.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


    def test_trip_wire_geometry_evaluates_against_a_real_feature(self):

        from qgis.core import QgsFeature, QgsGeometry, QgsPointXY

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            create_obstacle_control_measures_lines_layer,
        )

        layer = create_obstacle_control_measures_lines_layer()

        feature = QgsFeature(layer.fields())

        feature.setGeometry(
            QgsGeometry.fromPolylineXY(
                [QgsPointXY(0, 0), QgsPointXY(10, 0)]
            )
        )

        feature.setAttribute("measure_type", "trip_wire")
        feature.setAttribute("colour", "green")
        feature.setAttribute("status", "present")

        expression = QgsExpression("mct_trip_wire_geometry($geometry)")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        path = expression.evaluate(context)

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )
        self.assertFalse(path.isEmpty())
        self.assertEqual(len(path.asMultiPolyline()), 3)


class TestBlockObstacleEffect(QgisTestCase):

    """
    Block (270501) - the standard's own draw rules are fully specified
    here (page 575): PT1-PT2 crossbar, PT3 sets the stem's own length
    via its perpendicular distance to the PT1-PT2 line.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _parts(self, pt1, pt2, pt3):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2), QgsPointXY(*pt3)]
        ).asWkt()

        expression = QgsExpression(
            "mct_block_geometry(geom_from_wkt('{}'))".format(wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        return result.asMultiPolyline()


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        two_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(0, 10)]
        )

        expression = QgsExpression(
            "mct_block_geometry(geom_from_wkt('{}'))".format(
                two_point.asWkt()
            )
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), two_point.asWkt())


    def test_crossbar_is_pt1_to_pt2_unmodified(self):

        crossbar, _stem = self._parts((0, 10), (0, -10), (15, 0))

        self.assertAlmostEqual(crossbar[0].x(), 0)
        self.assertAlmostEqual(crossbar[0].y(), 10)
        self.assertAlmostEqual(crossbar[1].x(), 0)
        self.assertAlmostEqual(crossbar[1].y(), -10)


    def test_stem_runs_from_the_crossbars_own_midpoint(self):

        _crossbar, stem = self._parts((0, 10), (0, -10), (15, 0))

        self.assertAlmostEqual(stem[0].x(), 0)
        self.assertAlmostEqual(stem[0].y(), 0)


    def test_stem_length_is_pt3s_perpendicular_distance(self):

        # PT3 clicked exactly perpendicular here, so its own distance
        # to the line IS its own x offset.
        _crossbar, stem = self._parts((0, 10), (0, -10), (15, 0))

        self.assertAlmostEqual(stem[1].x(), 15, places=6)
        self.assertAlmostEqual(stem[1].y(), 0, places=6)


    def test_off_axis_pt3_still_uses_perpendicular_distance(self):

        # PT3 well above the crossbar's own top - the stem's length
        # must still be the PERPENDICULAR distance to the infinite
        # PT1-PT2 line, not the raw distance to PT3 itself.
        _crossbar, stem = self._parts((0, 10), (0, -10), (15, 25))

        self.assertAlmostEqual(stem[1].x(), 15, places=6)
        self.assertAlmostEqual(stem[1].y(), 0, places=6)


    def test_pt3_on_the_line_collapses_the_stem_rather_than_guessing(self):

        crossbar, stem = self._parts((0, 10), (0, -10), (0, 3))

        self.assertEqual(len(stem), 1)
        self.assertAlmostEqual(stem[0].x(), 0)
        self.assertAlmostEqual(stem[0].y(), 0)


    def test_block_is_offered_on_the_lines_layer(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(LINE_MEASURE_TYPE_CODES["block"], "270501")
        self.assertEqual(LINE_MEASURE_TYPE_LABELS["block"], "Block")

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("block", labels)


    def test_block_symbol_follows_present_planned_status(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _block_symbol,
        )

        symbol = _block_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 1)

        inner_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            inner_line.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


class TestTurnObstacleEffect(QgisTestCase):

    """
    Turn (270504) - rebuilt 2026-08-13 to the maintainer's own dictated
    construction (their exact words are quoted in mct_turn_arc's own
    docstring), replacing a first reading of the standard's own
    draw-rules text (a true 90 degree circular arc between only
    PT1/PT2, PT3 as a side-selector) after two reported problems:
    "rendering in the opposite direction of the points, and the line
    is getting trimmed instead of being from PT1 to PT3". Now: a
    quadratic Bezier curve, PT1 start, PT2 control point, PT3 end.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _curve(self, pt1, pt2, pt3, segments=None):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2), QgsPointXY(*pt3)]
        ).asWkt()

        arguments = "geom_from_wkt('{}')".format(wkt)

        if segments is not None:
            arguments += ", {}".format(segments)

        expression = QgsExpression(f"mct_turn_arc({arguments})")

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        two_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(10, 0)]
        )

        expression = QgsExpression(
            "mct_turn_arc(geom_from_wkt('{}'))".format(two_point.asWkt())
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), two_point.asWkt())


    def test_curve_starts_at_pt1_and_ends_at_pt3(self):

        curve = self._curve((0, 0), (5, 10), (10, 0))

        vertices = curve.asPolyline()

        self.assertAlmostEqual(vertices[0].x(), 0, places=6)
        self.assertAlmostEqual(vertices[0].y(), 0, places=6)
        self.assertAlmostEqual(vertices[-1].x(), 10, places=6)
        self.assertAlmostEqual(vertices[-1].y(), 0, places=6)


    def test_curve_bulges_toward_the_control_point_pt2(self):

        # A quadratic Bezier's own midpoint (t=0.5) sits at the average
        # of the two chord endpoints and the control point, weighted
        # 1:1:2 - (PT1 + 2*PT2 + PT3) / 4 - not exactly AT PT2, but
        # pulled toward it, away from the straight PT1-PT3 chord.
        curve = self._curve((0, 0), (5, 10), (10, 0))

        vertices = curve.asPolyline()

        midpoint = vertices[len(vertices) // 2]

        expected_x = (0 + 2 * 5 + 10) / 4.0
        expected_y = (0 + 2 * 10 + 0) / 4.0

        self.assertAlmostEqual(midpoint.x(), expected_x, places=3)
        self.assertAlmostEqual(midpoint.y(), expected_y, places=3)


    def test_control_point_off_to_one_side_curves_that_way(self):

        # Not hard-coded to a symmetric control point - the curve must
        # follow wherever PT2 actually is.
        curve = self._curve((0, 0), (2, 8), (10, 0))

        vertices = curve.asPolyline()

        # Every interior point should lean toward the PT2 side (x < 5,
        # the straight chord's own midpoint) more than a symmetric
        # curve would, since the control point itself sits at x=2.
        midpoint = vertices[len(vertices) // 2]

        self.assertLess(midpoint.x(), 5)


    def test_turn_is_offered_on_the_lines_layer(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(LINE_MEASURE_TYPE_CODES["turn"], "270504")
        self.assertEqual(LINE_MEASURE_TYPE_LABELS["turn"], "Turn")

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("turn", labels)


    def test_turn_symbol_has_a_generated_curve_and_an_arrowhead_marker(self):

        from qgis.core import (
            Qgis, QgsGeometryGeneratorSymbolLayer, QgsMarkerLineSymbolLayer
        )

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _turn_symbol,
        )

        symbol = _turn_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 2)

        for index in (0, 1):

            with self.subTest(symbol_layer=index):

                self.assertIsInstance(
                    symbol.symbolLayer(index), QgsGeometryGeneratorSymbolLayer
                )
                self.assertIn(
                    "mct_turn_arc($geometry)",
                    symbol.symbolLayer(index).geometryExpression()
                )

        # The arrowhead's own marker line lives INSIDE the second
        # generator's subSymbol, not as a sibling layer - it must
        # follow the curve's own last point (PT3), not the feature's
        # raw geometry (see _turn_symbol's own comment on why).
        chevron_marker_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertIsInstance(chevron_marker_line, QgsMarkerLineSymbolLayer)

        self.assertEqual(
            chevron_marker_line.placements(),
            Qgis.MarkerLinePlacement.LastVertex
        )


    def test_turn_symbol_follows_present_planned_status(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _turn_symbol,
        )

        symbol = _turn_symbol()

        inner_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            inner_line.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


class TestDisruptObstacleEffect(QgisTestCase):

    """
    Disrupt (270502) - the maintainer's own dictated construction
    (quoted in full in mct_disrupt_geometry's own docstring), replacing
    a first reading of the standard's own template (pixel-measured
    only, never trusted as an exact ratio).
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _parts(self, pt1, pt2, pt3, arrows_only=False):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2), QgsPointXY(*pt3)]
        ).asWkt()

        function = (
            "mct_disrupt_arrow_tips" if arrows_only else "mct_disrupt_geometry"
        )

        expression = QgsExpression(
            f"{function}(geom_from_wkt('{wkt}'))"
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        return result.asMultiPolyline()


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        two_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 20), QgsPointXY(0, -20)]
        )

        expression = QgsExpression(
            "mct_disrupt_geometry(geom_from_wkt('{}'))".format(
                two_point.asWkt()
            )
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), two_point.asWkt())


    def test_returns_base_plus_three_arrows(self):

        parts = self._parts((0, 20), (0, -20), (30, 0))

        self.assertEqual(len(parts), 4)


    def test_base_is_pt1_to_pt2_unmodified(self):

        base, _a, _b, _c = self._parts((0, 20), (0, -20), (30, 0))

        self.assertAlmostEqual(base[0].x(), 0)
        self.assertAlmostEqual(base[0].y(), 20)
        self.assertAlmostEqual(base[1].x(), 0)
        self.assertAlmostEqual(base[1].y(), -20)


    def test_arrow_from_pt2_runs_the_full_perpendicular_distance(self):

        _base, arrow_a, _b, _c = self._parts((0, 20), (0, -20), (30, 0))

        self.assertAlmostEqual(arrow_a[0].x(), 0)
        self.assertAlmostEqual(arrow_a[0].y(), -20)
        self.assertAlmostEqual(arrow_a[1].x(), 30, places=6)
        self.assertAlmostEqual(arrow_a[1].y(), -20, places=6)


    def test_arrow_from_pt1_is_half_the_length(self):

        _base, _a, arrow_b, _c = self._parts((0, 20), (0, -20), (30, 0))

        self.assertAlmostEqual(arrow_b[0].x(), 0)
        self.assertAlmostEqual(arrow_b[0].y(), 20)
        self.assertAlmostEqual(arrow_b[1].x(), 15, places=6)
        self.assertAlmostEqual(arrow_b[1].y(), 20, places=6)


    def test_middle_arrow_tip_is_the_average_of_the_other_two(self):

        # "halfway as compared to the tips of the other two arrows" -
        # average of 30 (full) and 15 (half) is 22.5.
        _base, _a, _b, arrow_c = self._parts((0, 20), (0, -20), (30, 0))

        self.assertAlmostEqual(arrow_c[1].x(), 22.5, places=6)
        self.assertAlmostEqual(arrow_c[1].y(), 0, places=6)


    def test_middle_arrow_extends_symmetrically_past_the_base(self):

        # "extend the shaft below the base, length same as base to the
        # tip of the arrow" - the tail is the SAME distance on the
        # opposite side.
        _base, _a, _b, arrow_c = self._parts((0, 20), (0, -20), (30, 0))

        self.assertAlmostEqual(arrow_c[0].x(), -22.5, places=6)
        self.assertAlmostEqual(arrow_c[0].y(), 0, places=6)


    def test_arrow_tips_function_excludes_the_base(self):

        arrows = self._parts((0, 20), (0, -20), (30, 0), arrows_only=True)

        self.assertEqual(len(arrows), 3)

        # None of the three arrows should equal the base's own
        # endpoints exactly as a PAIR (the base itself must not be
        # among them).
        base_pair = [(0.0, 20.0), (0.0, -20.0)]

        for arrow in arrows:

            pair = [(round(p.x(), 6), round(p.y(), 6)) for p in arrow]

            self.assertNotEqual(pair, base_pair)


    def test_pt3_on_the_base_line_collapses_rather_than_guessing(self):

        base, arrow_a, arrow_b, arrow_c = self._parts(
            (0, 20), (0, -20), (0, 5)
        )

        # Degenerate: every arrow collapses to a single point rather
        # than picking an arbitrary side.
        self.assertEqual(arrow_a[0], arrow_a[1])
        self.assertEqual(arrow_b[0], arrow_b[1])
        self.assertEqual(arrow_c[0], arrow_c[1])


    def test_disrupt_is_offered_on_the_lines_layer(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(LINE_MEASURE_TYPE_CODES["disrupt"], "270502")
        self.assertEqual(LINE_MEASURE_TYPE_LABELS["disrupt"], "Disrupt")

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("disrupt", labels)


    def test_disrupt_symbol_has_two_generators_and_an_arrowhead_marker(self):

        from qgis.core import (
            Qgis, QgsGeometryGeneratorSymbolLayer, QgsMarkerLineSymbolLayer
        )

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _disrupt_symbol,
        )

        symbol = _disrupt_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 2)

        self.assertIsInstance(
            symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer
        )
        self.assertIn(
            "mct_disrupt_geometry($geometry)",
            symbol.symbolLayer(0).geometryExpression()
        )

        self.assertIsInstance(
            symbol.symbolLayer(1), QgsGeometryGeneratorSymbolLayer
        )
        self.assertIn(
            "mct_disrupt_arrow_tips($geometry)",
            symbol.symbolLayer(1).geometryExpression()
        )

        chevron_marker_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertIsInstance(chevron_marker_line, QgsMarkerLineSymbolLayer)

        self.assertEqual(
            chevron_marker_line.placements(),
            Qgis.MarkerLinePlacement.LastVertex
        )


    def test_disrupt_symbol_follows_present_planned_status(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _disrupt_symbol,
        )

        symbol = _disrupt_symbol()

        inner_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            inner_line.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


class TestFixObstacleEffect(QgisTestCase):

    """
    Fix (270503) - the maintainer's own dictated construction, at their
    own explicit instruction different from the standard's own
    template ("I know it is slightly different from what manual
    suggests, go with it").
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _path(self, pt1, pt2, pt3):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2), QgsPointXY(*pt3)]
        ).asWkt()

        expression = QgsExpression(
            "mct_fix_geometry(geom_from_wkt('{}'))".format(wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        two_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(100, 0)]
        )

        expression = QgsExpression(
            "mct_fix_geometry(geom_from_wkt('{}'))".format(two_point.asWkt())
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), two_point.asWkt())


    def test_path_starts_at_pt1_and_ends_at_pt2(self):

        path = self._path((0, 0), (100, 0), (50, 10))

        vertices = path.asPolyline()

        self.assertAlmostEqual(vertices[0].x(), 0)
        self.assertAlmostEqual(vertices[0].y(), 0)
        self.assertAlmostEqual(vertices[-1].x(), 100)
        self.assertAlmostEqual(vertices[-1].y(), 0)


    def test_exact_multiple_of_tooth_length_matches_the_worked_example(self):

        # Hand-derived: L=10 (perpendicular distance from PT3 to the
        # PT1-PT2 line), total=100, usable=80, 8 complete teeth, no
        # leftover - flat runs of exactly L at each end.
        path = self._path((0, 0), (100, 0), (50, 10))

        vertices = path.asPolyline()

        self.assertAlmostEqual(vertices[1].x(), 10, places=6)
        self.assertAlmostEqual(vertices[1].y(), 0, places=6)

        self.assertAlmostEqual(vertices[-2].x(), 90, places=6)
        self.assertAlmostEqual(vertices[-2].y(), 0, places=6)

        # First tooth apex: half a tooth further, at full height.
        expected_height = 10 * math.sqrt(3.0) / 2.0

        self.assertAlmostEqual(vertices[2].x(), 15, places=6)
        self.assertAlmostEqual(vertices[2].y(), expected_height, places=6)


    def test_teeth_alternate_above_and_below_the_base_line(self):

        path = self._path((0, 0), (100, 0), (50, 10))

        vertices = path.asPolyline()

        # Every apex (odd-positioned interior vertex) alternates sign.
        apexes = [v.y() for v in vertices if abs(v.y()) > 1e-6]

        self.assertGreater(len(apexes), 2)

        for first, second in zip(apexes, apexes[1:]):

            self.assertLess(first * second, 0)


    def test_a_shorter_line_still_returns_something_sensible(self):

        # total_length < 2*L: no room for any complete teeth, but the
        # function must still return PT1-PT2 rather than erroring.
        path = self._path((0, 0), (5, 0), (2.5, 10))

        self.assertFalse(path.isEmpty())

        vertices = path.asPolyline()

        self.assertAlmostEqual(vertices[0].x(), 0)
        self.assertAlmostEqual(vertices[-1].x(), 5, places=6)


    def test_pt3_on_the_line_falls_back_to_a_plain_segment(self):

        path = self._path((0, 0), (100, 0), (50, 0))

        self.assertEqual(path.asWkt(), "LineString (0 0, 100 0)")


    def test_fix_is_offered_on_the_lines_layer(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            LINE_MEASURE_TYPE_LABELS,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(LINE_MEASURE_TYPE_CODES["fix"], "270503")
        self.assertEqual(LINE_MEASURE_TYPE_LABELS["fix"], "Fix")

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("fix", labels)


    def test_fix_symbol_has_a_generated_path_and_a_filled_arrowhead(self):

        # "end the line segment at PT2 with an arrowhead... filled
        # arrowhead" - the maintainer's own correction to the earlier
        # no-arrowhead reading.
        from qgis.core import (
            Qgis, QgsGeometryGeneratorSymbolLayer, QgsMarkerLineSymbolLayer,
            QgsSimpleMarkerSymbolLayerBase,
        )

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _fix_symbol,
        )

        symbol = _fix_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 2)

        for index in (0, 1):

            with self.subTest(symbol_layer=index):

                self.assertIsInstance(
                    symbol.symbolLayer(index), QgsGeometryGeneratorSymbolLayer
                )
                self.assertIn(
                    "mct_fix_geometry($geometry)",
                    symbol.symbolLayer(index).geometryExpression()
                )

        arrow_marker_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertIsInstance(arrow_marker_line, QgsMarkerLineSymbolLayer)

        self.assertEqual(
            arrow_marker_line.placements(),
            Qgis.MarkerLinePlacement.LastVertex
        )

        arrow_marker_shape = arrow_marker_line.subSymbol().symbolLayer(0)

        self.assertEqual(
            arrow_marker_shape.shape(),
            QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHeadFilled
        )


    def test_fix_symbol_follows_present_planned_status(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _fix_symbol,
        )

        symbol = _fix_symbol()

        inner_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            inner_line.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


class TestObstacleBypassFamily(QgisTestCase):

    """
    Obstacle Bypass Easy/Difficult/Impossible (270601-270603) - the
    standard's own draw rules are fully numeric (page 578-579): PT1/PT2
    are the two arrow tips, PT3's own perpendicular distance from the
    PT1-PT2 line sets the rear line's offset and the arrows' own
    length. Always BLACK, per the module's own audit.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _evaluate(self, function_name, pt1, pt2, pt3):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2), QgsPointXY(*pt3)]
        ).asWkt()

        expression = QgsExpression(
            "{}(geom_from_wkt('{}'))".format(function_name, wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    # PT1=(0,10), PT2=(0,-10), PT3=(15,0): PT3 sits exactly
    # perpendicular to the PT1-PT2 line, 15 units out along +x, so
    # every "depth" below is exactly 15 and every "height" is exactly
    # 20 - the same clean fixture Block's own tests use.
    PT1, PT2, PT3 = (0, 10), (0, -10), (15, 0)


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        two_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(0, 10)]
        )

        expression = QgsExpression(
            "mct_obstacle_bypass_arrows(geom_from_wkt('{}'))".format(
                two_point.asWkt()
            )
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), two_point.asWkt())


    def test_arrows_run_from_the_offset_rear_out_to_pt1_and_pt2(self):

        result = self._evaluate(
            "mct_obstacle_bypass_arrows", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        arrow_top, arrow_bottom = result.asMultiPolyline()

        self.assertAlmostEqual(arrow_top[0].x(), 15)
        self.assertAlmostEqual(arrow_top[0].y(), 10)
        self.assertAlmostEqual(arrow_top[1].x(), 0)
        self.assertAlmostEqual(arrow_top[1].y(), 10)

        self.assertAlmostEqual(arrow_bottom[0].x(), 15)
        self.assertAlmostEqual(arrow_bottom[0].y(), -10)
        self.assertAlmostEqual(arrow_bottom[1].x(), 0)
        self.assertAlmostEqual(arrow_bottom[1].y(), -10)


    def test_rear_easy_is_the_plain_offset_line(self):

        result = self._evaluate(
            "mct_obstacle_bypass_rear_easy", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "LineString")

        points = result.asPolyline()

        self.assertAlmostEqual(points[0].x(), 15)
        self.assertAlmostEqual(points[0].y(), 10)
        self.assertAlmostEqual(points[1].x(), 15)
        self.assertAlmostEqual(points[1].y(), -10)


    def test_rear_difficult_zigzags_between_the_offset_ends(self):

        result = self._evaluate(
            "mct_obstacle_bypass_rear_difficult", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "LineString")

        points = result.asPolyline()

        # 7 vertices (6 segments): starts/ends on the plain rear axis
        # (x=15), bulges to x=21 (depth 15 * amplitude ratio 0.4 = 6,
        # so x = 15 + 6) at the odd interior vertices.
        self.assertEqual(len(points), 7)

        self.assertAlmostEqual(points[0].x(), 15)
        self.assertAlmostEqual(points[0].y(), 10)

        self.assertAlmostEqual(points[1].x(), 21)
        self.assertAlmostEqual(points[1].y(), 20.0 / 3.0)

        self.assertAlmostEqual(points[3].x(), 21)
        self.assertAlmostEqual(points[3].y(), 0)

        self.assertAlmostEqual(points[6].x(), 15)
        self.assertAlmostEqual(points[6].y(), -10)


    def test_rear_impossible_is_two_independent_hooks(self):

        result = self._evaluate(
            "mct_obstacle_bypass_rear_impossible", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        top_hook, bottom_hook = result.asMultiPolyline()

        # Not connected to each other - the standard's own template
        # shows the opening fully closed off at each end, not spanned.
        self.assertEqual(len(top_hook), 3)
        self.assertEqual(len(bottom_hook), 3)

        # Top hook: rear_top (15,10) -> stub toward PT2 (height 20 *
        # 0.25 = 5) -> tick toward PT3 (depth 15 * 0.35 = 5.25).
        self.assertAlmostEqual(top_hook[0].x(), 15)
        self.assertAlmostEqual(top_hook[0].y(), 10)
        self.assertAlmostEqual(top_hook[1].x(), 15)
        self.assertAlmostEqual(top_hook[1].y(), 5)
        self.assertAlmostEqual(top_hook[2].x(), 20.25)
        self.assertAlmostEqual(top_hook[2].y(), 5)

        # Bottom hook mirrors it toward PT1's side.
        self.assertAlmostEqual(bottom_hook[0].x(), 15)
        self.assertAlmostEqual(bottom_hook[0].y(), -10)
        self.assertAlmostEqual(bottom_hook[1].x(), 15)
        self.assertAlmostEqual(bottom_hook[1].y(), -5)
        self.assertAlmostEqual(bottom_hook[2].x(), 20.25)
        self.assertAlmostEqual(bottom_hook[2].y(), -5)


    def test_all_three_variants_are_offered_and_black(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            TABLE_H_XIX_INVENTORY,
            create_obstacle_control_measures_lines_layer,
        )

        expected_codes = {
            "obstacle_bypass_easy": "270601",
            "obstacle_bypass_difficult": "270602",
            "obstacle_bypass_impossible": "270603",
        }

        for measure_type, code in expected_codes.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(LINE_MEASURE_TYPE_CODES[measure_type], code)
                self.assertEqual(
                    TABLE_H_XIX_INVENTORY[code]["colour"], BLACK
                )

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        for measure_type in expected_codes:
            self.assertIn(measure_type, labels)


    def test_each_variant_symbol_has_a_rear_layer_arrows_and_arrowhead(self):

        from qgis.core import (
            Qgis, QgsGeometryGeneratorSymbolLayer, QgsMarkerLineSymbolLayer,
        )

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _obstacle_bypass_difficult_symbol,
            _obstacle_bypass_easy_symbol,
            _obstacle_bypass_impossible_symbol,
        )

        builders = {
            "easy": (
                _obstacle_bypass_easy_symbol,
                "mct_obstacle_bypass_rear_easy($geometry)",
            ),
            "difficult": (
                _obstacle_bypass_difficult_symbol,
                "mct_obstacle_bypass_rear_difficult($geometry)",
            ),
            "impossible": (
                _obstacle_bypass_impossible_symbol,
                "mct_obstacle_bypass_rear_impossible($geometry)",
            ),
        }

        for variant, (builder, rear_expression) in builders.items():

            with self.subTest(variant=variant):

                symbol = builder()

                self.assertEqual(symbol.symbolLayerCount(), 3)

                self.assertIsInstance(
                    symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer
                )
                self.assertIn(
                    rear_expression,
                    symbol.symbolLayer(0).geometryExpression()
                )

                self.assertIsInstance(
                    symbol.symbolLayer(1), QgsGeometryGeneratorSymbolLayer
                )
                self.assertIn(
                    "mct_obstacle_bypass_arrows($geometry)",
                    symbol.symbolLayer(1).geometryExpression()
                )

                chevron_marker_line = (
                    symbol.symbolLayer(2).subSymbol().symbolLayer(0)
                )

                self.assertIsInstance(
                    chevron_marker_line, QgsMarkerLineSymbolLayer
                )
                self.assertEqual(
                    chevron_marker_line.placements(),
                    Qgis.MarkerLinePlacement.LastVertex
                )


class TestBridgeOrGap(QgisTestCase):

    """
    Bridge or Gap (271100) - the one line obstacle in this batch
    needing four anchor points: "points 1 and 2 define one side of the
    gap and points 3 and 4 define the opposite side."
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_too_few_vertices_returns_the_geometry_unchanged(self):

        from qgis.core import QgsGeometry, QgsPointXY

        three_point = QgsGeometry.fromPolylineXY(
            [QgsPointXY(0, 0), QgsPointXY(0, 10), QgsPointXY(5, 10)]
        )

        expression = QgsExpression(
            "mct_bridge_or_gap_geometry(geom_from_wkt('{}'))".format(
                three_point.asWkt()
            )
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.asWkt(), three_point.asWkt())


    def test_returns_two_independent_sides(self):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [
                QgsPointXY(0, 10), QgsPointXY(0, -10),
                QgsPointXY(20, 10), QgsPointXY(20, -10),
            ]
        ).asWkt()

        expression = QgsExpression(
            "mct_bridge_or_gap_geometry(geom_from_wkt('{}'))".format(wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        side_a, side_b = result.asMultiPolyline()

        self.assertAlmostEqual(side_a[0].x(), 0)
        self.assertAlmostEqual(side_a[0].y(), 10)
        self.assertAlmostEqual(side_a[1].x(), 0)
        self.assertAlmostEqual(side_a[1].y(), -10)

        self.assertAlmostEqual(side_b[0].x(), 20)
        self.assertAlmostEqual(side_b[0].y(), 10)
        self.assertAlmostEqual(side_b[1].x(), 20)
        self.assertAlmostEqual(side_b[1].y(), -10)


    def test_is_offered_black_with_field_t(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            FIELD_T,
            LINE_MEASURE_TYPE_CODES,
            TABLE_H_XIX_INVENTORY,
            _OBSTACLE_LINE_LABEL_EXPRESSION,
            create_obstacle_control_measures_lines_layer,
        )

        self.assertEqual(
            LINE_MEASURE_TYPE_CODES["bridge_or_gap"], "271100"
        )

        entry = TABLE_H_XIX_INVENTORY["271100"]

        self.assertEqual(entry["colour"], BLACK)
        self.assertEqual(entry["field_t"], FIELD_T)

        self.assertIn("bridge_or_gap", _OBSTACLE_LINE_LABEL_EXPRESSION)

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        self.assertIn("bridge_or_gap", labels)


    def test_symbol_follows_present_planned_status(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _bridge_or_gap_symbol,
        )

        symbol = _bridge_or_gap_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 1)

        inner_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)

        self.assertTrue(
            inner_line.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.StrokeStyle
            )
        )


class TestRoadblockFamily(QgisTestCase):

    """
    Roadblocks, Craters and Blown Bridges (271201-271204) - three
    "state" variants of the same two-line construction ("points 1 and 2
    determine the centerline... point 3 determines its width") plus one
    differently-shaped variant, Roadblock Complete, read off the
    standard's own picture (ASSUMED, not CONFIRMED, in the module's own
    audit).
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _evaluate(self, function_name, pt1, pt2, pt3):

        from qgis.core import QgsGeometry, QgsPointXY

        wkt = QgsGeometry.fromPolylineXY(
            [QgsPointXY(*pt1), QgsPointXY(*pt2), QgsPointXY(*pt3)]
        ).asWkt()

        expression = QgsExpression(
            "{}(geom_from_wkt('{}'))".format(function_name, wkt)
        )

        result = expression.evaluate()

        self.assertFalse(
            expression.hasEvalError(), expression.evalErrorString()
        )

        return result


    PT1, PT2, PT3 = (0, 10), (0, -10), (15, 0)


    def test_main_line_is_pt1_pt2_reversed_so_the_tip_is_last(self):

        result = self._evaluate(
            "mct_roadblock_main_line", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "LineString")

        points = result.asPolyline()

        self.assertAlmostEqual(points[0].x(), 0)
        self.assertAlmostEqual(points[0].y(), -10)
        self.assertAlmostEqual(points[1].x(), 0)
        self.assertAlmostEqual(points[1].y(), 10)


    def test_parallel_line_is_offset_toward_pt3_by_its_perpendicular_distance(
        self
    ):

        result = self._evaluate(
            "mct_roadblock_parallel_line", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "LineString")

        points = result.asPolyline()

        self.assertAlmostEqual(points[0].x(), 15)
        self.assertAlmostEqual(points[0].y(), 10)
        self.assertAlmostEqual(points[1].x(), 15)
        self.assertAlmostEqual(points[1].y(), -10)


    def test_complete_geometry_crosses_to_the_opposite_offset_point(self):

        result = self._evaluate(
            "mct_roadblock_complete_geometry", self.PT1, self.PT2, self.PT3
        )

        self.assertEqual(result.wkbType().name, "MultiLineString")

        line_to_pt1, line_to_pt2 = result.asMultiPolyline()

        self.assertAlmostEqual(line_to_pt1[0].x(), 15)
        self.assertAlmostEqual(line_to_pt1[0].y(), -10)
        self.assertAlmostEqual(line_to_pt1[1].x(), 0)
        self.assertAlmostEqual(line_to_pt1[1].y(), 10)

        self.assertAlmostEqual(line_to_pt2[0].x(), 15)
        self.assertAlmostEqual(line_to_pt2[0].y(), 10)
        self.assertAlmostEqual(line_to_pt2[1].x(), 0)
        self.assertAlmostEqual(line_to_pt2[1].y(), -10)


    def test_all_four_variants_are_offered_and_green(self):

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            LINE_MEASURE_TYPE_CODES,
            TABLE_H_XIX_INVENTORY,
            create_obstacle_control_measures_lines_layer,
        )

        expected_codes = {
            "roadblock_planned": "271201",
            "roadblock_readiness_1": "271202",
            "roadblock_readiness_2": "271203",
            "roadblock_complete": "271204",
        }

        for measure_type, code in expected_codes.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(LINE_MEASURE_TYPE_CODES[measure_type], code)
                self.assertEqual(
                    TABLE_H_XIX_INVENTORY[code]["colour"], GREEN
                )

        layer = create_obstacle_control_measures_lines_layer()

        labels = {
            rule.label() for rule in layer.renderer().rootRule().children()
        }

        for measure_type in expected_codes:
            self.assertIn(measure_type, labels)


    def test_planned_dashes_both_lines(self):

        from qgis.PyQt.QtCore import Qt

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _roadblock_planned_symbol,
        )

        symbol = _roadblock_planned_symbol()

        main_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)
        parallel_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertEqual(main_line.penStyle(), Qt.PenStyle.DashLine)
        self.assertEqual(parallel_line.penStyle(), Qt.PenStyle.DashLine)


    def test_readiness_1_dashes_only_the_parallel_line(self):

        from qgis.PyQt.QtCore import Qt

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _roadblock_readiness_1_symbol,
        )

        symbol = _roadblock_readiness_1_symbol()

        main_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)
        parallel_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertEqual(main_line.penStyle(), Qt.PenStyle.SolidLine)
        self.assertEqual(parallel_line.penStyle(), Qt.PenStyle.DashLine)


    def test_readiness_2_is_fully_solid(self):

        from qgis.PyQt.QtCore import Qt

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _roadblock_readiness_2_symbol,
        )

        symbol = _roadblock_readiness_2_symbol()

        main_line = symbol.symbolLayer(0).subSymbol().symbolLayer(0)
        parallel_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertEqual(main_line.penStyle(), Qt.PenStyle.SolidLine)
        self.assertEqual(parallel_line.penStyle(), Qt.PenStyle.SolidLine)


    def test_each_state_variant_has_an_arrowhead_on_the_main_line_only(self):

        from qgis.core import Qgis, QgsMarkerLineSymbolLayer

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _roadblock_planned_symbol,
            _roadblock_readiness_1_symbol,
            _roadblock_readiness_2_symbol,
        )

        for builder in (
            _roadblock_planned_symbol,
            _roadblock_readiness_1_symbol,
            _roadblock_readiness_2_symbol,
        ):

            with self.subTest(builder=builder.__name__):

                symbol = builder()

                self.assertEqual(symbol.symbolLayerCount(), 3)

                chevron_marker_line = (
                    symbol.symbolLayer(2).subSymbol().symbolLayer(0)
                )

                self.assertIsInstance(
                    chevron_marker_line, QgsMarkerLineSymbolLayer
                )
                self.assertEqual(
                    chevron_marker_line.placements(),
                    Qgis.MarkerLinePlacement.LastVertex
                )
                self.assertIn(
                    "mct_roadblock_main_line($geometry)",
                    symbol.symbolLayer(2).geometryExpression()
                )


    def test_complete_has_two_arrowheads_via_its_own_geometry(self):

        from qgis.core import (
            Qgis, QgsGeometryGeneratorSymbolLayer, QgsMarkerLineSymbolLayer,
        )

        from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
            _roadblock_complete_symbol,
        )

        symbol = _roadblock_complete_symbol()

        self.assertEqual(symbol.symbolLayerCount(), 2)

        self.assertIsInstance(
            symbol.symbolLayer(0), QgsGeometryGeneratorSymbolLayer
        )
        self.assertIn(
            "mct_roadblock_complete_geometry($geometry)",
            symbol.symbolLayer(0).geometryExpression()
        )

        chevron_marker_line = symbol.symbolLayer(1).subSymbol().symbolLayer(0)

        self.assertIsInstance(chevron_marker_line, QgsMarkerLineSymbolLayer)

        self.assertEqual(
            chevron_marker_line.placements(),
            Qgis.MarkerLinePlacement.LastVertex
        )
