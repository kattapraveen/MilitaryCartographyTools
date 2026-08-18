# -*- coding: utf-8 -*-

"""
Builds four "Land <Domain>" point layers -
MIL-STD-2525D Appendix D (Land Symbols), one per D.6-D.9 section, each a
genuinely distinct SIDC symbol_set (Table A-III: Land Unit=10, Land
Civilian Unit/Organization=11, Land Equipment=15, Land Installation=20).

Unlike Space/Air (military_symbology/space_layer.py, air_layer.py),
these are NOT merged into one layer via entity_symbol_set_overrides -
that mechanism is meant for folding in a small single-entity companion
(Space/Air Missile), not four substantial, independently-sized
vocabularies. Four separate layers, added together under one toolbar
action, mirrors c2_measures.py's own "one action, several layers"
precedent instead.

Land Unit ("ground_unit" in sidc.py - kept as the existing key rather
than renamed, since it's already used throughout sidc.py/tests/roadmap
and Table A-III's own code "10" doesn't change either way) moved here
2026-08-08 from military_symbology/unit_layer.py, which used to share it
across a cascading multi-domain dropdown with air/sea_surface/subsurface
- see that module's own docstring for what's left there.

Field applicability (echelon/headquarters) follows Chapter 5's Table VII
literally, since Appendix D's own Table D-II doesn't restate per-domain
columns the way the base document's Table VII does: Field B (Echelon)
applies only to Units (the "U" column) - so Land Unit gets it, Land
Civilian/Equipment/Installation don't. Field S (Headquarters Staff
Indicator) applies to Units/Equipment/Installations (not SIGINT) - all
four Land layers get it, including Land Civilian, whose own "civilian
unit/organization" framing reads closest to Table VII's "U" category for
this purpose.

Entity vocabulary: Land Unit is milsymbol-3.0.4's own
src/numbersidc/sidc/landunit.js, kept as the pre-existing curated 50-
entity subset (of 219 total) already in sidc.py's ENTITIES["ground_unit"]
- re-verified entity-by-entity against that source directly this session
(every code confirmed correct, no bugs found). Land Civilian is
landcivilian.js's FULL 11-entity vocabulary (small enough that no
curation is needed). Land Equipment (153 entities, of 229 total in
landequipment.js) and Land Installation (99 entities, of 131 total in
landinstallation.js) are curated subsets - see sidc.py's own
ENTITIES["land_equipment"]/["land_installation"] comments for the
categories covered and for two follow-up fixes, both caught by the user,
not self-discovered: (1) the first pass at both (50-ish entries each)
silently dropped an entire axis of real entries - Equipment's weapon/
vehicle weight-class variants, Installation's remaining sibling facility
types within a category (e.g. ATM/bullion storage/federal reserve bank
alongside bank) - fixed the same day by a full multi-line-aware parse of
each source file rather than another round of shallow spot-picking; (2)
those newly-added weapon variants were then mislabeled Short/
Intermediate/Long Range - trusted milsymbol.js's own internal icon-part
constant names (e.g. "GR.EQ.SHORT RANGE") instead of the standard's own
printed text, which actually reads Light/Medium/Heavy for every weapon
category except Rifle (Single Shot/Semiautomatic/Automatic, confirmed
directly against Table D-XI, printed page 229) - fixed by renaming the
entity keys/labels to match the standard's own wording, not milsymbol's
internal naming. (3) Land Equipment's law-enforcement family
(Table A-XXV, codes 1700xx-1711xx) shipped with only four of its twelve
entries through 1.0.3 - generic, Border Patrol, Customs, DEA - stopping
mid-family rather than at a category boundary, so it read as complete
when it was not; the eight missing entries were added 2026-08-18 after
confirming milsymbol draws every one of them. Note the family's tail is
NOT shared with the Activities or Land Installation law-enforcement
lists: 171000 is Coast Guard here, and there is no Prison or Law
Enforcement Vessel in Land Equipment at all.
(4) Land Installation's own law-enforcement family had the same shape of
problem plus a worse one, both fixed 2026-08-18 after the maintainer read
the live dropdown: ATF (112101) and Police (112107) were simply absent,
and 112111 - printed **Coast Guard** in Table A-XXVII - was offered to
users as "Law Enforcement Vessel", a row that does not exist in that
table at all (the standard's real one is Sea Surface 140300). Two labels
also read "Agency" where the standard reads "Administration" (DEA, TSA).
Every fix here changed labels and added entries; no shipped entity KEY
was renamed, because keys are written into saved features.

Sector 1/2 modifiers deliberately NOT built for any of these four layers
in this pass - Land Unit alone has ~50+ sector 1 and ~50+ sector 2
modifier codes (Tables D-VI/D-VII), and all four domains combined would
be a disproportionately large addition on top of an already-large
appendix; a documented, deliberate scope decision (same "not everything
has to be built every mini-phase" precedent already used for
ground_unit's own entity curation), not an oversight.

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


UNIT_LAYER_NAME = "Land Unit"

CIVILIAN_LAYER_NAME = "Land Civilian"

EQUIPMENT_LAYER_NAME = "Land Equipment"

INSTALLATION_LAYER_NAME = "Land Installation"

DEFAULT_UNIT_ENTITY = "infantry"

DEFAULT_CIVILIAN_ENTITY = "civilian"

DEFAULT_EQUIPMENT_ENTITY = "tank"

DEFAULT_INSTALLATION_ENTITY = "military"

# Display labels - kept separate from sidc.py's own vocabulary dicts,
# which are the data model (real SIDC component codes), not presentation
# text. Reused verbatim from unit_layer.py's own former
# _ENTITY_LABELS_BY_SYMBOL_SET["ground_unit"] (moved here, not
# retyped) - organised by the same functional-area breakdown (command/
# signal, maneuver, fires, air defense, combat support, intelligence,
# combat service support).
_UNIT_ENTITY_LABELS = {
    # Command & signal
    "command_and_control": "Command and Control",
    "signal": "Signal",
    "liaison": "Liaison",
    # Maneuver
    "infantry": "Infantry",
    "motorized_infantry": "Motorized Infantry",
    "mechanized_infantry": "Mechanized Infantry",
    "armor": "Armor",
    "reconnaissance": "Reconnaissance",
    "antitank": "Antitank/Antiarmor",
    "combined_arms": "Combined Arms",
    "aviation_rotary_wing": "Aviation (Rotary Wing)",
    "aviation_fixed_wing": "Aviation (Fixed Wing)",
    "air_assault": "Air Assault",
    "amphibious": "Amphibious",
    "special_forces": "Special Forces",
    "ranger": "Ranger",
    "sniper": "Sniper",
    "surveillance": "Surveillance",
    "unmanned_systems": "Unmanned Systems",
    # Fires
    "field_artillery": "Field Artillery",
    "field_artillery_self_propelled": "Field Artillery, Self-Propelled",
    "field_artillery_observer": "Field Artillery Observer",
    "mortar": "Mortar",
    "missile": "Missile",
    "joint_fire_support": "Joint Fire Support",
    # Air defense
    "air_defense": "Air Defense",
    "air_defense_gun": "Air Defense Gun",
    "air_defense_missile": "Air Defense Missile",
    "air_and_missile_defense": "Air and Missile Defense",
    # Combat support
    "engineer": "Engineer",
    "engineer_mechanized": "Engineer, Mechanized",
    "cbrn": "CBRN (Chemical, Biological, Radiological, Nuclear)",
    "explosive_ordnance_disposal": "Explosive Ordnance Disposal (EOD)",
    "military_police": "Military Police",
    "mine_clearing": "Mine Clearing",
    "search_and_rescue": "Search and Rescue",
    "security": "Security",
    # Intelligence & electronic warfare
    "military_intelligence": "Military Intelligence",
    "electronic_warfare": "Electronic Warfare",
    "counter_intelligence": "Counter-Intelligence",
    "sensor": "Sensor",
    # Combat service support
    "sustainment": "Sustainment",
    "maintenance": "Maintenance",
    "medical": "Medical",
    "supply": "Supply",
    "transportation": "Transportation",
    "quartermaster": "Quartermaster",
    "ordnance": "Ordnance",
    "ammunition": "Ammunition",
    "petroleum_oil_lubricants": "Petroleum, Oil, and Lubricants (POL)",
}

_CIVILIAN_ENTITY_LABELS = {
    "civilian": "Civilian (Generic)",
    "environmental_protection": "Environmental Protection",
    "government_organization": "Government Organization",
    "individual": "Individual",
    "group": "Group",
    "killing_victim": "Killing Victim",
    "killing_victims": "Killing Victims",
    "victim_of_attempted_crime": "Victim of Attempted Crime",
    "spy": "Spy",
    "composite_loss": "Composite Loss",
    "emergency_medical_operation": "Emergency Medical Operation",
}

_EQUIPMENT_ENTITY_LABELS = {
    "weapon": "Weapon (Generic)",
    "rifle": "Rifle",
    "rifle_single_shot": "Rifle - Single Shot",
    "rifle_semiautomatic": "Rifle - Semiautomatic",
    "rifle_automatic": "Rifle - Automatic",
    "machine_gun": "Machine Gun",
    "machine_gun_light": "Machine Gun (Light)",
    "machine_gun_medium": "Machine Gun (Medium)",
    "machine_gun_heavy": "Machine Gun (Heavy)",
    "grenade_launcher": "Grenade Launcher",
    "grenade_launcher_light": "Grenade Launcher (Light)",
    "grenade_launcher_medium": "Grenade Launcher (Medium)",
    "grenade_launcher_heavy": "Grenade Launcher (Heavy)",
    "flame_thrower": "Flame Thrower",
    "air_defense_gun": "Air Defense Gun",
    "air_defense_gun_light": "Air Defense Gun (Light)",
    "air_defense_gun_medium": "Air Defense Gun (Medium)",
    "air_defense_gun_heavy": "Air Defense Gun (Heavy)",
    "antitank_gun": "Antitank Gun",
    "antitank_gun_light": "Antitank Gun (Light)",
    "antitank_gun_medium": "Antitank Gun (Medium)",
    "antitank_gun_heavy": "Antitank Gun (Heavy)",
    "direct_fire_gun": "Direct Fire Gun",
    "direct_fire_gun_light": "Direct Fire Gun (Light)",
    "direct_fire_gun_medium": "Direct Fire Gun (Medium)",
    "direct_fire_gun_heavy": "Direct Fire Gun (Heavy)",
    "recoilless_gun": "Recoilless Gun",
    "recoilless_gun_light": "Recoilless Gun (Light)",
    "recoilless_gun_medium": "Recoilless Gun (Medium)",
    "recoilless_gun_heavy": "Recoilless Gun (Heavy)",
    "howitzer": "Howitzer",
    "howitzer_light": "Howitzer (Light)",
    "howitzer_medium": "Howitzer (Medium)",
    "howitzer_heavy": "Howitzer (Heavy)",
    "missile_launcher": "Missile Launcher",
    "missile_launcher_light": "Missile Launcher (Light)",
    "missile_launcher_medium": "Missile Launcher (Medium)",
    "missile_launcher_heavy": "Missile Launcher (Heavy)",
    "air_defense_missile_launcher_surface_to_air": "Air Defense Missile Launcher, Surface-to-Air",
    "air_defense_missile_launcher_surface_to_air_light": "Air Defense Missile Launcher, Surface-to-Air (Light)",
    "air_defense_missile_launcher_surface_to_air_medium": "Air Defense Missile Launcher, Surface-to-Air (Medium)",
    "air_defense_missile_launcher_surface_to_air_heavy": "Air Defense Missile Launcher, Surface-to-Air (Heavy)",
    "antitank_missile_launcher": "Antitank Missile Launcher",
    "antitank_missile_launcher_light": "Antitank Missile Launcher (Light)",
    "antitank_missile_launcher_medium": "Antitank Missile Launcher (Medium)",
    "antitank_missile_launcher_heavy": "Antitank Missile Launcher (Heavy)",
    "surface_to_surface_missile_launcher": "Surface-to-Surface Missile Launcher",
    "surface_to_surface_missile_launcher_light": "Surface-to-Surface Missile Launcher (Light)",
    "surface_to_surface_missile_launcher_medium": "Surface-to-Surface Missile Launcher (Medium)",
    "surface_to_surface_missile_launcher_heavy": "Surface-to-Surface Missile Launcher (Heavy)",
    "mortar": "Mortar",
    "mortar_light": "Mortar (Light)",
    "mortar_medium": "Mortar (Medium)",
    "mortar_heavy": "Mortar (Heavy)",
    "single_rocket_launcher": "Single Rocket Launcher",
    "single_rocket_launcher_light": "Single Rocket Launcher (Light)",
    "single_rocket_launcher_medium": "Single Rocket Launcher (Medium)",
    "single_rocket_launcher_heavy": "Single Rocket Launcher (Heavy)",
    "multiple_rocket_launcher": "Multiple Rocket Launcher",
    "multiple_rocket_launcher_light": "Multiple Rocket Launcher (Light)",
    "multiple_rocket_launcher_medium": "Multiple Rocket Launcher (Medium)",
    "multiple_rocket_launcher_heavy": "Multiple Rocket Launcher (Heavy)",
    "antitank_rocket_launcher": "Antitank Rocket Launcher",
    "antitank_rocket_launcher_light": "Antitank Rocket Launcher (Light)",
    "antitank_rocket_launcher_medium": "Antitank Rocket Launcher (Medium)",
    "antitank_rocket_launcher_heavy": "Antitank Rocket Launcher (Heavy)",
    "non_lethal_weapon": "Non-Lethal Weapon",
    "taser": "Taser",
    "water_cannon": "Water Cannon",
    "armoured_vehicle": "Armoured Vehicle (Generic)",
    "armored_fighting_vehicle": "Armored Fighting Vehicle",
    "armored_fighting_vehicle_command_and_control": "Armored Fighting Vehicle (Command and Control)",
    "armored_personnel_carrier": "Armored Personnel Carrier",
    "armored_personnel_carrier_medical_evacuation": "Armored Personnel Carrier (Medical Evacuation)",
    "tank": "Tank",
    "tank_light": "Tank (Light)",
    "tank_medium": "Tank (Medium)",
    "tank_heavy": "Tank (Heavy)",
    "tank_recovery_vehicle": "Tank Recovery Vehicle",
    "bridge": "Bridge",
    "fixed_bridge": "Fixed Bridge",
    "folding_girder_bridge": "Folding Girder Bridge",
    "hollow_deck_bridge": "Hollow Deck Bridge",
    "drilling": "Drilling",
    "earthmover": "Earthmover",
    "multifunctional_earthmover_digger": "Multifunctional Earthmover/Digger",
    "mine_clearing_equipment": "Mine Clearing Equipment",
    "mine_clearing_equipment_tank": "Mine Clearing Equipment (Tank-Mounted)",
    "mine_laying": "Mine Laying",
    "dozer": "Dozer",
    "dozer_armored": "Dozer, Armored",
    "utility_vehicle": "Utility Vehicle",
    "bus": "Bus",
    "semi_trailer_truck": "Semi-Trailer Truck",
    "semi_trailer_truck_light": "Semi-Trailer Truck (Light)",
    "semi_trailer_truck_medium": "Semi-Trailer Truck (Medium)",
    "semi_trailer_truck_heavy": "Semi-Trailer Truck (Heavy)",
    "train_locomotive": "Train Locomotive",
    "railcar": "Railcar",
    "automobile": "Automobile",
    "automobile_light": "Automobile (Light)",
    "automobile_medium": "Automobile (Medium)",
    "automobile_heavy": "Automobile (Heavy)",
    "open_bed_truck": "Open-Bed Truck",
    "open_bed_truck_light": "Open-Bed Truck (Light)",
    "open_bed_truck_medium": "Open-Bed Truck (Medium)",
    "open_bed_truck_heavy": "Open-Bed Truck (Heavy)",
    "multiple_passenger_vehicle": "Multiple Passenger Vehicle",
    "multiple_passenger_vehicle_light": "Multiple Passenger Vehicle (Light)",
    "multiple_passenger_vehicle_medium": "Multiple Passenger Vehicle (Medium)",
    "multiple_passenger_vehicle_heavy": "Multiple Passenger Vehicle (Heavy)",
    "civilian_utility_vehicle": "Civilian Utility Vehicle",
    "civilian_utility_vehicle_light": "Civilian Utility Vehicle (Light)",
    "civilian_utility_vehicle_medium": "Civilian Utility Vehicle (Medium)",
    "civilian_utility_vehicle_heavy": "Civilian Utility Vehicle (Heavy)",
    "jeep_type_vehicle": "Jeep-Type Vehicle",
    "jeep_type_vehicle_light": "Jeep-Type Vehicle (Light)",
    "jeep_type_vehicle_medium": "Jeep-Type Vehicle (Medium)",
    "jeep_type_vehicle_heavy": "Jeep-Type Vehicle (Heavy)",
    "known_insurgent_vehicle": "Known Insurgent Vehicle",
    "law_enforcement": "Law Enforcement",
    "bureau_of_alcohol_tobacco_firearms_and_explosives":
        "Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF)",
    "border_patrol": "Border Patrol",
    "customs_service": "Customs Service",
    "drug_enforcement_agency": "Drug Enforcement Administration (DEA)",
    "department_of_justice": "Department of Justice (DOJ)",
    "federal_bureau_of_investigation": "Federal Bureau of Investigation (FBI)",
    "police": "Police",
    # "secret" here is the US Secret Service, a MIL-STD-2525D entity
    # name - not a credential. Suppressions are for the scanners' own
    # keyword heuristics (1.0.0's automated review, 2026-08-17).
    "united_states_secret_service": "United States Secret Service (USSS)",  # nosec B105 # pragma: allowlist secret
    "transportation_security_administration":
        "Transportation Security Administration (TSA)",
    "coast_guard": "Coast Guard",
    "us_marshals_service": "US Marshals Service",
    "missile_support": "Missile Support (Generic)",
    "missile_transloader": "Missile Transloader",
    "missile_transporter": "Missile Transporter",
    "missile_crane_loading_device": "Missile Crane/Loading Device",
    "pack_animal": "Pack Animal",
    "bomb": "Bomb",
    "booby_trap": "Booby Trap",
    "cbrn_equipment": "CBRN Equipment",
    "computer_system": "Computer System",
    "command_launch_equipment": "Command Launch Equipment (CLE)",
    "generator_set": "Generator Set",
    "laser": "Laser",
    "tent": "Tent",
    "land_mine": "Land Mine",
    "antipersonnel_land_mine": "Antipersonnel Land Mine",
    "antitank_mine": "Antitank Mine",
    "improvised_explosive_device": "Improvised Explosive Device (IED)",
    "sensor": "Sensor",
    "radar": "Radar",
    "fire_protection": "Fire Protection",
    "manual_track": "Manual Track",
}

_INSTALLATION_ENTITY_LABELS = {
    "military": "Military (Generic)",
    "aircraft_production_and_assembly": "Aircraft Production and Assembly",
    "cbrn": "CBRN",
    "equipment_manufacture": "Equipment Manufacture",
    "government": "Government",
    "mine": "Mine",
    "printed_media": "Printed Media",
    "safe_house": "Safe House",
    "law_enforcement": "Law Enforcement (Generic)",
    "bureau_of_alcohol_tobacco_firearms_and_explosives":
        "Bureau of Alcohol, Tobacco, Firearms and Explosives (ATF)",
    "border_patrol": "Border Patrol",
    "customs_service": "Customs Service",
    # Table A-XXVII reads "Drug Enforcement Administration (DEA)" and
    # "Transportation Security Administration (TSA)". Both labels said
    # "Agency" until 2026-08-18. Keys keep their shipped spellings -
    # they are written into saved features' "entity" field - so only the
    # text a user reads in the dropdown changed.
    "drug_enforcement_agency": "Drug Enforcement Administration (DEA)",
    "department_of_justice": "Department of Justice (DOJ)",
    "federal_bureau_of_investigation": "Federal Bureau of Investigation (FBI)",
    "police": "Police",
    "prison": "Prison",
    # "secret" here is the US Secret Service, a MIL-STD-2525D entity
    # name - not a credential. Suppressions are for the scanners' own
    # keyword heuristics (1.0.0's automated review, 2026-08-17).
    "secret_service": "United States Secret Service (USSS)",  # nosec B105 # pragma: allowlist secret
    "transportation_security_agency": "Transportation Security Administration (TSA)",
    # Table A-XXVII prints 112111 as Coast Guard; there is no "Law
    # Enforcement Vessel" row in this table. The key is left alone (it
    # is in users' saved features); this is the text they read.
    "law_enforcement_vessel": "Coast Guard",
    "us_marshals_service": "US Marshals Service",
    "emergency_operation": "Emergency Operation",
    "fire_protection": "Fire Protection",
    "emergency_medical_operation": "Emergency Medical Operation",
    "home": "Home",
    "agriculture_and_food_infrastructure": "Agriculture and Food Infrastructure (Generic)",
    "agricultural_laboratory": "Agricultural Laboratory",
    "animal_feedlot": "Animal Feedlot",
    "farm_ranch": "Farm/Ranch",
    "food_distribution": "Food Distribution",
    "food_distribution_production": "Food Distribution (Production)",
    "food_distribution_retail": "Food Distribution (Retail)",
    "grain_storage": "Grain Storage",
    "banking_finance_and_insurance_infrastructure": "Banking, Finance and Insurance Infrastructure (Generic)",
    "atm": "ATM",
    "bank": "Bank",
    "bullion_storage": "Bullion Storage",
    "federal_reserve_bank": "Federal Reserve Bank",
    "financial_exchange": "Financial Exchange",
    "financial_services_other": "Financial Services, Other",
    "commercial_infrastructure": "Commercial Infrastructure (Generic)",
    "chemical_plant": "Chemical Plant",
    "firearms_manufacturer": "Firearms Manufacturer",
    "firearms_retailer": "Firearms Retailer",
    "hazardous_material_production": "Hazardous Material Production",
    "hazardous_material_storage": "Hazardous Material Storage",
    "industrial_site": "Industrial Site",
    "landfill": "Landfill",
    "pharmaceutical_manufacturer": "Pharmaceutical Manufacturer",
    "contaminated_hazardous_waste_site": "Contaminated Hazardous Waste Site",
    "toxic_release_inventory": "Toxic Release Inventory",
    "educational_facilities_infrastructure": "Educational Facilities Infrastructure (Generic)",
    "college_university": "College/University",
    "school": "School",
    "electric_power": "Electric Power",
    "natural_gas_facility": "Natural Gas Facility",
    "propane_facility": "Propane Facility",
    "government_site_infrastructure": "Government Site Infrastructure",
    "medical": "Medical",
    "medical_treatment_facility": "Medical Treatment Facility",
    "military_infrastructure": "Military Infrastructure (Generic)",
    "base": "Base",
    "airport": "Airport",
    "postal_service_infrastructure": "Postal Service Infrastructure (Generic)",
    "postal_distribution_center": "Postal Distribution Center",
    "post_office": "Post Office",
    "public_venues_infrastructure": "Public Venues Infrastructure (Generic)",
    "enclosed_facility": "Enclosed Facility (Public Venue)",
    "open_facility": "Open Facility (Open Venue)",
    "recreational_area": "Recreational Area",
    "religious_institution": "Religious Institution",
    "special_needs_infrastructure": "Special Needs Infrastructure (Generic)",
    "adult_day_care": "Adult Day Care",
    "child_day_care": "Child Day Care",
    "elder_care": "Elder Care",
    "telecommunications_infrastructure": "Telecommunications Infrastructure (Generic)",
    "broadcast_transmitter_antenna": "Broadcast Transmitter Antenna",
    "telecommunications_tower": "Telecommunications Tower",
    "transportation": "Transportation (Generic)",
    "air_traffic_control_facility": "Air Traffic Control Facility",
    "ferry": "Ferry",
    "helicopter_landing_site": "Helicopter Landing Site",
    "maintenance": "Maintenance",
    "railhead": "Railhead",
    "rest_stop": "Rest Stop",
    "toll_facility": "Toll Facility",
    "traffic_inspection_facility": "Traffic Inspection Facility",
    "tunnel": "Tunnel",
    "water": "Water (Generic)",
    "control_valve": "Control Valve",
    "dam": "Dam",
    "discharge_outfall": "Discharge Outfall",
    "ground_water_well": "Ground Water Well",
    "pumping_station": "Pumping Station",
    "reservoir": "Reservoir",
    "storage_tower": "Storage Tower",
    "surface_water_intake": "Surface Water Intake",
    "wastewater_treatment_facility": "Wastewater Treatment Facility",
    "water_purification": "Water Purification",
}


def add_land_unit_layer(iface):

    """Add "Land Unit" (D.6) - echelon and headquarters both apply (Table VII's "U" column)."""

    return add_single_domain_point_layer(
        iface,
        UNIT_LAYER_NAME,
        "ground_unit",
        _UNIT_ENTITY_LABELS,
        DEFAULT_UNIT_ENTITY,
        include_echelon=True,
        include_headquarters=True,
    )


def add_land_civilian_layer(iface):

    """Add "Land Civilian" (D.7) - no echelon, headquarters applies."""

    return add_single_domain_point_layer(
        iface,
        CIVILIAN_LAYER_NAME,
        "land_civilian",
        _CIVILIAN_ENTITY_LABELS,
        DEFAULT_CIVILIAN_ENTITY,
        include_echelon=False,
        include_headquarters=True,
    )


def add_land_equipment_layer(iface):

    """Add "Land Equipment" (D.8) - no echelon, headquarters applies."""

    return add_single_domain_point_layer(
        iface,
        EQUIPMENT_LAYER_NAME,
        "land_equipment",
        _EQUIPMENT_ENTITY_LABELS,
        DEFAULT_EQUIPMENT_ENTITY,
        include_echelon=False,
        include_headquarters=True,
    )


def add_land_installation_layer(iface):

    """Add "Land Installation" (D.9) - no echelon, headquarters applies."""

    return add_single_domain_point_layer(
        iface,
        INSTALLATION_LAYER_NAME,
        "land_installation",
        _INSTALLATION_ENTITY_LABELS,
        DEFAULT_INSTALLATION_ENTITY,
        include_echelon=False,
        include_headquarters=True,
    )


def add_land_layers(iface):

    """
    Add all four Land layers (Unit/Civilian/Equipment/Installation) in
    one call - the toolbar action's own callback. Each has its own
    already-exists guard (add_single_domain_point_layer()), so calling
    this again only adds whichever of the four are still missing.
    Returns a dict of {layer_name: layer_or_None}.
    """

    return {
        UNIT_LAYER_NAME: add_land_unit_layer(iface),
        CIVILIAN_LAYER_NAME: add_land_civilian_layer(iface),
        EQUIPMENT_LAYER_NAME: add_land_equipment_layer(iface),
        INSTALLATION_LAYER_NAME: add_land_installation_layer(iface),
    }
