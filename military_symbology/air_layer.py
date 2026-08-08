# -*- coding: utf-8 -*-

"""
Builds the "Tactical Graphics - Air" point layer - MIL-STD-2525D
Appendix C (Air Symbols), covering both of its sections in one layer:
C.6 Air Equipment and Platform Symbols (symbol set "01") and C.7 Air
Missile Symbols (symbol set "02" - Table A-III). Air Missile has only
one entity at this plugin's current level of coverage (no sector
modifiers exposed for any symbol set yet - see sidc.py), so its
"missile" entity is folded straight into this layer's own entity
dropdown via _point_symbol_layer.py's entity_symbol_set_overrides
mechanism, the same pattern space_layer.py already established for
Space Missile.

No echelon or headquarters fields - Appendix C's own amplifier table
(Table C-II, already read this session) lists neither Field B (Echelon)
nor Field S (Headquarters Staff Indicator) for air symbols, same finding
as Space's own Table B-II.

Entity vocabulary is military_symbology/sidc.py's ENTITIES["air"]/
["air_missile"] - see that module for sourcing (milsymbol.js's own
air.js/airmissile.js, cross-checked against the standard's own Table
C-III).

Sector 1/2 modifiers (added 2026-08-08, alongside the shared factory's
own modifier support) - _SECTOR1_LABELS/_SECTOR2_LABELS are each the
UNION of sidc.py's MODIFIERS["air"] and MODIFIERS["air_missile"] (role/
mission class for Air Equipment, target/range class for Air Missile) -
see space_layer.py's own comment and
build_single_domain_point_layer()'s docstring for why a merged layer
needs the union. A few keys (e.g. "interceptor", "short_range") are
valid AND mean essentially the same thing in both underlying
vocabularies, so they appear once here rather than twice - not a
conflict, since mct_build_sidc() resolves the actual numeric code
against whichever symbol_set the chosen entity maps to.

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


OUTPUT_LAYER_NAME = "Tactical Graphics - Air"

DEFAULT_ENTITY = "fighter"

# The one entity that resolves to a different symbol_set (Air Missile,
# "02") than this layer's own default ("01", Air Equipment/Platform).
_ENTITY_SYMBOL_SET_OVERRIDES = {
    "missile": "air_missile",
}

# Display labels - kept separate from sidc.py's own vocabulary dicts,
# which are the data model (real SIDC component codes), not
# presentation text.
_ENTITY_LABELS = {
    "military": "Military (Generic)",
    "fixed_wing": "Fixed-Wing",
    "medical_evacuation": "Medical Evacuation",
    "attack_strike": "Attack/Strike",
    "bomber": "Bomber",
    "fighter": "Fighter",
    "fighter_bomber": "Fighter/Bomber",
    "cargo": "Cargo",
    "jammer_electronic_countermeasures": "Jammer/Electronic Countermeasures (ECM)",
    "tanker": "Tanker",
    "patrol": "Patrol",
    "reconnaissance": "Reconnaissance",
    "trainer": "Trainer",
    "utility": "Utility",
    "vstol": "VSTOL",
    "airborne_command_post": "Airborne Command Post",
    "airborne_early_warning": "Airborne Early Warning",
    "antisurface_warfare": "Antisurface Warfare",
    "antisubmarine_warfare": "Antisubmarine Warfare",
    "communications": "Communications",
    "combat_search_and_rescue": "Combat Search and Rescue (CSAR)",
    "electronic_support": "Electronic Support",
    "government": "Government",
    "mine_countermeasures": "Mine Countermeasures",
    "personnel_recovery": "Personnel Recovery",
    "search_and_rescue": "Search and Rescue",
    "special_operations_forces": "Special Operations Forces",
    "ultra_light": "Ultra Light",
    "photographic_reconnaissance": "Photographic Reconnaissance",
    "vip": "VIP",
    "suppression_of_enemy_air_defense": "Suppression of Enemy Air Defense (SEAD)",
    "passenger": "Passenger",
    "escort": "Escort",
    "electronic_attack": "Electronic Attack (EA)",
    "military_rotary_wing": "Military Rotary Wing",
    "unmanned_aerial_vehicle": "Unmanned Aerial Vehicle (UAV)",
    "vertical_takeoff_uav": "Vertical-Takeoff UAV (VT-UAV)",
    "military_balloon": "Military Balloon",
    "military_airship": "Military Airship",
    "tethered_lighter_than_air": "Tethered Lighter Than Air",
    "civilian": "Civilian (Generic)",
    "civilian_fixed_wing": "Civilian Fixed-Wing",
    "civilian_rotary_wing": "Civilian Rotary Wing",
    "civilian_unmanned_aerial_vehicle": "Civilian Unmanned Aerial Vehicle",
    "civilian_balloon": "Civilian Balloon",
    "civilian_airship": "Civilian Airship",
    "civilian_tethered_lighter_than_air": "Civilian Tethered Lighter Than Air",
    "civilian_medical_evacuation": "Civilian Medical Evacuation",
    "weapon": "Weapon (Generic)",
    "bomb": "Bomb",
    "underwater_decoy": "Underwater Decoy",
    "manual_track": "Manual Track",
    "missile": "Missile",
}

# Sector 1 modifier - union of MODIFIERS["air"]["sector1"] (role/mission)
# and MODIFIERS["air_missile"]["sector1"] (missile class).
_SECTOR1_LABELS = {
    "attack": "Attack",
    "bomber": "Bomber",
    "cargo": "Cargo",
    "fighter": "Fighter",
    "interceptor": "Interceptor",
    "tanker": "Tanker",
    "utility": "Utility",
    "vstol": "VSTOL",
    "passenger": "Passenger",
    "ultra_light": "Ultra Light",
    "airborne_command_post": "Airborne Command Post",
    "airborne_early_warning": "Airborne Early Warning",
    "government": "Government",
    "medevac": "Medevac",
    "escort": "Escort",
    "jammer_electronic_countermeasures": "Jammer/Electronic Countermeasures (ECM)",
    "patrol": "Patrol",
    "reconnaissance": "Reconnaissance",
    "trainer": "Trainer",
    "photographic": "Photographic",
    "personnel_recovery": "Personnel Recovery",
    "antisubmarine_warfare": "Antisubmarine Warfare",
    "communications": "Communications",
    "electronic_support": "Electronic Support (ES)",
    "mine_countermeasures": "Mine Countermeasures",
    "search_and_rescue": "Search and Rescue",
    "special_operations_forces": "Special Operations Forces",
    "surface_warfare": "Surface Warfare",
    "vip": "VIP",
    "combat_search_and_rescue": "Combat Search and Rescue",
    "suppression_of_enemy_air_defense": "Suppression of Enemy Air Defence",
    "antisurface_warfare": "Antisurface Warfare",
    "fighter_bomber": "Fighter/Bomber",
    "intensive_care": "Intensive Care",
    "electronic_attack": "Electronic Attack (EA)",
    "multimission": "Multimission",
    "hijacking": "Hijacking",
    "asw_helo_lamps": "ASW Helo - LAMPS",
    "asw_helo_sh_60r": "ASW Helo - SH-60R",
    "hijacker": "Hijacker",
    "cyberspace": "Cyberspace",
    "air": "Air",
    "surface": "Surface",
    "subsurface": "Subsurface",
    "space": "Space",
    "anti_ballistic": "Anti-Ballistic",
    "ballistic": "Ballistic",
    "cruise": "Cruise",
    "hypersonic": "Hypersonic",
}

# Sector 2 modifier - union of MODIFIERS["air"]["sector2"] (fuel/range
# class) and MODIFIERS["air_missile"]["sector2"] (target/range class).
_SECTOR2_LABELS = {
    "heavy": "Heavy",
    "medium": "Medium",
    "light": "Light",
    "boom_only": "Boom-Only",
    "drogue_only": "Drogue-Only",
    "boom_and_drogue": "Boom and Drogue",
    "close_range": "Close Range",
    "short_range": "Short Range",
    "medium_range": "Medium Range",
    "long_range": "Long Range",
    "downlinked": "Downlinked",
    "cyberspace": "Cyberspace",
    "air": "Air",
    "surface": "Surface",
    "subsurface": "Subsurface",
    "space": "Space",
    "launched": "Launched",
    "missile": "Missile",
    "patriot": "Patriot",
    "standard_missile_2": "Standard Missile - 2 (SM-2)",
    "standard_missile_6": "Standard Missile - 6 (SM-6)",
    "evolved_sea_sparrow_missile": "Evolved Sea Sparrow Missile (ESSM)",
    "rolling_airframe_missile": "Rolling Airframe Missile (RAM)",
    "intermediate_range": "Intermediate Range",
    "intercontinental": "Intercontinental",
}


def add_air_layer(iface):

    """
    Add the "Tactical Graphics - Air" layer (Air Equipment/Platform plus
    the single Air Missile entity) - warns and does nothing if one
    already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        OUTPUT_LAYER_NAME,
        "air",
        _ENTITY_LABELS,
        DEFAULT_ENTITY,
        entity_symbol_set_overrides=_ENTITY_SYMBOL_SET_OVERRIDES,
        include_echelon=False,
        include_headquarters=False,
        sector1_labels=_SECTOR1_LABELS,
        sector2_labels=_SECTOR2_LABELS,
    )
