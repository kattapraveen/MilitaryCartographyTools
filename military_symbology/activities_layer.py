# -*- coding: utf-8 -*-

"""
Builds the "Activities" point layer - MIL-STD-2525D
Appendix G (Activities Symbols), symbol set "40" (Table A-III). A single
layer - Table A-III has no companion symbol set for Activities the way
Space/Air have a Missile counterpart.

No echelon or headquarters fields - Appendix G's own amplifier table
(Table G-II) lists neither Field B (Echelon) nor Field S (Headquarters
Staff Indicator) - Table G-II's own "S" field is actually "Offset
Location Indicator", an unrelated graphic amplifier this plugin doesn't
model, not Field S from Table VII's master list.

Entity vocabulary is sidc.py's ENTITIES["activities"] - the FULL
153-entity vocabulary from milsymbol-3.0.4's own activites.js, cross-
checked against the standard's own Table G-III (printed pages 357-363).
Includes the hierarchy-only parent codes (110000/130000/150000/180000/
etc.) that render frame-only, per that table's own remarks column - see
sidc.py's own comment on ENTITIES["activities"] for detail.

Sector 1 modifiers ARE built here (sidc.py's MODIFIERS["activities"]
["sector1"], 18 codes - the FULL vocabulary Table G-IV actually defines).
There is deliberately NO sector 2 field: Appendix G's own text says so
explicitly ("Note: There are no sector 2 modifiers in activities
symbols.", G.5.3.1 step 3) and Table G-IV itself only ever lists a
sector 1 column - see sidc.py's own comment on MODIFIERS["activities"]
for why the four extra sIdm1 codes and two sIdm2 codes present in
milsymbol's own source were excluded as unsanctioned by the standard.

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


OUTPUT_LAYER_NAME = "Activities"

DEFAULT_ENTITY = "criminal_activity_incident_type"

_ENTITY_LABELS = {
    "criminal_activity_incident": "Criminal Activity/Incident (Generic)",
    "criminal_activity_incident_type": "Criminal Activity Incident",
    "arrest": "Arrest",
    "arson_fire": "Arson/Fire",
    "attempted_criminal_activity": "Attempted Criminal Activity",
    "drive_by_shooting": "Drive-By Shooting",
    "drug_related_activities": "Drug Related Activities",
    "extortion": "Extortion",
    "graffiti": "Graffiti",
    "killing_victim": "Killing Victim",
    "poisoning": "Poisoning",
    "riot": "Riot",
    "booby_trap": "Booby Trap",
    "eviction": "Eviction",
    "black_marketing": "Black Marketing",
    "vandalism_loot_ransack_plunder_sack": "Vandalism/Loot/Ransack/Plunder/Sack",
    "jail_break": "Jail Break",
    "robbery": "Robbery",
    "theft": "Theft",
    "burglary": "Burglary",
    "smuggling": "Smuggling",
    "rock_throwing": "Rock Throwing",
    "dead_body": "Dead Body",
    "sabotage": "Sabotage",
    "threat_of_criminal_activity": "Threat of Criminal Activity",
    "bomb": "Bomb",
    "bomb_threat": "Bomb Threat",
    "ied": "IED",
    "ied_explosion": "IED Explosion",
    "premature_ied_explosion": "Premature IED Explosion",
    "ied_supply_cache": "IED Supply Cache",
    "individual_with_ied": "Individual with IED",
    "shooting": "Shooting",
    "sniping": "Sniping",
    "illegal_drug_operation": "Illegal Drug Operation",
    "drug_trafficking": "Drug Trafficking",
    "drug_laboratory": "Drug Laboratory",
    "explosion": "Explosion",
    "grenade_explosion": "Grenade Explosion",
    "incendiary_explosion": "Incendiary Explosion",
    "mine_explosion": "Mine Explosion",
    "mortar_fire_explosion": "Mortar Fire Explosion",
    "rocket_explosion": "Rocket Explosion",
    "bomb_explosion": "Bomb Explosion",
    "home": "Home",
    "civil_disturbance": "Civil Disturbance",
    "demonstration": "Demonstration",
    "operations": "Operations (Generic)",
    "patrolling": "Patrolling",
    "psychological_operations": "Psychological Operations",
    "radio_and_television_psychological_operations": "Radio and Television Psychological Operations",
    "searching": "Searching",
    "willing_coerced_qualifier": "Willing/Coerced Qualifier (Generic)",
    "willing": "Willing",
    "coerced_impressed": "Coerced/Impressed",
    "mine_laying": "Mine Laying",
    "spy": "Spy",
    "warrant_served": "Warrant Served",
    "exfiltration": "Exfiltration",
    "infiltration": "Infiltration",
    "meeting": "Meeting",
    "polling_place_election": "Polling Place/Election",
    "raid": "Raid",
    "emergency_operation": "Emergency Operation",
    "emergency_collection_evacuation_point": "Emergency Collection/Evacuation Point",
    "food_distribution": "Food Distribution",
    "emergency_incident_command_center": "Emergency Incident Command Center",
    "emergency_operations_center": "Emergency Operations Center",
    "emergency_public_information_center": "Emergency Public Information Center",
    "emergency_shelter": "Emergency Shelter",
    "emergency_staging_area": "Emergency Staging Area",
    "water_distribution_center": "Water Distribution Center",
    "emergency_medical_operation": "Emergency Medical Operation",
    "emt_station_location": "EMT Station Location",
    "health_department_facility": "Health Department Facility",
    "medical_facilities_outpatient": "Medical Facilities Outpatient",
    "emergency_medical_operation_facility": "Emergency Medical Operation Facility",
    "pharmacy": "Pharmacy",
    "triage": "Triage",
    "fire_protection": "Fire Protection",
    "fire_hydrant": "Fire Hydrant",
    "fire_station": "Fire Station",
    "other_water_supply_location": "Other Water Supply Location",
    # Table A-XXXVIII prints 131500 as "Law Enforcement Operation";
    # the shorter form was ours. Corrected 2026-08-18 after 2525E
    # showed the standard's own wording side by side with it.
    "law_enforcement": "Law Enforcement Operation",
    "bureau_of_alcohol_tobacco_firearms_and_explosives": "Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF)",
    "border_patrol": "Border Patrol",
    "customs_service": "Customs Service",
    "drug_enforcement_administration": "Drug Enforcement Administration (DEA)",
    "department_of_justice": "Department of Justice (DOJ)",
    "federal_bureau_of_investigation": "Federal Bureau of Investigation (FBI)",
    "police": "Police",
    "prison": "Prison",
    # "secret" here is the US Secret Service, a MIL-STD-2525D entity
    # name - not a credential. Suppressions are for the scanners' own
    # keyword heuristics (1.0.0's automated review, 2026-08-17).
    "united_states_secret_service": "United States Secret Service (USSS)",  # nosec B105 # pragma: allowlist secret
    "transportation_security_administration": "Transportation Security Administration (TSA)",
    # Table A-XXXVIII prints 131511 as Coast Guard; there is no "Law
    # Enforcement Vessel" row in this table. Key left alone (saved
    # features carry it); the label is what a user reads.
    "law_enforcement_vessel": "Coast Guard",
    "us_marshals_service": "US Marshals Service",
    "internal_security_force": "Internal Security Force",
    "fire_event": "Fire Event",
    "fire_origin": "Fire Origin",
    "smoke": "Smoke",
    "hot_spot": "Hot Spot",
    "non_residential_fire": "Non-Residential Fire",
    "residential_fire": "Residential Fire",
    "school_fire": "School Fire",
    "special_needs_fire": "Special Needs Fire",
    "wild_fire": "Wild Fire",
    "hazardous_materials": "Hazardous Materials (Generic)",
    "hazardous_materials_incident": "Hazardous Materials Incident",
    "chemical_agent": "Chemical Agent",
    "corrosive_material": "Corrosive Material",
    "hazardous_when_wet": "Hazardous When Wet",
    "explosive_material": "Explosive Material",
    "flammable_gas": "Flammable Gas",
    "flammable_liquid": "Flammable Liquid",
    "flammable_solid": "Flammable Solid",
    "non_flammable_gas": "Non-Flammable Gas",
    "organic_peroxide": "Organic Peroxide",
    "oxidizer": "Oxidizer",
    "radioactive_material": "Radioactive Material",
    "spontaneously_combustible_material": "Spontaneously Combustible Material",
    "toxic_gas": "Toxic Gas",
    "toxic_infectious_material": "Toxic Infectious Material",
    "unexploded_ordnance": "Unexploded Ordnance",
    "transportation": "Transportation",
    "hijacking_airplane": "Hijacking (Airplane)",
    "hijacking_boat": "Hijacking (Boat)",
    "train_locomotive": "Train Locomotive",
    "known_insurgent_vehicle": "Known Insurgent Vehicle",
    "vehicle_explosion": "Vehicle Explosion",
    "natural_event": "Natural Event",
    "geologic": "Geologic",
    "aftershock": "Aftershock",
    "avalanche": "Avalanche",
    "earthquake_epicenter": "Earthquake Epicenter",
    "landslide": "Landslide",
    "subsidence": "Subsidence",
    "volcanic_eruption": "Volcanic Eruption",
    "volcanic_threat": "Volcanic Threat",
    "cave_entrance": "Cave Entrance",
    "hydro_meteorological": "Hydro-Meteorological",
    "drought": "Drought",
    "flood": "Flood",
    "tsunami": "Tsunami",
    "infestation": "Infestation",
    "bird": "Bird",
    "insect": "Insect",
    "microbial": "Microbial",
    "reptile": "Reptile",
    "rodent": "Rodent",
    "personalities": "Personalities (Generic)",
    "religious_leader": "Religious Leader",
    "spokesperson": "Spokesperson",
    "isolated_personnel": "Isolated Personnel",
}

_SECTOR1_LABELS = {
    "assassination": "Assassination",
    "execution": "Execution (Wrongful Killing)",
    "hijacking_hijacked": "Hijacking/Hijacked",
    "house_to_house": "House-to-House",
    "kidnapping": "Kidnapping",
    "murder": "Murder",
    "piracy": "Piracy",
    "rape": "Rape",
    "written_military_information_support_operations": "Written Military Information Support Operations",
    "pirate": "Pirate",
    "false": "False",
    "find": "Find",
    "found_and_cleared": "Found and Cleared",
    "hoax_decoy": "Hoax (Decoy)",
    "attempted": "Attempted",
    "accident": "Accident",
    "incident": "Incident",
    "theft_modifier": "Theft",
}


def add_activities_layer(iface, edition=None):

    """
    Add the "Activities" layer - warns and does
    nothing if one already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        OUTPUT_LAYER_NAME,
        "activities",
        _ENTITY_LABELS,
        DEFAULT_ENTITY,
        include_echelon=False,
        include_headquarters=False,
        sector1_labels=_SECTOR1_LABELS,
        edition=edition,
    )
