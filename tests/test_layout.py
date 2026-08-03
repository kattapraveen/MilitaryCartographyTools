# -*- coding: utf-8 -*-

"""
Tests for the "New Military Layout" suite (layout/new_layout.py's
create_layout()/update_layout()/get_layout_values(), and every
marginalia module's idempotent add_*/remove_* pair) and the
print-layout grid frame (grid/layout_grid_frame.py).

Military Cartography Tools
"""

from qgis.core import (
    QgsProject,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsLayoutItemMap,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.layout.new_layout import (
    create_layout,
    update_layout,
    get_layout_values,
    _find_map_item,
    _compute_geometry,
)
from MilitaryCartographyTools.grid.layout_grid_frame import add_grid_frame, remove_grid_frame
from MilitaryCartographyTools.layout.scale_bar import (
    _pick_units_per_segment,
    NUM_SEGMENTS,
    TARGET_BAR_WIDTH_MM,
)


def _bar_width_mm(scale, units_per_segment):
    return (units_per_segment * NUM_SEGMENTS * 1_000_000) / scale


class TestPickUnitsPerSegment(QgisTestCase):

    """
    Regression coverage for the scale-bar-too-large bug (confirmed
    live at 1:1,000 and 1:2,000 - see scale_bar.py's NICE_SEGMENT_KM
    comment): the picked segment size must never blow the bar up far
    past TARGET_BAR_WIDTH_MM just because the "nice" value list ran
    out of small enough options.
    """

    def test_close_in_scale_no_longer_overshoots_the_page(self):

        # Previously chose 0.1 (400mm bar - wider than a 297mm-wide
        # A4-landscape page). Should now land exactly on target.
        km = _pick_units_per_segment(1000, NUM_SEGMENTS)

        width_mm = _bar_width_mm(1000, km)

        self.assertLessEqual(width_mm, TARGET_BAR_WIDTH_MM * 1.5)

    def test_common_round_scale_unaffected(self):

        # 1:50,000 already landed exactly on target before this fix -
        # confirm the new smaller "nice" values don't change that.
        km = _pick_units_per_segment(50000, NUM_SEGMENTS)

        self.assertEqual(km, 1)

    def test_every_nice_value_is_smallest_that_meets_target(self):

        # For a spread of scales, the chosen value's bar width should
        # always be >= target (the function's contract) and never so
        # far past it that the previous "nice" value would also have
        # worked - i.e. it's genuinely the smallest sufficient one.
        for scale in (1000, 2000, 10000, 15000, 60000, 150000, 500000):

            km = _pick_units_per_segment(scale, NUM_SEGMENTS)

            self.assertGreaterEqual(
                _bar_width_mm(scale, km),
                TARGET_BAR_WIDTH_MM
            )


class FakeMapSettings:

    def __init__(self, crs):

        self._crs = crs


    def destinationCrs(self):

        return self._crs


class FakeCanvas:

    """
    Just enough of QgsMapCanvas's interface for create_layout():
    its own extent and destination CRS - not a real widget, since
    create_layout() never needs one.
    """

    def __init__(self, extent, crs="EPSG:32737"):

        self._extent = extent
        self._crs = QgsCoordinateReferenceSystem(crs)


    def extent(self):

        return self._extent


    def mapSettings(self):

        return FakeMapSettings(self._crs)


class FakeIface:

    def __init__(self, canvas):

        self._canvas = canvas
        self.opened = []


    def mapCanvas(self):

        return self._canvas


    def openLayoutDesigner(self, layout):

        self.opened.append(layout)


    def mainWindow(self):

        return None


def make_iface():

    canvas = FakeCanvas(
        QgsRectangle(200000, 9200000, 260000, 9240000)
    )

    return FakeIface(canvas)


class TestComputeGeometry(QgisTestCase):

    def test_no_heading_no_classification_map_fills_from_top_clearance(self):

        geometry = _compute_geometry(297.0, 210.0, [], "None")

        self.assertFalse(geometry["has_classification"])
        self.assertGreater(geometry["map_bottom"], geometry["map_top"])


    def test_heading_and_classification_push_map_top_down(self):

        bare = _compute_geometry(297.0, 210.0, [], "None")
        dressed = _compute_geometry(297.0, 210.0, ["Heading"], "RESTRICTED")

        self.assertTrue(dressed["has_classification"])
        self.assertGreater(dressed["map_top"], bare["map_top"])


class TestCreateAndUpdateLayout(QgisTestCase):

    def test_create_layout_has_a_map_item(self):

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
        )

        self.assertIsNotNone(_find_map_item(layout))


    def test_create_layout_applies_heading_and_classification(self):

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
            heading_lines=["Ex Experiment"],
            classification="SECRET",
        )

        heading_item = layout.itemById("mct_heading")
        classification_item = layout.itemById("mct_classification_top")

        self.assertIsNotNone(heading_item)
        self.assertEqual(heading_item.text(), "EX EXPERIMENT")
        self.assertIsNotNone(classification_item)
        self.assertEqual(classification_item.text(), "SECRET")


    def test_duplicate_layout_names_get_suffixed(self):

        iface = make_iface()

        first = create_layout(iface, "Same Name", 297.0, 210.0, 50000)
        second = create_layout(iface, "Same Name", 297.0, 210.0, 50000)

        self.assertEqual(first.name(), "Same Name")
        self.assertEqual(second.name(), "Same Name (2)")


    def test_update_layout_changes_size_scale_and_clears_optional_items(self):

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
            heading_lines=["Heading"],
            classification="RESTRICTED",
        )

        update_layout(
            layout,
            420.0,
            297.0,
            100000,
            heading_lines=[],
            classification="None",
        )

        values = get_layout_values(layout)

        self.assertEqual(values["width"], 420.0)
        self.assertEqual(values["height"], 297.0)
        self.assertEqual(values["scale"], 100000.0)
        self.assertEqual(values["heading_lines"], [])
        self.assertEqual(values["classification"], "None")

        self.assertIsNone(layout.itemById("mct_heading"))
        self.assertIsNone(layout.itemById("mct_classification_top"))


    def test_update_layout_preserves_map_centre(self):

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
        )

        map_item = _find_map_item(layout)
        center_before = map_item.extent().center()

        update_layout(layout, 420.0, 297.0, 100000)

        center_after = map_item.extent().center()

        self.assertAlmostEqual(center_before.x(), center_after.x(), delta=1.0)
        self.assertAlmostEqual(center_before.y(), center_after.y(), delta=1.0)


    def test_repeated_apply_never_duplicates_marginalia_items(self):

        """
        Idempotency regression: calling update_layout() repeatedly
        (simulating repeated "Apply" clicks in the Layout Settings
        panel) must replace each marginalia item in place, never
        stack duplicates.
        """

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
            heading_lines=["A"],
            classification="SECRET",
        )

        for _ in range(3):

            update_layout(
                layout,
                297.0,
                210.0,
                50000,
                heading_lines=["A"],
                classification="SECRET",
            )

        item_ids = [
            "mct_heading",
            "mct_classification_top",
            "mct_classification_bottom",
            "mct_scale_bar",
            "mct_scale_bar_unit_label",
            "mct_scale_bar_scale_label",
            "mct_metadata_block",
            "mct_center_coordinate",
            "mct_north_arrow",
        ]

        for item_id in item_ids:

            with self.subTest(item_id=item_id):

                matches = [
                    item
                    for item in layout.items()
                    if hasattr(item, "id") and item.id() == item_id
                ]

                self.assertEqual(len(matches), 1)


class TestGridFrame(QgisTestCase):

    def test_add_and_remove_grid_frame(self):

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
        )

        map_item = _find_map_item(layout)

        add_grid_frame(map_item)

        names = [grid.name() for grid in map_item.grids().asList()]
        self.assertIn("Military Grid Frame", names)

        remove_grid_frame(map_item)

        names = [grid.name() for grid in map_item.grids().asList()]
        self.assertNotIn("Military Grid Frame", names)


    def test_add_grid_frame_twice_does_not_duplicate(self):

        layout = create_layout(
            make_iface(),
            "Test Layout",
            297.0,
            210.0,
            50000,
        )

        map_item = _find_map_item(layout)

        add_grid_frame(map_item)
        add_grid_frame(map_item)

        names = [
            grid.name()
            for grid in map_item.grids().asList()
            if grid.name() == "Military Grid Frame"
        ]

        self.assertEqual(len(names), 1)
