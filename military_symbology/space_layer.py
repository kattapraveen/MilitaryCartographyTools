# -*- coding: utf-8 -*-

"""
Builds the "Tactical Graphics - Space" point layer - MIL-STD-2525D
Appendix B (Space Symbols), covering both of its sections in one layer:
B.6 Space Equipment and Platform Symbols (symbol set "05") and B.7 Space
Missile Symbols (symbol set "06" - Table A-III). Space Missile has only
one entity at this plugin's current level of coverage (no sector
modifiers exposed for any symbol set yet - see sidc.py), so rather than
give it a whole second layer for one entity, its "missile" entity is
folded straight into this layer's own entity dropdown via
_point_symbol_layer.py's entity_symbol_set_overrides mechanism, which
resolves it to symbol set "06" instead of this layer's default "05" only
for that one entity.

Entity vocabulary is military_symbology/sidc.py's ENTITIES["space"]/
["space_missile"] - see that module for sourcing (milsymbol.js's own
space.js/spacemissile.js, cross-checked against the standard's own
Table B-III).

No echelon or headquarters fields - Appendix B's own amplifier table
(Table B-II) lists neither Field B (Echelon) nor Field S (Headquarters
Staff Indicator) for space symbols at all, unlike land units.

Sector 1/2 modifiers (added 2026-08-08, alongside the shared factory's
own modifier support) - _SECTOR1_LABELS/_SECTOR2_LABELS are each the
UNION of sidc.py's MODIFIERS["space"] and MODIFIERS["space_missile"]
(orbit type/sensor type for Space Equipment, missile class/range for
Space Missile) - see build_single_domain_point_layer()'s own docstring
for why a merged layer needs the union rather than just its default
symbol_set's own vocabulary, and the failure mode if an incompatible
entity/modifier pair is chosen anyway.

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


OUTPUT_LAYER_NAME = "Tactical Graphics - Space"

DEFAULT_ENTITY = "satellite"

# The one entity that resolves to a different symbol_set (Space Missile,
# "06") than this layer's own default ("05", Space Equipment/Platform) -
# see this module's own docstring.
_ENTITY_SYMBOL_SET_OVERRIDES = {
    "missile": "space_missile",
}

# Display labels - kept separate from sidc.py's own vocabulary dicts,
# which are the data model (real SIDC component codes), not
# presentation text. Mirrors unit_layer.py's own _ENTITY_LABELS_BY_
# SYMBOL_SET convention.
_ENTITY_LABELS = {
    "military": "Military (Generic)",
    "space_vehicle": "Space Vehicle",
    "re_entry_vehicle": "Re-Entry Vehicle",
    "planet_lander": "Planet Lander",
    "orbiter_shuttle": "Orbiter/Shuttle",
    "capsule": "Capsule",
    "satellite_general": "Satellite, General",
    "satellite": "Satellite",
    "antisatellite_weapon": "Antisatellite Weapon",
    "astronomical_satellite": "Astronomical Satellite",
    "biosatellite": "Biosatellite",
    "communications_satellite": "Communications Satellite",
    "earth_observation_satellite": "Earth Observation Satellite",
    "miniaturized_satellite": "Miniaturized Satellite",
    "navigational_satellite": "Navigational Satellite",
    "reconnaissance_satellite": "Reconnaissance Satellite",
    "space_station": "Space Station",
    "tethered_satellite": "Tethered Satellite",
    "weather_satellite": "Weather Satellite",
    "space_launch_vehicle": "Space Launch Vehicle",
    "civilian": "Civilian (Generic)",
    "civilian_orbiter_shuttle": "Civilian Orbiter/Shuttle",
    "civilian_capsule": "Civilian Capsule",
    "civilian_satellite": "Civilian Satellite",
    "civilian_astronomical_satellite": "Civilian Astronomical Satellite",
    "civilian_biosatellite": "Civilian Biosatellite",
    "civilian_communications_satellite": "Civilian Communications Satellite",
    "civilian_earth_observation_satellite": "Civilian Earth Observation Satellite",
    "civilian_miniaturized_satellite": "Civilian Miniaturized Satellite",
    "civilian_navigational_satellite": "Civilian Navigational Satellite",
    "civilian_space_station": "Civilian Space Station",
    "civilian_tethered_satellite": "Civilian Tethered Satellite",
    "civilian_weather_satellite": "Civilian Weather Satellite",
    "civilian_planetary_lander": "Civilian Planetary Lander",
    "civilian_space_vehicle": "Civilian Space Vehicle",
    "manual_track": "Manual Track",
    "missile": "Missile",
}

# Sector 1 modifier - union of MODIFIERS["space"]["sector1"] (orbit
# type) and MODIFIERS["space_missile"]["sector1"] (missile class).
_SECTOR1_LABELS = {
    "low_earth_orbit": "Low Earth Orbit (LEO)",
    "medium_earth_orbit": "Medium Earth Orbit (MEO)",
    "high_earth_orbit": "High Earth Orbit (HEO)",
    "geosynchronous_orbit": "Geosynchronous Orbit (GSO)",
    "geostationary_orbit": "Geostationary Orbit (GO)",
    "molniya_orbit": "Molniya Orbit (MO)",
    "cyberspace": "Cyberspace",
    "ballistic": "Ballistic",
    "space": "Space",
    "interceptor": "Interceptor",
    "hypersonic": "Hypersonic",
}

# Sector 2 modifier - union of MODIFIERS["space"]["sector2"] (sensor
# type) and MODIFIERS["space_missile"]["sector2"] (missile range class).
_SECTOR2_LABELS = {
    "optical": "Optical",
    "infrared": "Infrared",
    "radar": "Radar",
    "signals_intelligence": "Signals Intelligence (SIGINT)",
    "cyberspace": "Cyberspace",
    "electromagnetic_warfare": "Electromagnetic Warfare (ASAT)",
    "high_power_microwave": "High Power Microwave",
    "laser": "Laser",
    "mine": "Mine",
    "maintenance": "Maintenance",
    "refuel": "Refuel",
    "tug": "Tug",
    "short_range": "Short Range",
    "medium_range": "Medium Range",
    "intermediate_range": "Intermediate Range",
    "long_range": "Long Range",
    "intercontinental": "Intercontinental",
    "arrow": "Arrow",
    "ground_based_interceptor": "Ground-Based Interceptor (GBI)",
    "patriot": "Patriot",
    "standard_missile_terminal_phase": "Standard Missile - Terminal Phase (SM-T)",
    "standard_missile_3": "Standard Missile - 3 (SM-3)",
    "terminal_high_altitude_area_defense": "Terminal High-Altitude Area Defense (THAAD)",
    "space": "Space",
    "close_range": "Close Range",
    "debris": "Debris",
    "unknown": "Unknown",
}


def add_space_layer(iface):

    """
    Add the "Tactical Graphics - Space" layer (Space Equipment/Platform
    plus the single Space Missile entity) - warns and does nothing if
    one already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        OUTPUT_LAYER_NAME,
        "space",
        _ENTITY_LABELS,
        DEFAULT_ENTITY,
        entity_symbol_set_overrides=_ENTITY_SYMBOL_SET_OVERRIDES,
        include_echelon=False,
        include_headquarters=False,
        sector1_labels=_SECTOR1_LABELS,
        sector2_labels=_SECTOR2_LABELS,
    )
