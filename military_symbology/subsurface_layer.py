# -*- coding: utf-8 -*-

"""
Builds two "Tactical Graphics - Subsurface" / "Tactical Graphics - Mine
Warfare" point layers - MIL-STD-2525D Appendix F (Subsurface Symbols),
split per its own two sections (F.6 Subsurface Unit/Equipment/
Installation, symbol set "35"; F.7 Mine Warfare, symbol set "36" - Table
A-III). Two separate layers, not merged - Mine Warfare's own 64-entity
vocabulary is far too large to fold into a companion the way Space/Air
Missile's single entity was; this mirrors Land's "several genuinely
distinct layers under one action" pattern instead.

Subsurface ("subsurface" in sidc.py) moved here 2026-08-08 from
military_symbology/unit_layer.py, which used to share it across a
cascading multi-domain dropdown with sea_surface/air/ground_unit before
each of those moved to its own dedicated layer in turn -
unit_layer.py itself is retired now that subsurface was its last
remaining domain (see this session's roadmap entry for the full
history).

**This is where the user's originally-reported bug lived**: "Subsurface
- Military Generic is in Air, Sea Surface [but not for Subsurface]".
Investigated directly - `ENTITIES["subsurface"]["military"]` ("110000")
was already correct and matches subsurface.js's own "SU.IC.MILITARY"
exactly (confirmed by a full parse of the source, not a spot check); the
actual root cause was almost certainly `unit_layer.py`'s old
ValueRelation-based cascading "Entity" dropdown, which that module's own
docstring already flagged as having a confirmed native-crash risk during
development. Resolved structurally, not by changing this code: Subsurface
now has its own dedicated layer with a plain ValueMap dropdown, no
cascading, no shared-layer entity-collision risk at all.

No echelon or headquarters fields - Appendix F's own amplifier table
(Table F-II) lists neither, same finding as every icon-based appendix
checked so far.

Entity vocabulary: `ENTITIES["subsurface"]` (22 entities) and
`ENTITIES["mine_warfare"]` (64 entities) are both the FULL vocabulary
from milsymbol-3.0.4's own subsurface.js/minewarfare.js - both small
enough for full coverage (same policy as Sea Surface). Mine Warfare's
own MILCO (Mine-Like Contact) entries have real confidence-level (1-5)
sub-variants for each position (general/bottom/moored/floating) - the
same kind of systematic sub-code axis Land Equipment's light/medium/
heavy variants turned out to be - caught here up front by the same full
multi-line-aware parse, not missed the way it was there.

Subsurface's own sector 1/2 modifiers (`MODIFIERS["subsurface"]`, 22 +
17 codes) are also fully built, same reasoning as Sea Surface's. Mine
Warfare has NO sector modifiers at all - milsymbol's own minewarfare.js
source has zero sIdm1/sIdm2 entries, not a curation choice.

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


SUBSURFACE_LAYER_NAME = "Tactical Graphics - Subsurface"

MINE_WARFARE_LAYER_NAME = "Tactical Graphics - Mine Warfare"

DEFAULT_SUBSURFACE_ENTITY = "submarine"

DEFAULT_MINE_WARFARE_ENTITY = "sea_mine"

_SUBSURFACE_ENTITY_LABELS = {
    "military": "Military (Generic)",
    "submarine": "Submarine",
    "submarine_surfaced": "Submarine, Surfaced",
    "submarine_snorkeling": "Submarine, Snorkeling",
    "submarine_bottomed": "Submarine, Bottomed",
    "other_submersible": "Other Submersible",
    "non_submarine": "Non-Submarine",
    "autonomous_underwater_vehicle": "Autonomous Underwater Vehicle (AUV/UUV)",
    "diver_military": "Diver, Military",
    "civilian": "Civilian (Generic)",
    "submersible_civilian": "Submersible, Civilian",
    "autonomous_underwater_vehicle_civilian": "Autonomous Underwater Vehicle, Civilian",
    "diver_civilian": "Diver, Civilian",
    "underwater_weapon": "Underwater Weapon (Generic)",
    "torpedo": "Torpedo",
    "improvised_explosive_device": "Improvised Explosive Device (IED)",
    "underwater_decoy": "Underwater Decoy",
    "echo_tracker_classifier": "Echo Tracker Classifier (ETC)/Possible Contact (POSCON)",
    "fused_track": "Fused Track",
    "manual_track": "Manual Track",
    "seabed_installation_military": "Seabed Installation, Man-Made, Military",
    "seabed_installation_non_military": "Seabed Installation, Man-Made, Non-Military",
}

_SUBSURFACE_SECTOR1_LABELS = {
    "antisubmarine_warfare": "Antisubmarine Warfare",
    "auxiliary": "Auxiliary",
    "command_and_control": "Command and Control",
    "intelligence_surveillance_reconnaissance": "Intelligence, Surveillance, Reconnaissance",
    "mine_countermeasures": "Mine Countermeasures",
    "mine_warfare": "Mine Warfare",
    "surface_warfare": "Surface Warfare",
    "attack": "Attack",
    "ballistic_missile": "Ballistic Missile",
    "guided_missile": "Guided Missile",
    "other_guided_missiles_point_defence": "Other Guided Missiles (Point Defence)",
    "special_operations_force": "Special Operations Force",
    "possible_submarine_low_1": "Possible Submarine - Low 1",
    "possible_submarine_low_2": "Possible Submarine - Low 2",
    "possible_submarine_high_3": "Possible Submarine - High 3",
    "possible_submarine_high_4": "Possible Submarine - High 4",
    "probable_submarine": "Probable Submarine",
    "certain_submarine": "Certain Submarine",
    "anti_torpedo_torpedo": "Anti-Torpedo Torpedo",
    "hijacking_hijacked": "Hijacking/Hijacked",
    "hijacker": "Hijacker",
    "cyberspace": "Cyberspace",
}

_SUBSURFACE_SECTOR2_LABELS = {
    "air_independent_propulsion": "Air Independent Propulsion",
    "diesel_propulsion": "Diesel Propulsion",
    "diesel_type_1": "Diesel - Type 1",
    "diesel_type_2": "Diesel - Type 2",
    "diesel_type_3": "Diesel - Type 3",
    "nuclear_powered": "Nuclear Powered",
    "nuclear_type_1": "Nuclear - Type 1",
    "nuclear_type_2": "Nuclear - Type 2",
    "nuclear_type_3": "Nuclear - Type 3",
    "nuclear_type_4": "Nuclear - Type 4",
    "nuclear_type_5": "Nuclear - Type 5",
    "nuclear_type_6": "Nuclear - Type 6",
    "nuclear_type_7": "Nuclear - Type 7",
    "autonomous_control": "Autonomous Control",
    "remotely_piloted": "Remotely Piloted",
    "expendable": "Expendable",
    "cyberspace": "Cyberspace",
}

_MINE_WARFARE_ENTITY_LABELS = {
    "sea_mine": "Sea Mine (Generic)",
    "sea_mine_bottom": "Sea Mine - Bottom",
    "sea_mine_moored": "Sea Mine - Moored",
    "sea_mine_floating": "Sea Mine - Floating",
    "sea_mine_rising": "Sea Mine - Rising",
    "sea_mine_other_position": "Sea Mine (In Other Position)",
    "sea_mine_kingfisher": "Sea Mine - Kingfisher",
    "sea_mine_small_object": "Sea Mine - Small Object",
    "sea_mine_exercise": "Sea Mine, Exercise Mine",
    "sea_mine_exercise_bottom": "Sea Mine, Exercise Mine - Bottom",
    "sea_mine_exercise_moored": "Sea Mine, Exercise Mine - Moored",
    "sea_mine_exercise_floating": "Sea Mine, Exercise Mine - Floating",
    "sea_mine_exercise_rising": "Sea Mine, Exercise Mine - Rising",
    "sea_mine_neutralized": "Sea Mine, Neutralized",
    "sea_mine_neutralized_bottom": "Sea Mine, Neutralized - Bottom",
    "sea_mine_neutralized_moored": "Sea Mine, Neutralized - Moored",
    "sea_mine_neutralized_floating": "Sea Mine, Neutralized - Floating",
    "sea_mine_neutralized_rising": "Sea Mine, Neutralized - Rising",
    "sea_mine_other_position_neutralized": "Sea Mine (In Other Position), Neutralized",
    "unexploded_explosive_ordnance": "Unexploded Explosive Ordnance",
    "sea_mine_decoy": "Sea Mine Decoy (Generic)",
    "sea_mine_decoy_bottom_ground": "Sea Mine Decoy, Bottom/Ground",
    "sea_mine_decoy_moored": "Sea Mine Decoy, Moored",
    "sea_mine_milco": "Sea Mine MILCO (Mine-Like Contact)",
    "sea_mine_milco_confidence_1": "Sea Mine MILCO - Confidence Level 1",
    "sea_mine_milco_confidence_2": "Sea Mine MILCO - Confidence Level 2",
    "sea_mine_milco_confidence_3": "Sea Mine MILCO - Confidence Level 3",
    "sea_mine_milco_confidence_4": "Sea Mine MILCO - Confidence Level 4",
    "sea_mine_milco_confidence_5": "Sea Mine MILCO - Confidence Level 5",
    "sea_mine_milco_bottom": "Sea Mine MILCO - Bottom",
    "sea_mine_milco_bottom_confidence_1": "Sea Mine MILCO - Bottom, Confidence Level 1",
    "sea_mine_milco_bottom_confidence_2": "Sea Mine MILCO - Bottom, Confidence Level 2",
    "sea_mine_milco_bottom_confidence_3": "Sea Mine MILCO - Bottom, Confidence Level 3",
    "sea_mine_milco_bottom_confidence_4": "Sea Mine MILCO - Bottom, Confidence Level 4",
    "sea_mine_milco_bottom_confidence_5": "Sea Mine MILCO - Bottom, Confidence Level 5",
    "sea_mine_milco_moored": "Sea Mine MILCO - Moored",
    "sea_mine_milco_moored_confidence_1": "Sea Mine MILCO - Moored, Confidence Level 1",
    "sea_mine_milco_moored_confidence_2": "Sea Mine MILCO - Moored, Confidence Level 2",
    "sea_mine_milco_moored_confidence_3": "Sea Mine MILCO - Moored, Confidence Level 3",
    "sea_mine_milco_moored_confidence_4": "Sea Mine MILCO - Moored, Confidence Level 4",
    "sea_mine_milco_moored_confidence_5": "Sea Mine MILCO - Moored, Confidence Level 5",
    "sea_mine_milco_floating": "Sea Mine MILCO - Floating",
    "sea_mine_milco_floating_confidence_1": "Sea Mine MILCO - Floating, Confidence Level 1",
    "sea_mine_milco_floating_confidence_2": "Sea Mine MILCO - Floating, Confidence Level 2",
    "sea_mine_milco_floating_confidence_3": "Sea Mine MILCO - Floating, Confidence Level 3",
    "sea_mine_milco_floating_confidence_4": "Sea Mine MILCO - Floating, Confidence Level 4",
    "sea_mine_milco_floating_confidence_5": "Sea Mine MILCO - Floating, Confidence Level 5",
    "sea_mine_milec": "Sea Mine MILEC",
    "sea_mine_milec_bottom": "Sea Mine MILEC - Bottom",
    "sea_mine_milec_moored": "Sea Mine MILEC - Moored",
    "sea_mine_milec_floating": "Sea Mine MILEC - Floating",
    "sea_mine_negative_reacquisition": "Sea Mine, Negative Reacquisition",
    "sea_mine_negative_reacquisition_bottom": "Sea Mine, Negative Reacquisition - Bottom",
    "sea_mine_negative_reacquisition_moored": "Sea Mine, Negative Reacquisition - Moored",
    "sea_mine_negative_reacquisition_floating": "Sea Mine, Negative Reacquisition - Floating",
    "sea_mine_general_obstructor": "Sea Mine, General Obstructor",
    "sea_mine_general_obstructor_neutralized": "Sea Mine, General Obstructor, Neutralized",
    "sea_mine_anchor": "Sea Mine, Mine Anchor",
    "sea_mine_non_mine_like_contact": "Sea Mine, Non-Mine, Mine-Like Contact",
    "sea_mine_non_mine_like_contact_bottom": "Sea Mine, Non-Mine, Mine-Like Contact - Bottom",
    "sea_mine_non_mine_like_contact_moored": "Sea Mine, Non-Mine, Mine-Like Contact - Moored",
    "sea_mine_non_mine_like_contact_floating": "Sea Mine, Non-Mine, Mine-Like Contact - Floating",
    "environmental_report_location": "Environmental Report Location",
    "dive_report_location": "Dive Report Location",
}


def add_subsurface_layer(iface):

    """
    Add the "Tactical Graphics - Subsurface" layer - warns and does
    nothing if one already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        SUBSURFACE_LAYER_NAME,
        "subsurface",
        _SUBSURFACE_ENTITY_LABELS,
        DEFAULT_SUBSURFACE_ENTITY,
        include_echelon=False,
        include_headquarters=False,
        sector1_labels=_SUBSURFACE_SECTOR1_LABELS,
        sector2_labels=_SUBSURFACE_SECTOR2_LABELS,
    )


def add_mine_warfare_layer(iface):

    """Add the "Tactical Graphics - Mine Warfare" layer - same guard."""

    return add_single_domain_point_layer(
        iface,
        MINE_WARFARE_LAYER_NAME,
        "mine_warfare",
        _MINE_WARFARE_ENTITY_LABELS,
        DEFAULT_MINE_WARFARE_ENTITY,
        include_echelon=False,
        include_headquarters=False,
    )


def add_subsurface_layers(iface):

    """
    Add both Appendix F layers (Subsurface, Mine Warfare) in one call -
    the toolbar action's own callback. Each has its own already-exists
    guard, so calling this again only adds whichever is still missing.
    Returns a dict of {layer_name: layer_or_None}.
    """

    return {
        SUBSURFACE_LAYER_NAME: add_subsurface_layer(iface),
        MINE_WARFARE_LAYER_NAME: add_mine_warfare_layer(iface),
    }
