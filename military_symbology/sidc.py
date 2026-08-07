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
    # Confirmed against milsymbol.js's own dimensionMapping (src/
    # numbersidc/metadata.js) - "01" = Air, "30" = Sea (surface), "35" =
    # Subsurface - matching MIL-STD-2525D's own Appendix C/E/F
    # (Air/Sea Surface/Subsurface Symbols), which milsymbol.js already
    # fully renders. Added 2026-08-07 after the user confirmed these
    # were missing entirely (only "ground_unit" existed) while cross-
    # checking Phase 10 against the official standard.
    "air": "01",
    "sea_surface": "30",
    "subsurface": "35",
    # Appendix H's own point-type control measures (checkpoints, contact/
    # decision points, target points, sustainment/supply points, and
    # similar) - a different rendering mechanism from control_measures.py's
    # hand-built line/area symbology (that module covers H's LINE/AREA
    # control measures; this symbol set covers H's POINT ones, which
    # milsymbol.js already renders same as any other symbol set). Added
    # 2026-08-07 - see military_symbology/control_measure_points.py.
    "control_measure": "25",
}

# Entity base codes (the first 6 characters of the 10-character function-ID
# field), keyed by symbol set - real codes from milsymbol-3.0.4's own
# src/numbersidc/sidc/landunit.js, e.g. sId["121100"] for infantry. A
# curated common-vocabulary subset per the Phase 10 plan, not the full
# spec (landunit.js alone has ~140 top-level entities, plus every other
# symbol set) - deliberately excludes the more peripheral administrative
# categories (band, postal, religious support, laundry/bath, and similar)
# and the civilian law-enforcement-agency entries the same symbol set
# also covers (FBI, DEA, Customs, and similar), neither of which read as
# "military formations" in the operational-mapping sense this plugin is
# for. Growing this further is additive (milsymbol already renders any
# valid code we build; this dict only limits what's reachable through
# this plugin's own UI) - organised by the standard functional-area
# breakdown (command/signal, maneuver, fires, air defense, combat
# support, intelligence, combat service support) rather than
# alphabetically, to make it easier to find a related entity nearby.
ENTITIES = {
    "ground_unit": {
        # Command & signal
        "command_and_control": "110000",
        "signal": "111000",
        "liaison": "110500",
        # Maneuver
        "infantry": "121100",
        "motorized_infantry": "121104",
        "mechanized_infantry": "121102",
        "armor": "120500",
        "reconnaissance": "121300",
        "antitank": "120400",
        "combined_arms": "121000",
        "aviation_rotary_wing": "120600",
        "aviation_fixed_wing": "120800",
        "air_assault": "120100",
        "amphibious": "120300",
        "special_forces": "121700",
        "ranger": "122000",
        "sniper": "121500",
        "surveillance": "121600",
        "unmanned_systems": "121900",
        # Fires
        "field_artillery": "130300",
        "field_artillery_self_propelled": "130301",
        "field_artillery_observer": "130400",
        "mortar": "130800",
        "missile": "130700",
        "joint_fire_support": "130500",
        # Air defense
        "air_defense": "130100",
        "air_defense_gun": "130101",
        "air_defense_missile": "130102",
        "air_and_missile_defense": "130103",
        # Combat support
        "engineer": "140700",
        "engineer_mechanized": "140701",
        "cbrn": "140100",
        "explosive_ordnance_disposal": "140800",
        "military_police": "141200",
        "mine_clearing": "141400",
        "search_and_rescue": "141800",
        "security": "141700",
        # Intelligence & electronic warfare
        "military_intelligence": "151000",
        "electronic_warfare": "150500",
        "counter_intelligence": "150200",
        "sensor": "151200",
        # Combat service support
        "sustainment": "160000",
        "maintenance": "161100",
        "medical": "161300",
        "supply": "163400",
        "transportation": "163600",
        "quartermaster": "162900",
        "ordnance": "162300",
        "ammunition": "160400",
        "petroleum_oil_lubricants": "162500",
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/air.js
    # (symbolSet == "01"). Two entries are renamed purely to avoid
    # colliding with ground_unit's own keys in unit_layer.py's combined
    # entity dropdown - "reconnaissance" -> "air_reconnaissance" and
    # "electronic_warfare" -> "airborne_electronic_warfare" (ground_unit
    # already has its own "electronic_warfare" for a land EW unit, a
    # different code entirely) - each pair are unrelated codes in
    # unrelated symbol sets, these are UI-clarity renames only.
    "air": {
        "military": "110000",
        "fixed_wing": "110100",
        "attack": "110102",
        "bomber": "110103",
        "fighter": "110104",
        "fighter_bomber": "110105",
        "cargo": "110107",
        "airborne_electronic_warfare": "110108",
        "tanker": "110109",
        "patrol": "110110",
        "air_reconnaissance": "110111",
        "trainer": "110112",
        "utility": "110113",
        "airborne_early_warning": "110116",
        "antisubmarine_warfare": "110118",
        "medical_evacuation": "110101",
        "combat_search_and_rescue": "110120",
        "special_operations_forces": "110126",
        "rotary_wing": "110200",
        "unmanned_aerial_vehicle": "110300",
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/sea.js
    # (symbolSet == "30").
    "sea_surface": {
        "military": "110000",
        "carrier": "120100",
        "cruiser": "120202",
        "destroyer": "120203",
        "frigate": "120204",
        "corvette": "120205",
        "littoral_combat_ship": "120206",
        "amphibious_assault_ship": "120302",
        "landing_ship": "120307",
        "landing_craft": "120308",
        "minelayer": "120401",
        "minesweeper": "120402",
        "mine_countermeasures_ship": "120405",
        "patrol_craft": "120501",
        "unmanned_surface_vehicle": "120700",
        "auxiliary_ship": "130100",
        "hospital_ship": "130107",
        "cargo_ship": "130108",
        "oiler": "130110",
        "submarine_tender": "130112",
        "tug": "130113",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/subsurface.js (symbolSet == "35").
    "subsurface": {
        "military": "110000",
        "submarine": "110100",
        "submarine_surfaced": "110101",
        "submarine_snorkeling": "110102",
        "other_submersible": "110200",
        "autonomous_underwater_vehicle": "110400",
        "diver_military": "110500",
        "torpedo": "130100",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/control-measure.js (symbolSet == "25"), which
    # has ~260 point-type control measure entries in total - this is a
    # curated subset of ~80, the same "common vocabulary now, growable
    # later" approach as every other symbol set above. Deliberately
    # excludes the ~110 Maritime Control Points entries almost entirely
    # (deeply Navy/ASW-specific jargon - sonobuoy types, acoustic fix
    # types, and similar - not "military cartography" in the general
    # operational-mapping sense this plugin is for, mirroring why
    # ground_unit's own curation above excludes band/postal/religious
    # support), the granular per-nation/per-class supply point variants
    # (NATO/US Class I-X - 16 entries, kept to the two generic ones
    # instead), and a handful of entries that were clearly data-quality
    # artifacts in milsymbol's own source (an empty icon reference, a
    # "FIX TODO" comment left in by its own maintainers).
    "control_measure": {
        # Command and control points
        "unspecified_control_point": "130100",
        "amnesty_point": "130200",
        "checkpoint": "130300",
        "center_of_main_effort": "130400",
        "contact_point": "130500",
        "coordination_point": "130600",
        "decision_point": "130700",
        "distress_call": "130800",
        "entry_control_point": "130900",
        "linkup_point": "131100",
        "passage_point": "131200",
        "point_of_interest": "131300",
        "rally_point": "131400",
        "release_point": "131500",
        "start_point": "131600",
        "special_point": "131700",
        "waypoint": "131800",
        "airfield": "131900",
        "target_handover": "132000",
        "key_terrain": "132100",
        # Maneuver / observation points
        "observation_post": "160100",
        "observation_post_reconnaissance": "160201",
        "observation_post_forward_observer": "160202",
        "observation_post_cbrn": "160203",
        "observation_post_sensor_listening": "160204",
        "observation_post_combat": "160205",
        "target_reference_point": "160300",
        "point_of_departure": "160400",
        # Maritime hazards / reference points
        "distressed_vessel": "218000",
        "downed_aircraft": "218100",
        "iceberg": "218300",
        "oil_rig": "218500",
        "sea_mine_like_contact": "218600",
        # Fires
        "point_target": "240601",
        "nuclear_target": "240602",
        "target_recorded": "240603",
        "fire_support_station": "240900",
        "firing_point": "250100",
        "hide_point": "250200",
        "launch_point": "250300",
        "reload_point": "250400",
        "survey_control_point": "250500",
        # Protection (obstacles, mines, shelters, CBRN events)
        "abatis": "280100",
        "antipersonnel_mine": "280200",
        "antitank_mine": "280300",
        "unspecified_mine": "280600",
        "booby_trap": "280700",
        "engineer_regulating_point": "280800",
        "shelter": "280900",
        "shelter_above_ground": "281000",
        "shelter_below_ground": "281100",
        "fort": "281200",
        "chemical_event": "281300",
        "biological_event": "281400",
        "nuclear_event": "281500",
        "radiological_event": "281700",
        # Sustainment, supply, casualty & personnel handling
        "ambulance_exchange_point": "320100",
        "ammunition_supply_point": "320200",
        "ammunition_transfer_point": "320300",
        "cannibalization_point": "320400",
        "casualty_collection_point": "320500",
        "civilian_collection_point": "320600",
        "detainee_collection_point": "320700",
        "enemy_prisoner_of_war_collection_point": "320800",
        "logistics_release_point": "320900",
        "maintenance_collection_point": "321000",
        "medevac_pickup_point": "321100",
        "rearm_refuel_resupply_point": "321200",
        "refuel_on_the_move_point": "321300",
        "traffic_control_post": "321400",
        "trailer_transfer_point": "321500",
        "unit_maintenance_collection_point": "321600",
        "general_supply_point": "321700",
        "medical_supply_point": "321800",
        # Mission tasks (point form - control_measures.py separately
        # covers the arrow/line-graphic form some of these same task
        # names also take under H.5.26, a different rendering mechanism)
        "destroy_point": "340900",
        "interdict_point": "341400",
        "neutralize_point": "341600",
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
