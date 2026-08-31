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

from qgis.core import QgsExpression, qgsfunction

from ..military_symbology.nonnato_symbol_engine import (
    booby_trap_control_measure_svg,
    render_nonnato_equipment_svg,
    render_nonnato_sigint_svg,
    render_nonnato_unit_svg,
)


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
    designation (default none), combined_arms (default false).

    **No icon-size stabilisation for a typed designation yet** (unlike
    mct_sidc_svg(), see stabilised_point_size_expression()) - a
    genuinely separate mechanism tightly coupled to that function's
    own call shape, not extended here for this first pass. A typed
    designation may shrink the icon slightly, matching this project's
    own pre-2026-08-13 NATO behaviour; worth revisiting once this
    layer is otherwise proven out.
    """

    if len(values) < 2:
        return "Need at least an affiliation and an entity"

    affiliation = str(values[0])
    entity = str(values[1])
    echelon = str(values[2]) if len(values) > 2 and values[2] else "unspecified"
    status = str(values[3]) if len(values) > 3 and values[3] else "present"
    designation = values[4] if len(values) > 4 else None
    combined_arms = bool(values[5]) if len(values) > 5 and values[5] else False

    try:

        svg = render_nonnato_unit_svg(
            affiliation,
            entity,
            echelon=echelon,
            status=status,
            designation=designation,
            combined_arms=combined_arms,
        )

    except KeyError as error:

        # Matches mct_build_sidc()'s own convention (see that
        # function): an invalid attribute value returns readable error
        # text through the expression rather than raising out of a
        # renderer callback, which QGIS would otherwise surface as a
        # much less useful generic evaluation failure.
        return str(error)

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


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
    Units-only).

    Arguments, the second optional: affiliation, entity, designation
    (default none).
    """

    if len(values) < 2:
        return "Need at least an affiliation and an entity"

    affiliation = str(values[0])
    entity = str(values[1])
    designation = values[2] if len(values) > 2 else None

    try:

        svg = render_nonnato_equipment_svg(
            affiliation, entity, designation=designation
        )

    except KeyError as error:

        return str(error)

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_nonnato_sigint_svg',
    group='Military Cartography Tools'
)
def mct_nonnato_sigint_svg(values, feature=None, parent=None):

    """
    "base64:<...>" for a non-NATO Land SIGINT feature - mirrors
    mct_nonnato_equipment_svg()'s own role but built around
    render_nonnato_sigint_svg() instead: no echelon/status/
    combined_arms, same reasoning as Equipment (see that function's own
    docstring), and no dimension field either, since Land is the only
    dimension in scope.

    Arguments, the second optional: affiliation, entity, designation
    (default none).
    """

    if len(values) < 2:
        return "Need at least an affiliation and an entity"

    affiliation = str(values[0])
    entity = str(values[1])
    designation = values[2] if len(values) > 2 else None

    try:

        svg = render_nonnato_sigint_svg(
            affiliation, entity, designation=designation
        )

    except KeyError as error:

        return str(error)

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_nonnato_booby_trap_svg',
    group='Military Cartography Tools'
)
def mct_nonnato_booby_trap_svg(values, feature=None, parent=None):

    """
    "base64:<...>" for the Control Measure Point's own Booby Trap - a
    fully custom icon (see booby_trap_control_measure_svg()'s own
    docstring), not routed through mct_sidc_svg()/milsymbol at all.
    Fixed MINE_GREEN, no arguments needed - unlike every other
    mct_nonnato_*_svg() function, this one entity's colour never varies
    by affiliation, matching every other mine-family icon's own
    convention.
    """

    svg = booby_trap_control_measure_svg()

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


_FUNCTIONS = [
    mct_nonnato_unit_svg,
    mct_nonnato_equipment_svg,
    mct_nonnato_sigint_svg,
    mct_nonnato_booby_trap_svg,
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
