# -*- coding: utf-8 -*-

"""
Builds a 20-character MIL-STD-2525D / APP-6D SIDC (Symbol Identification
Code) from named components, rather than requiring a caller to hand-assemble
the raw fixed-width string themselves.

Field positions and codes below are not from the printed standard directly -
they're read straight out of milsymbol.js's own parsing logic
(military_symbology/vendor/milsymbol.js, sourced from
milsymbol-3.0.4/src/numbersidc/metadata.js and
milsymbol-3.0.4/src/ms/symbol/getmetadata.js), since that's the code that
actually has to interpret whatever string we hand it - matching the
library's own source is the only way to be sure our output means what we
intend, rather than trusting a possibly-misremembered field layout.

    position   1-2   version/coding scheme (fixed here at "10" - Warfighting)
    position     3   context ("0" = Reality, fixed here - Exercise/
                     Simulation aren't exposed)
    position     4   affiliation (Standard Identity 2) - see AFFILIATIONS
    positions  5-6   symbol set - see SYMBOL_SETS
    position     7   status - see STATUS
    position     8   headquarters/task force/feint-dummy amplifier -
                     "0" = none, "2" = headquarters (the only two exposed;
                     feint/dummy and task force aren't yet, see ROADMAP)
    positions 9-10   echelon/mobility - see ECHELONS
    positions 11-20  function ID: a 6-character base entity code (see
                     ENTITIES) padded with 4 zeros for the modifier-1/
                     modifier-2 subfields this module doesn't set

Military Cartography Tools
"""


AFFILIATIONS = {
    "unknown": "1",
    "friend": "3",
    "neutral": "4",
    "hostile": "6",
}

STATUS = {
    "present": "0",
    "planned": "1",
}

# Only the two most commonly needed HQ_TASK_FORCE_DUMMY values are exposed -
# headquarters is a modifier applicable to any entity, not a distinct
# entity choice, so it's its own parameter rather than living in ENTITIES.
HEADQUARTERS_CODE = "2"
NO_HEADQUARTERS_CODE = "0"

ECHELONS = {
    "unspecified": "00",
    "team_crew": "11",
    "squad": "12",
    "section": "13",
    "platoon": "14",
    "company": "15",
    "battalion": "16",
    "regiment": "17",
    "brigade": "18",
    "division": "21",
    "corps": "22",
    "army": "23",
}

SYMBOL_SETS = {
    "ground_unit": "10",
}

# Entity base codes (the first 6 characters of the 10-character function-ID
# field), keyed by symbol set - real codes from milsymbol-3.0.4's own
# src/numbersidc/sidc/landunit.js, e.g. sId["121100"] for infantry. A
# curated starting subset per the Phase 10 plan, not the full spec - growing
# this is additive (milsymbol already renders any valid code we build; this
# dict only limits what's reachable through this plugin's own UI).
ENTITIES = {
    "ground_unit": {
        "infantry": "121100",
        "motorized_infantry": "121104",
        "mechanized_infantry": "121102",
        "armor": "120500",
        "reconnaissance": "121300",
        "field_artillery": "130300",
        "engineer": "140700",
    },
}


def build_sidc(
    affiliation,
    entity,
    symbol_set="ground_unit",
    echelon="unspecified",
    status="present",
    headquarters=False,
):

    """
    A 20-character SIDC string for the given components. Raises KeyError
    (with the invalid value's own field name in the message) for any
    unrecognised affiliation/symbol_set/entity/echelon/status - callers
    should validate against this module's own vocabulary dicts before
    calling, rather than relying on typo-tolerant behaviour here.
    """

    if affiliation not in AFFILIATIONS:

        raise KeyError(
            f"Unknown affiliation {affiliation!r} - expected one of "
            f"{sorted(AFFILIATIONS)}"
        )

    if symbol_set not in SYMBOL_SETS:

        raise KeyError(
            f"Unknown symbol_set {symbol_set!r} - expected one of "
            f"{sorted(SYMBOL_SETS)}"
        )

    entities_for_set = ENTITIES[symbol_set]

    if entity not in entities_for_set:

        raise KeyError(
            f"Unknown entity {entity!r} for symbol_set {symbol_set!r} - "
            f"expected one of {sorted(entities_for_set)}"
        )

    if echelon not in ECHELONS:

        raise KeyError(
            f"Unknown echelon {echelon!r} - expected one of "
            f"{sorted(ECHELONS)}"
        )

    if status not in STATUS:

        raise KeyError(
            f"Unknown status {status!r} - expected one of {sorted(STATUS)}"
        )

    version = "10"
    context = "0"
    affiliation_code = AFFILIATIONS[affiliation]
    symbol_set_code = SYMBOL_SETS[symbol_set]
    status_code = STATUS[status]
    hq_code = HEADQUARTERS_CODE if headquarters else NO_HEADQUARTERS_CODE
    echelon_code = ECHELONS[echelon]
    function_id = entities_for_set[entity] + "0000"

    return (
        version
        + context
        + affiliation_code
        + symbol_set_code
        + status_code
        + hq_code
        + echelon_code
        + function_id
    )
