# -*- coding: utf-8 -*-

"""
Tests for military_symbology/layout_symbol_dialog.py - U-1's "Insert
Symbol" dialog, the minimal Affiliation/Symbol Set/Entity picker used
to place a static symbol onto a print layout page.

Military Cartography Tools
"""

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology.edition import (
    set_current_edition,
)
from MilitaryCartographyTools.military_symbology.layout_symbol_dialog import (
    DEFAULT_SYMBOL_SET,
    SYMBOL_SET_LABELS,
    InsertSymbolDialog,
    humanize_entity_key,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    DEFAULT_EDITION,
    SYMBOL_SETS,
    entities_for_edition,
)


class TestSymbolSetLabels(QgisTestCase):

    def test_every_symbol_set_has_a_label(self):

        self.assertEqual(set(SYMBOL_SET_LABELS), set(SYMBOL_SETS))


    def test_default_symbol_set_is_a_real_one(self):

        self.assertIn(DEFAULT_SYMBOL_SET, SYMBOL_SETS)


class TestHumanizeEntityKey(QgisTestCase):

    def test_underscores_become_spaces_and_title_case(self):

        self.assertEqual(
            humanize_entity_key("command_post_node"),
            "Command Post Node"
        )


    def test_single_word(self):

        self.assertEqual(humanize_entity_key("infantry"), "Infantry")


class TestInsertSymbolDialog(QgisTestCase):

    def tearDown(self):

        set_current_edition(DEFAULT_EDITION)
        super().tearDown()


    def test_defaults_to_the_default_symbol_set_and_a_real_entity(self):

        dialog = InsertSymbolDialog()

        self.assertEqual(
            dialog.symbol_set_combo.currentData(), DEFAULT_SYMBOL_SET
        )

        self.assertIn(
            dialog.entity_combo.currentData(),
            entities_for_edition(DEFAULT_EDITION)[DEFAULT_SYMBOL_SET]
        )


    def test_changing_symbol_set_repopulates_entity(self):

        dialog = InsertSymbolDialog()

        index = dialog.symbol_set_combo.findData("air")

        self.assertNotEqual(index, -1)

        dialog.symbol_set_combo.setCurrentIndex(index)

        self.assertIn(
            dialog.entity_combo.currentData(),
            entities_for_edition(DEFAULT_EDITION)["air"]
        )


    def test_sidc_reflects_the_current_selection(self):

        dialog = InsertSymbolDialog()

        index = dialog.affiliation_combo.findData("hostile")
        dialog.affiliation_combo.setCurrentIndex(index)

        index = dialog.symbol_set_combo.findData("air")
        dialog.symbol_set_combo.setCurrentIndex(index)

        index = dialog.entity_combo.findData("bomber")
        self.assertNotEqual(index, -1)
        dialog.entity_combo.setCurrentIndex(index)

        sidc = dialog.sidc()

        self.assertEqual(sidc[3], "6")  # hostile
        self.assertEqual(sidc[4:6], SYMBOL_SETS["air"])
        self.assertEqual(
            sidc[10:16], entities_for_edition(DEFAULT_EDITION)["air"]["bomber"]
        )


    def test_entity_label_matches_the_combo_text(self):

        dialog = InsertSymbolDialog()

        self.assertEqual(
            dialog.entity_label(), dialog.entity_combo.currentText()
        )


    def test_every_symbol_set_offers_at_least_one_entity(self):

        # Every combo entry must actually populate the Entity dropdown
        # under the default edition - an empty Entity combo would let
        # the user click Insert with no valid selection at all.
        dialog = InsertSymbolDialog()

        for symbol_set in SYMBOL_SET_LABELS:

            with self.subTest(symbol_set=symbol_set):

                index = dialog.symbol_set_combo.findData(symbol_set)

                self.assertNotEqual(index, -1)

                dialog.symbol_set_combo.setCurrentIndex(index)

                self.assertGreater(dialog.entity_combo.count(), 0)


    def test_entities_track_the_current_edition(self):

        set_current_edition("2525E")

        dialog = InsertSymbolDialog()

        self.assertIn(
            dialog.entity_combo.currentData(),
            entities_for_edition("2525E")[DEFAULT_SYMBOL_SET]
        )
