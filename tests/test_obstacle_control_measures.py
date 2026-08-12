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

from MilitaryCartographyTools.military_symbology.obstacle_control_measures import (
    AREA,
    LINE,
    PARENT,
    POINT,
    TABLE_H_XIX_INVENTORY,
    buildable_inventory,
    inventory_for_batch,
)


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

        for code, (name, geometry, batch, verified) in TABLE_H_XIX_INVENTORY.items():

            with self.subTest(code=code):

                self.assertIn(geometry, (AREA, LINE, POINT, PARENT))
                self.assertTrue(name)
                self.assertTrue(batch)
                self.assertIsInstance(verified, bool)


    def test_parent_rows_are_excluded_from_buildable_work(self):

        # Heading rows whose template column reads "N/A" - nothing to
        # draw. Ten of the 75.
        parents = {
            code for code, entry in TABLE_H_XIX_INVENTORY.items()
            if entry[1] == PARENT
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

            self.assertNotEqual(entry[1], PARENT)


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

            self.assertEqual(TABLE_H_XIX_INVENTORY[code][1], POINT)

        # Only these two of the family are freeform areas.
        for code in ("270706", "270707"):

            self.assertEqual(TABLE_H_XIX_INVENTORY[code][1], AREA)

        # The one 28xxxx code that is a line, not a point.
        self.assertEqual(TABLE_H_XIX_INVENTORY["282003"][1], LINE)
        self.assertEqual(TABLE_H_XIX_INVENTORY["282003"][0], "Overhead Wire")

        # The PDF text layer renders 271500 as "~~ry", which reads as
        # Ferry. It is Ford Easy; Ferry is 290700.
        self.assertEqual(TABLE_H_XIX_INVENTORY["271500"][0], "Ford Easy")
        self.assertEqual(TABLE_H_XIX_INVENTORY["290700"][0], "Ferry")
