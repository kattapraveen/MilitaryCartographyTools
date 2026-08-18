# -*- coding: utf-8 -*-

"""
Builds the "Sea Surface" point layer - MIL-STD-2525D
Appendix E (Sea Surface Symbols), symbol set "30" (Table A-III). No
missile-family companion to fold in here, unlike Space/Air - Table A-III
has no separate "Sea Surface Missile" symbol set, so this is a single
layer.

Moved 2026-08-08 from military_symbology/unit_layer.py, which used to
share sea_surface across a cascading multi-domain dropdown with
subsurface (and, previously, ground_unit/air before their own
mini-phases split them out) - see that module's own docstring for what's
left there (only subsurface now, pending Appendix F).

No echelon or headquarters fields - Appendix E's own amplifier table
(Table E-II) lists neither Field B (Echelon) nor Field S (Headquarters
Staff Indicator), same finding as every icon-based appendix so far.

Entity vocabulary is sidc.py's ENTITIES["sea_surface"] - the FULL
93-entity vocabulary from milsymbol-3.0.4's own sea.js (not a curated
subset - Sea Surface's own source is small enough that full coverage was
the more consistent choice this time, avoiding a repeat of the Land
Equipment/Installation gap the user caught). Includes Table E-VI's "Own
Ship" (150000 - Combat Information Center-internal, friend-only) and
Table E-VII's "Fused Track" (160000 - a track still being classified,
always pending status - this plugin doesn't enforce that pairing, same
"amplifier restrictions aren't enforced in code" pattern as sector 2
modifiers not being blocked for civilian entities either).

Sector 1/2 modifiers ARE built here (sidc.py's MODIFIERS["sea_surface"],
25 sector 1 + 16 sector 2 codes, also the FULL vocabulary) - Sea
Surface's own modifier tables are compact enough (unlike Land's 50+ per
sector) that there was no reason to defer them the way Land's were.

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


OUTPUT_LAYER_NAME = "Sea Surface"

DEFAULT_ENTITY = "frigate"

_ENTITY_LABELS = {
    "military": "Military (Generic)",
    "combatant": "Combatant (Generic)",
    "carrier": "Carrier",
    "surface_combatant_line": "Surface Combatant, Line",
    "battleship": "Battleship",
    "cruiser_guided_missile": "Cruiser, Guided Missile",
    "destroyer": "Destroyer",
    "frigate": "Frigate",
    "corvette": "Corvette",
    "littoral_combatant_ship": "Littoral Combatant Ship",
    "amphibious_warfare_ship": "Amphibious Warfare Ship",
    "amphibious_force_flagship": "Amphibious Force Flagship",
    "amphibious_assault": "Amphibious Assault",
    "amphibious_assault_ship_general": "Amphibious Assault Ship (General)",
    "amphibious_assault_ship_multi_purpose": "Amphibious Assault Ship (Multi-Purpose)",
    "amphibious_assault_ship_helicopter": "Amphibious Assault Ship (Helicopter)",
    "amphibious_transport_dock": "Amphibious Transport, Dock",
    "landing_ship": "Landing Ship",
    "landing_craft": "Landing Craft",
    "mine_warfare_vessel": "Mine Warfare Vessel (Generic)",
    "minelayer": "Minelayer",
    "minesweeper": "Minesweeper",
    "minesweeper_drone": "Minesweeper, Drone",
    "minehunter": "Minehunter",
    "mine_countermeasures": "Mine Countermeasures",
    "mine_countermeasure_support_ship": "Mine Countermeasure Support Ship",
    "patrol": "Patrol (Generic)",
    "patrol_craft": "Patrol Craft",
    "patrol_gun": "Patrol Gun",
    "sea_surface_decoy": "Sea Surface Decoy",
    "unmanned_surface_water_vehicle": "Unmanned Surface Water Vehicle",
    "military_speedboat": "Military Speedboat",
    "military_speedboat_rigid_hull_inflatable_boat": "Military Speedboat (Rigid-Hull Inflatable Boat)",
    "military_jetski": "Military Jetski",
    "navy_task_organization_unit": "Navy Task Organization Unit",
    "navy_task_element": "Navy Task Element",
    "navy_task_force": "Navy Task Force",
    "navy_task_group": "Navy Task Group",
    "navy_task_unit": "Navy Task Unit",
    "convoy": "Convoy",
    "radar": "Radar",
    "noncombatant": "Noncombatant (Generic)",
    "auxiliary_ship": "Auxiliary Ship",
    "ammunition_ship": "Ammunition Ship",
    "stores_ship": "Stores Ship",
    "auxiliary_flag_or_command_ship": "Auxiliary Flag or Command Ship",
    "intelligence_collector": "Intelligence Collector",
    "ocean_research_ship": "Ocean Research Ship",
    "survey_ship": "Survey Ship",
    "hospital_ship": "Hospital Ship",
    "cargo_ship": "Cargo Ship",
    "combat_support_ship_fast": "Combat Support Ship, Fast",
    "oiler_replenishment": "Oiler, Replenishment",
    "repair_ship": "Repair Ship",
    "submarine_tender": "Submarine Tender",
    "tug_ocean_going": "Tug, Ocean Going",
    "service_craft_yard_general": "Service Craft, Yard (General)",
    "barge_not_self_propelled": "Barge, Not Self-Propelled",
    "barge_self_propelled": "Barge, Self-Propelled",
    "tug_harbour": "Tug, Harbour",
    "launch": "Launch",
    "civilian": "Civilian (Generic)",
    "merchant_ship_general": "Merchant Ship (General)",
    "cargo_general": "Cargo (General)",
    "container_ship": "Container Ship",
    "dredge": "Dredge",
    "roll_on_roll_off": "Roll-On/Roll-Off",
    "ferry": "Ferry",
    "heavy_lift": "Heavy Lift",
    "hovercraft": "Hovercraft",
    "merchant_ship_lash_carrier": "Merchant Ship, LASH Carrier (with Barges)",
    "oiler_tanker": "Oiler/Tanker",
    "passenger_ship": "Passenger Ship",
    "tug_ocean_going_civilian": "Tug, Ocean Going (Civilian)",
    "tow": "Tow",
    "transport_ship_hazardous_material": "Transport Ship (Hazardous Material)",
    "junk_dhow": "Junk/Dhow",
    "barge_not_self_propelled_civilian": "Barge, Not Self-Propelled (Civilian)",
    "hospital_ship_civilian": "Hospital Ship (Civilian)",
    "fishing_vessel": "Fishing Vessel (Generic)",
    "drifter": "Drifter",
    "trawler": "Trawler",
    "fishing_vessel_dredge": "Fishing Vessel (Dredge)",
    "law_enforcement_vessel": "Law Enforcement Vessel",
    "leisure_craft_sailing_boat": "Leisure Craft (Sailing Boat)",
    "leisure_craft_motorized": "Leisure Craft (Motorized)",
    "leisure_craft_motorized_rigid_hull_inflatable_boat": "Leisure Craft (Motorized, Rigid-Hull Inflatable Boat)",
    "leisure_craft_motorized_speedboat": "Leisure Craft (Motorized, Speedboat)",
    "leisure_craft_jetski": "Leisure Craft (Jetski)",
    "civilian_unmanned_surface_water_vehicle": "Civilian Unmanned Surface Water Vehicle",
    "own_ship": "Own Ship",
    "fused_track": "Fused Track",
    "manual_track": "Manual Track",
}

_SECTOR1_LABELS = {
    "own_ship": "Own Ship",
    "antiair_warfare": "Antiair Warfare",
    "antisubmarine_warfare": "Antisubmarine Warfare",
    "escort": "Escort",
    "electronic_warfare": "Electronic Warfare",
    "intelligence_surveillance_reconnaissance": "Intelligence, Surveillance, Reconnaissance",
    "mine_countermeasures": "Mine Countermeasures",
    "missile_defense": "Missile Defense",
    "medical": "Medical",
    "mine_warfare": "Mine Warfare",
    "remote_multi_mission_vehicle": "Remote Multi-Mission Vehicle",
    "special_operations_force": "Special Operations Force",
    "surface_warfare": "Surface Warfare",
    "ballistic_missile": "Ballistic Missile",
    "guided_missile": "Guided Missile",
    "other_guided_missile": "Other Guided Missile",
    "torpedo": "Torpedo",
    "drone_equipped": "Drone-Equipped",
    "helicopter_equipped": "Helicopter-Equipped",
    "ballistic_missile_defense_shooter": "Ballistic Missile Defense, Shooter",
    "ballistic_missile_defense_long_range_surveillance_and_track": "Ballistic Missile Defense, Long-Range Surveillance and Track (LRS&T)",
    "sea_base_x_band": "Sea-Base X-Band",
    "hijacking_hijacked": "Hijacking/Hijacked",
    "hijacker": "Hijacker",
    "cyberspace": "Cyberspace",
}

_SECTOR2_LABELS = {
    "nuclear_powered": "Nuclear Powered",
    "heavy": "Heavy",
    "light": "Light",
    "medium": "Medium",
    "dock": "Dock",
    "logistics": "Logistics",
    "tank": "Tank",
    "vehicle": "Vehicle",
    "fast": "Fast",
    "air_cushioned_us": "Air-Cushioned (USA Only)",
    "air_cushioned": "Air-Cushioned",
    "hydrofoil": "Hydrofoil",
    "autonomous_control": "Autonomous Control",
    "remotely_piloted": "Remotely Piloted",
    "expendable": "Expendable",
    "cyberspace": "Cyberspace",
}


def add_sea_surface_layer(iface, edition=None):

    """
    Add the "Sea Surface" layer - warns and does
    nothing if one already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        OUTPUT_LAYER_NAME,
        "sea_surface",
        _ENTITY_LABELS,
        DEFAULT_ENTITY,
        include_echelon=False,
        include_headquarters=False,
        sector1_labels=_SECTOR1_LABELS,
        sector2_labels=_SECTOR2_LABELS,
        edition=edition,
    )
