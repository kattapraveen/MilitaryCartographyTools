# -*- coding: utf-8 -*-

"""
Tests for military_symbology/obstacle_control_measures.py - Table
H-XIX, Mini-Phase H15/H16.

This module currently holds the batch-B0 AUDIT only; no layers or
symbols are built yet. So these tests pin the inventory itself, which
is what every later batch reads from - see that module's own docstring.

Military Cartography Tools
"""

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
