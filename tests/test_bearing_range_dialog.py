# -*- coding: utf-8 -*-

"""
Tests for core/bearing_range_tool.py's BearingRangeDialog - the
persistent log table set_from()/set_to() fill in, independent of
BearingRangeTool's own click state machine (see
tests/test_bearing_range_tool.py for that).

Military Cartography Tools
"""

from qgis.core import QgsPointXY

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.core.bearing_range_tool import (
    BearingRangeDialog,
    COLUMN_LABELS,
)


class TestBearingRangeDialog(QgisTestCase):

    def test_set_from_updates_label_and_clears_previous_to_point(self):

        dialog = BearingRangeDialog()

        dialog.set_from(QgsPointXY(37.34, -3.09))
        dialog.set_to(QgsPointXY(37.35, -3.08))

        dialog.set_from(QgsPointXY(37.36, -3.07))

        self.assertIsNone(dialog.to_lonlat)
        self.assertEqual(dialog.to_label.text(), "-")


    def test_from_label_shows_lat_lon_and_mgrs_on_separate_lines(self):

        dialog = BearingRangeDialog()

        point = QgsPointXY(37.34, -3.09)
        dialog.set_from(point)

        expected_mgrs = dialog.converter.format(
            dialog.converter.convert(point.y(), point.x())
        )

        lines = dialog.from_label.text().split("\n")

        self.assertEqual(len(lines), 2)
        self.assertIn("-3.09", lines[0])
        self.assertEqual(lines[1], expected_mgrs)


    def test_logged_row_shows_mgrs_for_both_points(self):

        dialog = BearingRangeDialog()

        from_point = QgsPointXY(37.34, -3.09)
        to_point = QgsPointXY(37.34, -2.09)

        dialog.set_from(from_point)
        dialog.set_to(to_point)

        expected_from_mgrs = dialog.converter.format(
            dialog.converter.convert(from_point.y(), from_point.x())
        )
        expected_to_mgrs = dialog.converter.format(
            dialog.converter.convert(to_point.y(), to_point.x())
        )

        from_column = COLUMN_LABELS.index("From")
        to_column = COLUMN_LABELS.index("To")

        self.assertIn(
            expected_from_mgrs,
            dialog.table.item(0, from_column).text()
        )

        self.assertIn(
            expected_to_mgrs,
            dialog.table.item(0, to_column).text()
        )


    def test_set_to_logs_a_row_with_all_columns(self):

        dialog = BearingRangeDialog()

        dialog.set_from(QgsPointXY(37.34, -3.09))
        dialog.set_to(QgsPointXY(37.34, -2.09))

        self.assertEqual(dialog.table.rowCount(), 1)

        for column in range(len(COLUMN_LABELS)):

            self.assertIsNotNone(dialog.table.item(0, column))
            self.assertNotEqual(dialog.table.item(0, column).text(), "")


    def test_due_north_reading_shows_zero_true_azimuth(self):

        dialog = BearingRangeDialog()

        dialog.set_from(QgsPointXY(37.34, -3.09))
        dialog.set_to(QgsPointXY(37.34, -2.09))

        true_azimuth_column = COLUMN_LABELS.index("True Az")

        self.assertEqual(
            dialog.table.item(0, true_azimuth_column).text(),
            "0.0°"
        )


    def test_new_rows_are_inserted_at_the_top(self):

        dialog = BearingRangeDialog()

        dialog.set_from(QgsPointXY(37.34, -3.09))
        dialog.set_to(QgsPointXY(37.34, -2.09))

        dialog.set_from(QgsPointXY(37.40, -3.09))
        dialog.set_to(QgsPointXY(37.40, -2.09))

        self.assertEqual(dialog.table.rowCount(), 2)

        # The second (most recent) reading's "From" point is the
        # newer one, still on top.
        from_column = COLUMN_LABELS.index("From")

        self.assertIn(
            "37.4",
            dialog.table.item(0, from_column).text()
        )


    def test_clear_button_empties_the_table(self):

        dialog = BearingRangeDialog()

        dialog.set_from(QgsPointXY(37.34, -3.09))
        dialog.set_to(QgsPointXY(37.34, -2.09))

        # The Clear button is the only QPushButton in the dialog -
        # simplest reliable way to reach it without relying on
        # layout traversal.
        from qgis.PyQt.QtWidgets import QPushButton

        clear_button = dialog.findChild(QPushButton)
        clear_button.click()

        self.assertEqual(dialog.table.rowCount(), 0)
