# -*- coding: utf-8 -*-

"""
Non-NATO symbology expression functions for Military Cartography Tools.

Kept separate from expressions/military_symbology_functions.py on
purpose: the two mct_sidc_svg()/mct_build_sidc() functions there are
generic milsymbol/SIDC plumbing NATO layers depend on (frame/fill were
added there as a small, additive, backward-compatible exception - see
that module's own mct_sidc_svg() docstring). Everything here is
genuinely non-NATO-specific business logic - the affiliation colour
map, the entity/echelon icon fixups, the Combined Arms overlay, Enemy
(Info Unknown)'s no-SIDC special case - and belongs in its own file so
it can never be mistaken for something a NATO layer might also need.

Military Cartography Tools
"""

import base64
import re

from qgis.core import QgsExpression, qgsfunction

from ..military_symbology.nonnato_symbol_engine import (
    booby_trap_control_measure_svg,
    render_nonnato_equipment_svg,
    render_nonnato_pillbox_svg,
    render_nonnato_unit_svg,
)


def _viewbox_width(svg):

    """
    The rendered SVG's own declared width (viewBox's 3rd number) - same
    regex military_symbology_functions.py's own mct_sidc_svg_width()
    uses, needed for exactly the same reason: QGIS sizes an SVG marker
    by this width, and a typed designation widens it, so a size
    expression has to divide it out to hold the icon still. See
    _stabilised_size_expression() below for where this feeds in.
    """

    match = re.search(r'viewBox="\S+ \S+ (\S+) \S+"', svg)

    return float(match.group(1)) if match else 0.0


def _viewbox_height(svg):

    """
    The rendered SVG's own declared height (viewBox's 4th number) - the
    companion to _viewbox_width() above, needed for a different reason:
    QGIS anchors an SVG marker on the CENTRE of its own viewBox, and
    inject_centered_designation_below() grows that viewBox downward to
    fit the designation text, which moves the centre down and so shifts
    the icon itself UP on the map. Anything composed alongside the icon
    as its own symbol layer (see land_equipment_layer_nonnato.py's own
    _wheel_symbol_layers()) has to follow that shift, which means
    knowing the height the icon actually rendered at.
    """

    match = re.search(r'viewBox="\S+ \S+ \S+ (\S+)"', svg)

    return float(match.group(1)) if match else 0.0


def _render_unit(values):

    """
    Shared argument parsing for mct_nonnato_unit_svg()/_width() - kept
    in one place so the two can never read a differently-defaulted
    echelon/status/designation_left/designation_right/combined_arms
    from the same raw `values`. Returns (svg, error_text); exactly one
    is None.
    """

    if len(values) < 2:
        return None, "Need at least an affiliation and an entity"

    affiliation = str(values[0])
    entity = str(values[1])
    echelon = str(values[2]) if len(values) > 2 and values[2] else "unspecified"
    status = str(values[3]) if len(values) > 3 and values[3] else "present"
    designation_left = values[4] if len(values) > 4 else None
    designation_right = values[5] if len(values) > 5 else None
    combined_arms = bool(values[6]) if len(values) > 6 and values[6] else False

    try:

        svg = render_nonnato_unit_svg(
            affiliation,
            entity,
            echelon=echelon,
            status=status,
            designation_left=designation_left,
            designation_right=designation_right,
            combined_arms=combined_arms,
        )

    except KeyError as error:

        # Matches mct_build_sidc()'s own convention (see that
        # function): an invalid attribute value returns readable error
        # text through the expression rather than raising out of a
        # renderer callback, which QGIS would otherwise surface as a
        # much less useful generic evaluation failure.
        return None, str(error)

    return svg, None


@qgsfunction(
    'mct_nonnato_unit_svg',
    group='Military Cartography Tools'
)
def mct_nonnato_unit_svg(values, feature=None, parent=None):

    """
    "base64:<...>" for a non-NATO Land Unit feature's own attributes -
    the one function land_unit_layer_nonnato.py's renderer calls,
    mirroring mct_sidc_svg()'s own role for NATO layers but built
    around render_nonnato_unit_svg() instead of a raw SIDC string,
    since non-NATO needs real logic (the affiliation colour map, the
    icon fixups, Combined Arms, Enemy (Info Unknown)'s no-SIDC path)
    that a thin milsymbol-options passthrough can't express.

    Arguments, all but the first two optional: affiliation, entity,
    echelon (default "unspecified"), status (default "present"),
    designation_left (default none), designation_right (default none),
    combined_arms (default false).

    See mct_nonnato_unit_svg_width() below for the icon-size
    stabilisation companion function - land_unit_layer_nonnato.py's own
    renderer calls both, mirroring mct_sidc_svg()/mct_sidc_svg_width()'s
    own pairing for NATO layers.
    """

    svg, error = _render_unit(values)

    if error is not None:
        return error

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_nonnato_unit_svg_width',
    group='Military Cartography Tools'
)
def mct_nonnato_unit_svg_width(values, feature=None, parent=None):

    """
    The rendered WIDTH, in milsymbol's own icon units, of exactly the
    symbol mct_nonnato_unit_svg() would return for the same arguments -
    the non-NATO Land Unit counterpart to mct_sidc_svg_width() (see
    that function's own docstring for the full reasoning: QGIS sizes an
    SVG marker by its width, and milsymbol widens an icon's box to take
    in a typed designation, which SHRINKS the icon at a fixed marker
    size unless something divides that widening back out).

    Fixed 2026-09-02, reported live: "when i insert a land unit with
    designator, the size of the glyph is reducing making it
    unreadable" - this layer never got the NATO layers' own 2026-08-13
    fix, because stabilised_point_size_expression() is hardwired to
    mct_sidc_svg()'s own call shape (string-replaces "mct_sidc_svg(",
    parses out a "mct_build_sidc(...)" argument) and none of that
    exists in a mct_nonnato_unit_svg(...) call. See nonnato_symbol_
    engine.stabilised_nonnato_size_expression() for the decoupled
    version built for this instead.

    Takes mct_nonnato_unit_svg()'s own argument list, so the two can be
    called side by side with the same expression text - same contract
    mct_sidc_svg_width() documents for its own sibling.
    """

    svg, error = _render_unit(values)

    if error is not None:
        return 0.0

    return _viewbox_width(svg)


def _render_equipment(values):

    """Shared argument parsing for mct_nonnato_equipment_svg()/_width() - see _render_unit()'s own docstring for why this is factored out."""

    if len(values) < 2:
        return None, "Need at least an affiliation and an entity"

    affiliation = str(values[0])
    entity = str(values[1])
    designation = values[2] if len(values) > 2 else None

    try:

        svg = render_nonnato_equipment_svg(
            affiliation, entity, designation=designation
        )

    except KeyError as error:

        return None, str(error)

    return svg, None


@qgsfunction(
    'mct_nonnato_equipment_svg',
    group='Military Cartography Tools'
)
def mct_nonnato_equipment_svg(values, feature=None, parent=None):

    """
    "base64:<...>" for a non-NATO Land Equipment feature - mirrors
    mct_nonnato_unit_svg()'s own role but built around render_nonnato_
    equipment_svg() instead: no echelon/status/combined_arms arguments,
    since none of the three apply to Equipment (no frame to carry an
    echelon or Combined Arms indicator, and Status is settled as
    Units-only). Also covers Jammer/Radar (SIGINT, Land-scoped) since
    2026-09-02 - merged in here rather than kept as its own function,
    at the maintainer's own request, once a two-entity layer stopped
    justifying its own module. render_nonnato_equipment_svg() itself
    handles the different SIDC symbol_set those two need.

    Also called from the "Mines and Obstacles (Non-NATO)" layer since
    2026-09-03, for the nine mine entities that moved out of Land
    Equipment there (see mines_and_obstacles_layer_nonnato.py) - this
    function itself needed no change, since it was always layer-
    agnostic; only which layer's own renderer calls it changed.

    Arguments, the second optional: affiliation, entity, designation
    (default none). See mct_nonnato_equipment_svg_width() below for the
    icon-size stabilisation companion function.
    """

    svg, error = _render_equipment(values)

    if error is not None:
        return error

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_nonnato_equipment_svg_width',
    group='Military Cartography Tools'
)
def mct_nonnato_equipment_svg_width(values, feature=None, parent=None):

    """The rendered WIDTH of exactly the symbol mct_nonnato_equipment_svg() would return - see mct_nonnato_unit_svg_width()'s own docstring for the full reasoning and the 2026-09-02 fix this belongs to."""

    svg, error = _render_equipment(values)

    if error is not None:
        return 0.0

    return _viewbox_width(svg)


@qgsfunction(
    'mct_nonnato_equipment_svg_height',
    group='Military Cartography Tools'
)
def mct_nonnato_equipment_svg_height(values, feature=None, parent=None):

    """
    The rendered HEIGHT of exactly the symbol mct_nonnato_equipment_
    svg() would return, in milsymbol's own icon units - takes the same
    argument list as its two siblings above.

    Added 2026-09-03 for Armoured Protection Vehicle (Wheeled), whose
    own three wheels are separate simple-marker symbol layers rather
    than circles inside the SVG (see land_equipment_layer_nonnato.py's
    own _wheel_symbol_layers() for why). Those layers are offset from
    the map point, but the ICON is anchored on its own viewBox centre -
    and that centre moves down as soon as a designation grows the
    viewBox downward, shifting the icon up while a fixed offset would
    leave the wheels behind, overlapping the designation text (reported
    live: "when i add the unique designator in APV wheeled, the wheels
    shift and overlap on the text of unique designation instead of
    staying where they are"). Feeding this height into the wheels' own
    offset expression keeps them locked to the hull.
    """

    svg, error = _render_equipment(values)

    if error is not None:
        return 0.0

    return _viewbox_height(svg)


@qgsfunction(
    'mct_nonnato_booby_trap_svg',
    group='Military Cartography Tools'
)
def mct_nonnato_booby_trap_svg(values, feature=None, parent=None):

    """
    "base64:<...>" for Mines and Obstacles' own Booby Trap (moved here
    2026-09-03 from Control Measure Points, alongside the mine family -
    see mines_and_obstacles_layer_nonnato.py) - a fully custom icon (see
    booby_trap_control_measure_svg()'s own docstring), not routed
    through mct_sidc_svg()/milsymbol at all. Fixed MINE_GREEN, no
    arguments needed - unlike every other mct_nonnato_*_svg() function,
    this one entity's colour never varies by affiliation, matching every
    other mine-family icon's own convention.
    """

    svg = booby_trap_control_measure_svg()

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


def _render_pillbox(values):

    """Shared argument parsing for mct_nonnato_pillbox_svg()/_width() - see _render_unit()'s own docstring for why this is factored out."""

    if len(values) < 1:
        return None, "Need at least an affiliation"

    affiliation = str(values[0])
    status = str(values[1]) if len(values) > 1 and values[1] else "present"
    designation = values[2] if len(values) > 2 else None

    svg = render_nonnato_pillbox_svg(
        affiliation, status=status, designation=designation
    )

    return svg, None


@qgsfunction(
    'mct_nonnato_pillbox_svg',
    group='Military Cartography Tools'
)
def mct_nonnato_pillbox_svg(values, feature=None, parent=None):

    """
    "base64:<...>" for the Control Measure Point's own Pill Box
    (`shelter`) - branched out to its own function purely for
    apply_pillbox_fixup() (see render_nonnato_pillbox_svg()'s own
    docstring): every other Control Measure Point entity still goes
    straight through the plain mct_sidc_svg() pipeline.

    Arguments, the first required: affiliation, status (default
    "present"), designation (default none).
    """

    svg, error = _render_pillbox(values)

    if error is not None:
        return error

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_nonnato_pillbox_svg_width',
    group='Military Cartography Tools'
)
def mct_nonnato_pillbox_svg_width(values, feature=None, parent=None):

    """The rendered WIDTH of exactly the symbol mct_nonnato_pillbox_svg() would return - see mct_nonnato_unit_svg_width()'s own docstring for the full reasoning behind this pairing."""

    svg, error = _render_pillbox(values)

    if error is not None:
        return 0.0

    return _viewbox_width(svg)


_FUNCTIONS = [
    mct_nonnato_unit_svg,
    mct_nonnato_unit_svg_width,
    mct_nonnato_equipment_svg,
    mct_nonnato_equipment_svg_width,
    mct_nonnato_equipment_svg_height,
    mct_nonnato_booby_trap_svg,
    mct_nonnato_pillbox_svg,
    mct_nonnato_pillbox_svg_width,
]


def register():

    for function in _FUNCTIONS:

        QgsExpression.registerFunction(
            function
        )


def unregister():

    for function in _FUNCTIONS:

        QgsExpression.unregisterFunction(
            function.name()
        )
