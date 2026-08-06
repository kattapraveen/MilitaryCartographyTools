# -*- coding: utf-8 -*-

"""
Tests for layout/map_sheet_series_dialog.py's
generate_from_dialog_values() - the accept-flow logic driven by
MapSheetSeriesDialog's OK button, split out so it's testable
without driving an actual QDialog, matching the rest of this
plugin's dialog modules.

Military Cartography Tools
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject, QgsRectangle

from .qgis_test_case import FakeIface, make_canvas, QgisTestCase

from MilitaryCartographyTools.layout.map_sheet_series_dialog import (
    generate_from_dialog_values,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


def _values(width=297.0, height=210.0, scale=100000.0):

    return {
        "width": width,
        "height": height,
        "scale": scale,
        "heading_lines": [],
        "classification": "None",
    }


class TestGenerateFromDialogValues(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.canvas = make_canvas()

        self.canvas.setExtent(
            QgsRectangle(39.0, -7.0, 39.2, -6.8)
        )

        self.iface = FakeIface(canvas=self.canvas)


    def test_generates_layouts_for_the_current_canvas_extent(self):

        layouts = generate_from_dialog_values(
            self.iface,
            _values()
        )

        self.assertIsNotNone(layouts)
        self.assertGreater(len(layouts), 0)

        manager = QgsProject.instance().layoutManager()

        self.assertEqual(
            len(manager.layouts()),
            len(layouts)
        )


    def test_success_pushes_an_info_message(self):

        generate_from_dialog_values(
            self.iface,
            _values()
        )

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_too_many_sheets_warns_and_returns_none(self):

        # A very fine scale over the current (still fairly large)
        # canvas extent forces far more sheets than the practical
        # limit.
        result = generate_from_dialog_values(
            self.iface,
            _values(scale=500.0)
        )

        self.assertIsNone(result)
        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )

        manager = QgsProject.instance().layoutManager()

        self.assertEqual(
            len(manager.layouts()),
            0
        )


    def test_a_later_success_clears_an_earlier_queued_warning(self):

        # Regression test: an over-limit attempt followed by a
        # narrowed-down, successful one within the same dialog
        # session must not leave the first attempt's warning sitting
        # queued behind the success message, where it could resurface
        # later and look like a stray, contradictory failure.
        generate_from_dialog_values(
            self.iface,
            _values(scale=500.0)
        )

        generate_from_dialog_values(
            self.iface,
            _values()
        )

        self.assertEqual(
            self.iface.messageBar().clear_count,
            2
        )
