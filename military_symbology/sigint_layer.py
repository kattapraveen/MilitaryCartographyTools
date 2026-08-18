# -*- coding: utf-8 -*-

"""
Builds the "SIGINT" point layer - MIL-STD-2525D
Appendix J (Signals Intelligence Symbols), symbol sets "50" through "54"
(Table A-III / Table J-II's own SymbolSetCode column).

Structurally different from every appendix built so far (B-G): SIGINT's
own four entities (Signal Intercept, Communications, Jammer, Radar) are
identical across FIVE symbol sets - Space (50), Air (51), Land (52), Sea
Surface (53), Subsurface (54) - chosen by which "dimension" the SIGINT
platform is actually in (J.5.3.3: "A SIGINT symbol may be in the space,
air, land, sea surface, or subsurface dimension... that symbol shall
follow the amplifier requirements as stated in [that] appendix"), not by
a different entity code per dimension the way every other appendix
works. This is exactly the case _point_symbol_layer.py's
dimension_labels/dimension_symbol_sets mechanism (added alongside this
layer) exists for - a small, fixed "Dimension" field driving a CASE
expression on symbol_set, instead of either a whole separate layer per
dimension (needless duplication for a 4-entity vocabulary) or a
ValueRelation cascading dropdown (the exact mechanism already retired
from unit_layer.py for its own crash risk).

No echelon/headquarters/sector 2 modifier fields. J.5.3.3's own
cross-reference to "the amplifier requirements as stated in [the
matching] appendix" would suggest these SHOULD vary per dimension (e.g.
Echelon for a Land SIGINT symbol) - but which of Appendix D's own four
Land layers' amplifier rules would even apply to a Land-dimension SIGINT
entity is genuinely ambiguous from the appendix's own text (Land itself
splits Unit/Civilian/Equipment/Installation, each with different
fields), so this plugin deliberately does NOT attempt to fabricate a
per-dimension conditional field set - a known, documented simplification
rather than a guessed doctrinal rule, the same kind of restriction this
project already doesn't enforce elsewhere (e.g. which sector modifier
pairs with which entity). Sector 1 modifiers ARE built (the FULL
64-entry vocabulary Table J-III actually defines - see sidc.py's own
comment on MODIFIERS["sigint_space"] for the one excluded milsymbol-only
code); there is no sector 2 at all (J.5.3.2's own text: "There are no
sector 2 modifiers in SIGINT").

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


OUTPUT_LAYER_NAME = "SIGINT"

DEFAULT_ENTITY = "radar"

DEFAULT_DIMENSION = "air"

_ENTITY_LABELS = {
    "signal_intercept": "Signal Intercept (Generic)",
    "communications": "Communications",
    "jammer": "Jammer",
    "radar": "Radar",
}

_DIMENSION_LABELS = {
    "space": "Space",
    "air": "Air",
    "land": "Land",
    "sea_surface": "Sea Surface",
    "subsurface": "Subsurface",
}

_DIMENSION_SYMBOL_SETS = {
    "space": "sigint_space",
    "air": "sigint_air",
    "land": "sigint_land",
    "sea_surface": "sigint_sea_surface",
    "subsurface": "sigint_subsurface",
}

_SECTOR1_LABELS = {
    "anti_aircraft_fire_control": "Anti-Aircraft Fire Control",
    "airborne_search_and_bombing": "Airborne Search and Bombing",
    "airborne_intercept": "Airborne Intercept",
    "altimeter": "Altimeter",
    "airborne_reconnaissance_and_mapping": "Airborne Reconnaissance and Mapping",
    "air_traffic_control": "Air Traffic Control",
    "beacon_transponder_not_iff": "Beacon Transponder (Not IFF)",
    "battlefield_surveillance": "Battlefield Surveillance",
    "controlled_approach": "Controlled Approach",
    "controlled_intercept": "Controlled Intercept",
    "cellular_mobile": "Cellular/Mobile",
    "coastal_surveillance": "Coastal Surveillance",
    "decoy_mimic": "Decoy/Mimic",
    "data_transmission": "Data Transmission",
    "earth_surveillance": "Earth Surveillance",
    "early_warning": "Early Warning",
    "fire_control": "Fire Control",
    "ground_mapping": "Ground Mapping",
    "height_finding": "Height Finding",
    "harbor_surveillance": "Harbor Surveillance",
    "identification_friend_or_foe_interrogator": "Identification, Friend or Foe (Interrogator)",
    "instrument_landing_system": "Instrument Landing System",
    "ionospheric_sounding": "Ionospheric Sounding",
    "identification_friend_or_foe_transponder": "Identification, Friend or Foe (Transponder)",
    "barrage_jammer": "Barrage Jammer",
    "click_jammer": "Click Jammer",
    "deceptive_jammer": "Deceptive Jammer",
    "frequency_swept_jammer": "Frequency Swept Jammer",
    "jammer_general": "Jammer (General)",
    "noise_jammer": "Noise Jammer",
    "pulsed_jammer": "Pulsed Jammer",
    "repeater_jammer": "Repeater Jammer",
    "spot_noise_jammer": "Spot Noise Jammer",
    "transponder_jammer": "Transponder Jammer",
    "missile_acquisition": "Missile Acquisition",
    "missile_control": "Missile Control",
    "missile_downlink": "Missile Downlink",
    "meteorological": "Meteorological",
    "multi_function": "Multi-Function",
    "missile_guidance": "Missile Guidance",
    "missile_homing": "Missile Homing",
    "missile_tracking": "Missile Tracking",
    "navigational_general": "Navigational/General",
    "navigational_distance_measuring_equipment": "Navigational/Distance Measuring Equipment",
    "navigation_terrain_following": "Navigation/Terrain Following",
    "navigational_weather_avoidance": "Navigational/Weather Avoidance",
    "omni_line_of_sight_los": "Omni-Line of Sight (LOS)",
    "proximity_use": "Proximity Use",
    "point_to_point_line_of_sight_los": "Point-To-Point Line of Sight (LOS)",
    "instrumentation": "Instrumentation",
    "range_only": "Range Only",
    "sonobuoy": "Sonobuoy",
    "satellite_downlink": "Satellite Downlink",
    "space": "Space",
    "surface_search": "Surface Search",
    "shell_tracking": "Shell Tracking",
    "satellite_uplink": "Satellite Uplink",
    "target_acquisition": "Target Acquisition",
    "target_illumination": "Target Illumination",
    "tropospheric_scatter": "Tropospheric Scatter",
    "target_tracking": "Target Tracking",
    "unknown": "Unknown",
    "video_remoting": "Video Remoting",
    "experimental": "Experimental",
}


def add_sigint_layer(iface, edition=None):

    """
    Add the "SIGINT" layer - warns and does nothing
    if one already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        OUTPUT_LAYER_NAME,
        # The literal fallback symbol_set - never actually used once the
        # "dimension" field has a real value (its default is set below),
        # but build_single_domain_point_layer() always needs one.
        "sigint_air",
        _ENTITY_LABELS,
        DEFAULT_ENTITY,
        include_echelon=False,
        include_headquarters=False,
        sector1_labels=_SECTOR1_LABELS,
        dimension_labels=_DIMENSION_LABELS,
        dimension_symbol_sets=_DIMENSION_SYMBOL_SETS,
        default_dimension=DEFAULT_DIMENSION,
        edition=edition,
    )
