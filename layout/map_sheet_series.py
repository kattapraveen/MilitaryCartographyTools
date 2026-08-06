# -*- coding: utf-8 -*-

"""
Batch-generate a numbered series of print sheets tiling a large
area of operations (AO) extent - mostly a wrapper around New
Military Layout's own create_layout() (called once per sheet, at
that sheet's own computed centre), rather than new print-layout
geometry work of its own. Every layout create_layout() builds
already gets its own grid position diagram (see
grid_position_diagram.py) automatically, so this module doesn't
need to add one itself.

Sheets are named after the real MGRS grid square their own centre
falls in - "{GZD} {100km square}" (e.g. "37M EN"), not any separate,
invented numbering scheme - plus a running "#N" sequence number,
since a print sheet at any normal operational scale is almost always
much smaller than one 100km square, so several sheets in the same
series routinely share that same base name and need disambiguating.

Military Cartography Tools
"""

import math
from collections import defaultdict

from qgis.core import QgsCoordinateTransform, QgsPointXY, QgsProject

from ..core.coordinate_utils import WGS84, get_utm_crs
from .grid_position import grid_label_for_point
from .new_layout import MAP_SIDE_MARGIN, _compute_geometry, create_layout


# Guards against an accidental huge-AO/small-scale combination
# silently kicking off generating hundreds of layouts, which would
# be extremely slow and almost certainly not what was intended -
# the dialog surfaces this as a warning asking to zoom in or choose
# a larger scale denominator instead.
MAX_SHEETS = 200


def _sheet_ground_size_m(width_mm, height_mm, scale, heading_lines, classification):

    """
    (ground_width_m, ground_height_m) one sheet covers at the given
    page size/scale - derived from the map item's own rect (page
    size minus margins/marginalia bands), the same geometry
    create_layout() itself computes, so a generated series' sheets
    tile edge-to-edge with no gap or overlap against what each
    individual layout actually renders.
    """

    geometry = _compute_geometry(
        width_mm,
        height_mm,
        heading_lines,
        classification
    )

    rect_width_mm = width_mm - (2 * MAP_SIDE_MARGIN)
    rect_height_mm = geometry["map_bottom"] - geometry["map_top"]

    return (
        (rect_width_mm / 1000.0) * scale,
        (rect_height_mm / 1000.0) * scale
    )


def compute_sheet_grid(
    ao_extent,
    ao_crs,
    width_mm,
    height_mm,
    scale,
    heading_lines=None,
    classification=None
):

    """
    A rows x cols grid (list of lists, row 0 = north) of per-sheet
    dicts - {"row", "col", "center", "center_wgs84"} - tiling
    ao_extent (given in ao_crs) edge-to-edge starting from its own
    north-west corner. "center" is in ao_crs (ready to hand straight
    to create_layout()'s own center parameter, since that's the same
    CRS the map canvas/layout map item itself uses); "center_wgs84"
    is provided separately since naming needs latitude/longitude.

    Tiling math itself happens in a local UTM zone derived from the
    AO's own centre (matching get_utm_crs()'s use everywhere else
    in this plugin) rather than ao_crs directly, since ao_crs may be
    geographic (degrees), where "width in degrees" isn't a uniform
    real-world distance to tile against.
    """

    heading_lines = heading_lines or []

    transform_to_wgs84 = QgsCoordinateTransform(
        ao_crs,
        WGS84,
        QgsProject.instance()
    )

    ao_center_wgs84 = transform_to_wgs84.transform(
        ao_extent.center()
    )

    tiling_crs = get_utm_crs(
        ao_center_wgs84.y(),
        ao_center_wgs84.x()
    )

    transform_to_tiling_crs = QgsCoordinateTransform(
        ao_crs,
        tiling_crs,
        QgsProject.instance()
    )

    transform_from_tiling_crs = QgsCoordinateTransform(
        tiling_crs,
        ao_crs,
        QgsProject.instance()
    )

    transform_tiling_to_wgs84 = QgsCoordinateTransform(
        tiling_crs,
        WGS84,
        QgsProject.instance()
    )

    ao_extent_tiling_crs = transform_to_tiling_crs.transformBoundingBox(
        ao_extent
    )

    ground_width_m, ground_height_m = _sheet_ground_size_m(
        width_mm,
        height_mm,
        scale,
        heading_lines,
        classification
    )

    cols = max(
        1,
        math.ceil(ao_extent_tiling_crs.width() / ground_width_m)
    )

    rows = max(
        1,
        math.ceil(ao_extent_tiling_crs.height() / ground_height_m)
    )

    if rows * cols > MAX_SHEETS:

        raise ValueError(
            f"This would generate {rows * cols} sheets ({rows} rows x "
            f"{cols} columns), over the {MAX_SHEETS}-sheet limit - zoom "
            "in to a smaller area or choose a larger scale denominator."
        )

    north = ao_extent_tiling_crs.yMaximum()
    west = ao_extent_tiling_crs.xMinimum()

    grid = []

    for row in range(rows):

        grid_row = []

        for col in range(cols):

            center_tiling_crs = QgsPointXY(
                west + (ground_width_m * (col + 0.5)),
                north - (ground_height_m * (row + 0.5))
            )

            center = transform_from_tiling_crs.transform(
                center_tiling_crs
            )

            center_wgs84 = transform_tiling_to_wgs84.transform(
                center_tiling_crs
            )

            grid_row.append(
                {
                    "row": row,
                    "col": col,
                    "center": center,
                    "center_wgs84": center_wgs84,
                }
            )

        grid.append(
            grid_row
        )

    return grid


def _assign_sheet_names(grid):

    """
    "{GZD} {100km square} #{N}" for every sheet in grid, in row-
    major generation order - N restarts at 1 for each distinct GZD/
    100km-square pair, since that's the actual disambiguator: two
    sheets only need telling apart when they'd otherwise share the
    same base name.
    """

    sequence_by_base_name = defaultdict(int)

    for grid_row in grid:

        for sheet in grid_row:

            gzd, hundred_km_id = grid_label_for_point(
                sheet["center_wgs84"].y(),
                sheet["center_wgs84"].x()
            )

            base_name = f"{gzd} {hundred_km_id}"

            sequence_by_base_name[base_name] += 1

            sheet["name"] = (
                f"{base_name} #{sequence_by_base_name[base_name]}"
            )


def generate_sheet_series(
    iface,
    ao_extent,
    ao_crs,
    width_mm,
    height_mm,
    scale,
    heading_lines=None,
    classification=None
):

    """
    Build one print layout per sheet in the grid tiling ao_extent,
    each named after the real MGRS grid square its own centre falls
    in (see _assign_sheet_names()). Layouts are registered in the
    project's Layout Manager but not opened in the Designer
    individually - opening dozens of Designer windows at once isn't
    practical - the caller reports how many were created instead.

    Returns the flat list of created QgsPrintLayout objects, in
    row-major order.
    """

    grid = compute_sheet_grid(
        ao_extent,
        ao_crs,
        width_mm,
        height_mm,
        scale,
        heading_lines,
        classification
    )

    _assign_sheet_names(
        grid
    )

    layouts = []

    for grid_row in grid:

        for sheet in grid_row:

            layout = create_layout(
                iface,
                f"Sheet {sheet['name']}",
                width_mm,
                height_mm,
                scale,
                heading_lines=heading_lines,
                classification=classification,
                center=sheet["center"],
                open_designer=False
            )

            layouts.append(
                layout
            )

    return layouts
