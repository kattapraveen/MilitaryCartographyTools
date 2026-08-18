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
    positions 11-16  function ID: a 6-character base entity code - see
                     ENTITIES
    positions 17-18  sector 1 modifier - see MODIFIERS, "00" if none
    positions 19-20  sector 2 modifier - see MODIFIERS, "00" if none

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
    # Table D-III (Land appendix) lists three further echelons beyond
    # Army that this dict was missing entirely until 2026-08-09, found
    # while re-auditing MIL-STD-2525D Appendix H's own H.5.1.1.6 (which
    # cross-references table D-III for the same echelon indicator used
    # on boundary lines) - confirmed against milsymbol.js's own
    # echelonMobility table (24="Army Group/front", 25="Region/Theater",
    # 26="Command"), which already supports all three; this project's
    # own ECHELONS dict had simply never been extended to match. A real
    # vocabulary gap affecting every point-symbol layer built with
    # military_symbology/_point_symbol_layer.py, not just Appendix H.
    "army_group": "24",
    "theater": "25",
    "command": "26",
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
    # Table A-III: Space=05, Space Missile=06. Added 2026-08-08 during
    # the appendix-by-appendix completion pass, Appendix B (Space).
    "space": "05",
    "space_missile": "06",
    # Table A-III: Air Missile=02. Added 2026-08-08, Appendix C (Air).
    "air_missile": "02",
    # Table A-III: Land Civilian Unit/Organization=11, Land Equipment=15,
    # Land Installation=20. Added 2026-08-08, Appendix D (Land) - "10"
    # (Land Unit) is "ground_unit" above, already present since sub-phase
    # 10.1.
    "land_civilian": "11",
    "land_equipment": "15",
    "land_installation": "20",
    # Table A-III: Mine Warfare=36. Added 2026-08-08, Appendix F.
    "mine_warfare": "36",
    # Table A-III: Activities=40. Added 2026-08-08, Appendix G.
    "activities": "40",
    # Table A-III / Table J-II's own SymbolSetCode column: Signals
    # Intelligence Space=50, Air=51, Land=52, Sea Surface=53,
    # Subsurface=54. Added 2026-08-08, Appendix J. Genuinely five
    # symbol sets for ONE shared entity vocabulary (Table J-II lists the
    # same four entity codes against all five) - see sigint_layer.py and
    # ENTITIES["sigint"] below.
    "sigint_space": "50",
    "sigint_air": "51",
    "sigint_land": "52",
    "sigint_sea_surface": "53",
    "sigint_subsurface": "54",
    # Table A-III: Cyberspace=60. Added 2026-08-08, Appendix L.
    "cyberspace": "60",
    # Appendix H's own point-type control measures (checkpoints, contact/
    # decision points, target points, sustainment/supply points, and
    # similar) - a different rendering mechanism from the hand-built
    # line/area symbology each H.5.x logical group's own module builds
    # (c2_measures.py and future ones, see _control_measure_shared.py -
    # those cover H's LINE/AREA control measures; this symbol set covers
    # H's POINT ones, which milsymbol.js already renders same as any
    # other symbol set). Added 2026-08-07 - see
    # military_symbology/control_measure_points.py.
    "control_measure": "25",
}

# Real codes from milsymbol-3.0.4's own
# src/numbersidc/sidc/signalsintelligence.js - the FULL 4-entity
# vocabulary, cross-checked against the standard's own Table J-II
# (Appendix J, printed pages 773-774). One shared dict object (not five
# separate copies) referenced under all five ENTITIES["sigint_*"] keys
# below - Table J-II's own SymbolSetCode column lists the exact same
# four entity codes against all five symbol sets (50-54) at once, so a
# single source of truth here is both correct and impossible to let
# drift out of sync across the five keys, unlike a hand-copied
# duplicate would be.
_SIGINT_ENTITIES = {
    "signal_intercept": "110000",
    "communications": "110100",
    "jammer": "110200",
    "radar": "110300",
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
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/landcivilian.js (symbolSet == "11") - the FULL
    # vocabulary (only 11 top-level entities, small enough that no
    # curation is needed, unlike ground_unit's own 219-entity source).
    "land_civilian": {
        "civilian": "110000",
        "environmental_protection": "110100",
        "government_organization": "110200",
        "individual": "110300",
        "group": "110400",
        "killing_victim": "110500",
        "killing_victims": "110600",
        "victim_of_attempted_crime": "110700",
        "spy": "110800",
        "composite_loss": "110900",
        "emergency_medical_operation": "111000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/landequipment.js (symbolSet == "15") - a
    # curated subset (229 top-level entities in total), spanning
    # weapons, vehicles/armor, engineer equipment, transport, civilian
    # vehicles, law enforcement, missile support and other equipment.
    #
    # Revised 2026-08-08 after the user pointed out a systematic gap in
    # the first pass: nearly every weapon category
    # (machine_gun/grenade_launcher/air_defense_gun/antitank_gun/
    # direct_fire_gun/recoilless_gun/howitzer/missile_launcher/antitank_
    # missile_launcher/surface_to_surface_missile_launcher/mortar/
    # single_rocket_launcher/multiple_rocket_launcher/antitank_rocket_
    # launcher/air_defense_missile_launcher_surface_to_air) has a
    # Light/Medium/Heavy weight-class variant at entity-subtype codes
    # X01/X02/X03 (confirmed directly against the standard's own Table
    # D-XI, printed pages 229-242 - not just milsymbol.js), and nearly
    # every vehicle category (tank, automobile/open_bed_truck/multiple_
    # passenger_vehicle/civilian_utility_vehicle/jeep_type_vehicle) has
    # the same Light/Medium/Heavy axis - the first pass only included
    # the generic (X00) form of each, silently dropping this entire axis
    # rather than a few isolated entries. Every code below was verified
    # via a full multi-line-aware parse of landequipment.js's own
    # sId["code"] = [...] entries (not spot-checked), confirming both
    # the omission and the fix.
    #
    # Same-day second correction, also caught by the user: the newly-
    # added weapon variants were initially named/labeled Short/
    # Intermediate/Long Range, trusting milsymbol.js's own internal
    # icon-part constant strings (e.g. "GR.EQ.SHORT RANGE") instead of
    # checking the standard's own printed text - those milsymbol strings
    # turned out to be internal graphics-composition labels unrelated to
    # the actual doctrinal category, which Table D-XI's own text gives
    # as Light/Medium/Heavy for every weapon category EXCEPT rifle,
    # which the standard specifically calls Single Shot/Semiautomatic/
    # Automatic (page 229) - genuinely different from every other
    # category, not a light/medium/heavy variant at all. Renamed
    # accordingly (rifle_single_shot/rifle_semiautomatic/rifle_automatic;
    # every other category's own _short_range/_intermediate_range/
    # _long_range keys renamed to _light/_medium/_heavy) - a reminder
    # that milsymbol's own internal naming is not a reliable stand-in
    # for the standard's actual text, even for something as small as a
    # sub-variant label.
    #
    # Sub-sub-variants beyond this one level (e.g. the SAM launcher's
    # own TLAR/TELAR mounting variants nested inside its own weight-class
    # variants, or trailer/medevac-combo compound vehicle codes) are
    # still deliberately excluded as a clearer, more consistent curation
    # boundary: include a category's generic form and its direct weight/
    # size variants, not deeper compounds on top of those.
    "land_equipment": {
        # Weapons
        "weapon": "110000",
        "rifle": "110100",
        "rifle_single_shot": "110101",
        "rifle_semiautomatic": "110102",
        "rifle_automatic": "110103",
        "machine_gun": "110200",
        "machine_gun_light": "110201",
        "machine_gun_medium": "110202",
        "machine_gun_heavy": "110203",
        "grenade_launcher": "110300",
        "grenade_launcher_light": "110301",
        "grenade_launcher_medium": "110302",
        "grenade_launcher_heavy": "110303",
        "flame_thrower": "110400",
        "air_defense_gun": "110500",
        "air_defense_gun_light": "110501",
        "air_defense_gun_medium": "110502",
        "air_defense_gun_heavy": "110503",
        "antitank_gun": "110600",
        "antitank_gun_light": "110601",
        "antitank_gun_medium": "110602",
        "antitank_gun_heavy": "110603",
        "direct_fire_gun": "110700",
        "direct_fire_gun_light": "110701",
        "direct_fire_gun_medium": "110702",
        "direct_fire_gun_heavy": "110703",
        "recoilless_gun": "110800",
        "recoilless_gun_light": "110801",
        "recoilless_gun_medium": "110802",
        "recoilless_gun_heavy": "110803",
        "howitzer": "110900",
        "howitzer_light": "110901",
        "howitzer_medium": "110902",
        "howitzer_heavy": "110903",
        "missile_launcher": "111000",
        "missile_launcher_light": "111001",
        "missile_launcher_medium": "111002",
        "missile_launcher_heavy": "111003",
        "air_defense_missile_launcher_surface_to_air": "111100",
        "air_defense_missile_launcher_surface_to_air_light": "111101",
        "air_defense_missile_launcher_surface_to_air_medium": "111104",
        "air_defense_missile_launcher_surface_to_air_heavy": "111107",
        "antitank_missile_launcher": "111200",
        "antitank_missile_launcher_light": "111201",
        "antitank_missile_launcher_medium": "111202",
        "antitank_missile_launcher_heavy": "111203",
        "surface_to_surface_missile_launcher": "111300",
        "surface_to_surface_missile_launcher_light": "111301",
        "surface_to_surface_missile_launcher_medium": "111302",
        "surface_to_surface_missile_launcher_heavy": "111303",
        "mortar": "111400",
        "mortar_light": "111401",
        "mortar_medium": "111402",
        "mortar_heavy": "111403",
        "single_rocket_launcher": "111500",
        "single_rocket_launcher_light": "111501",
        "single_rocket_launcher_medium": "111502",
        "single_rocket_launcher_heavy": "111503",
        "multiple_rocket_launcher": "111600",
        "multiple_rocket_launcher_light": "111601",
        "multiple_rocket_launcher_medium": "111602",
        "multiple_rocket_launcher_heavy": "111603",
        "antitank_rocket_launcher": "111700",
        "antitank_rocket_launcher_light": "111701",
        "antitank_rocket_launcher_medium": "111702",
        "antitank_rocket_launcher_heavy": "111703",
        "non_lethal_weapon": "111800",
        "taser": "111900",
        "water_cannon": "112000",
        # Vehicles / armor
        "armoured_vehicle": "120100",
        "armored_fighting_vehicle": "120101",
        "armored_fighting_vehicle_command_and_control": "120102",
        "armored_personnel_carrier": "120103",
        "armored_personnel_carrier_medical_evacuation": "120104",
        "tank": "120200",
        "tank_light": "120201",
        "tank_medium": "120202",
        "tank_heavy": "120203",
        "tank_recovery_vehicle": "120300",
        # Engineer
        "bridge": "130100",
        "fixed_bridge": "130300",
        "folding_girder_bridge": "130500",
        "hollow_deck_bridge": "130600",
        "drilling": "130700",
        "earthmover": "130800",
        "multifunctional_earthmover_digger": "130801",
        "mine_clearing_equipment": "130900",
        "mine_clearing_equipment_tank": "130902",
        "mine_laying": "131000",
        "dozer": "131100",
        "dozer_armored": "131101",
        # Transport
        "utility_vehicle": "140100",
        "bus": "140500",
        "semi_trailer_truck": "140600",
        "semi_trailer_truck_light": "140601",
        "semi_trailer_truck_medium": "140602",
        "semi_trailer_truck_heavy": "140603",
        "train_locomotive": "150100",
        "railcar": "150200",
        # Civilian vehicles
        "automobile": "160100",
        "automobile_light": "160101",
        "automobile_medium": "160102",
        "automobile_heavy": "160103",
        "open_bed_truck": "160200",
        "open_bed_truck_light": "160201",
        "open_bed_truck_medium": "160202",
        "open_bed_truck_heavy": "160203",
        "multiple_passenger_vehicle": "160300",
        "multiple_passenger_vehicle_light": "160301",
        "multiple_passenger_vehicle_medium": "160302",
        "multiple_passenger_vehicle_heavy": "160303",
        "civilian_utility_vehicle": "160400",
        "civilian_utility_vehicle_light": "160401",
        "civilian_utility_vehicle_medium": "160402",
        "civilian_utility_vehicle_heavy": "160403",
        "jeep_type_vehicle": "160500",
        "jeep_type_vehicle_light": "160501",
        "jeep_type_vehicle_medium": "160502",
        "jeep_type_vehicle_heavy": "160503",
        "known_insurgent_vehicle": "160800",
        # Law enforcement - Table A-XXV's full 12-entity family, in the
        # standard's own code order. 170100 and 170500-171100 added
        # 2026-08-18: the first curation stopped after DEA, which left a
        # family that LOOKED complete (generic + three agencies) while
        # omitting eight entries milsymbol draws perfectly well. All
        # twelve confirmed renderable by hashing each SVG against a
        # known-bogus code's bare frame.
        #
        # This set's tail does NOT match the other two law-enforcement
        # families: 171000 is Coast Guard here, where Activities (1315xx)
        # and Land Installation (1121xx) have Prison / Law Enforcement
        # Vessel and no Coast Guard at all. Read Table A-XXV, never
        # another set's list.
        "law_enforcement": "170000",
        "bureau_of_alcohol_tobacco_firearms_and_explosives": "170100",
        "border_patrol": "170200",
        "customs_service": "170300",
        # Table A-XXV reads "Drug Enforcement Administration (DEA)". The
        # key keeps its shipped "..._agency" spelling so features already
        # saved by 1.0.3 and earlier still resolve; only the label is
        # corrected to the standard's wording.
        "drug_enforcement_agency": "170400",
        "department_of_justice": "170500",
        "federal_bureau_of_investigation": "170600",
        "police": "170700",
        # "secret" here is the US Secret Service, a MIL-STD-2525D entity
        # name - not a credential. Suppressions are for the scanners' own
        # keyword heuristics (1.0.0's automated review, 2026-08-17).
        "united_states_secret_service": "170800",  # nosec B105 # pragma: allowlist secret
        "transportation_security_administration": "170900",
        "coast_guard": "171000",
        "us_marshals_service": "171100",
        # Missile support
        "missile_support": "190000",
        "missile_transloader": "190100",
        "missile_transporter": "190200",
        "missile_crane_loading_device": "190300",
        # Other equipment
        "pack_animal": "180000",
        "bomb": "200200",
        "booby_trap": "200300",
        "cbrn_equipment": "200400",
        "computer_system": "200500",
        "command_launch_equipment": "200600",
        "generator_set": "200700",
        "laser": "201000",
        "tent": "201300",
        "land_mine": "210100",
        "antipersonnel_land_mine": "210200",
        "antitank_mine": "210300",
        "improvised_explosive_device": "210400",
        "sensor": "220100",
        "radar": "220300",
        "fire_protection": "230200",
        "manual_track": "240000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/landinstallation.js (symbolSet == "20") - a
    # curated subset (131 total in the source), spanning government/
    # public-safety, agriculture, financial, commercial/industrial,
    # educational, utility, government-site, postal, public-venue,
    # telecommunications, transportation and water infrastructure.
    #
    # Expanded 2026-08-08 alongside the land_equipment fix above: unlike
    # Equipment, Installation's own sub-codes are genuinely distinct
    # SIBLING facility types within a category (e.g. bank/ATM/bullion
    # storage/federal reserve bank are four different icons, not a
    # light/medium/heavy axis on one icon) - a milder form of the same
    # "picked some siblings, not the family" gap, fixed here by filling
    # in each category's remaining meaningful siblings. Still not
    # exhaustive - genuinely near-duplicate/reserved codes were left out
    # (e.g. 120204/120700/121202/112101, all empty in the source;
    # 120501/120502, which duplicate 120500's own icon; 121410, which
    # duplicates 121400's).
    "land_installation": {
        "military": "110000",
        "aircraft_production_and_assembly": "110100",
        "cbrn": "110600",
        "equipment_manufacture": "110800",
        "government": "110900",
        "mine": "111300",
        "printed_media": "111600",
        "safe_house": "111700",
        # Law enforcement - Table A-XXVII's full 13-entity family. ATF
        # (112101) and Police (112107) added 2026-08-18; both were
        # simply absent, which left two holes in an otherwise contiguous
        # run of codes.
        #
        # 112111 is **Coast Guard** in the standard, not "Law
        # Enforcement Vessel" - that row does not exist in this table at
        # all. The key below keeps its shipped (wrong) spelling because
        # it is written into the "entity" field of features users have
        # already saved; the label a user actually reads was corrected
        # 2026-08-18. The standard's real Law Enforcement Vessel is Sea
        # Surface 140300, which ENTITIES["sea_surface"] has right. Do not
        # "align" these two by changing the sea surface one.
        "law_enforcement": "112100",
        "bureau_of_alcohol_tobacco_firearms_and_explosives": "112101",
        "border_patrol": "112102",
        "customs_service": "112103",
        # Table A-XXVII reads "Drug Enforcement Administration (DEA)";
        # key keeps its shipped spelling, label corrected 2026-08-18.
        "drug_enforcement_agency": "112104",
        "department_of_justice": "112105",
        "federal_bureau_of_investigation": "112106",
        "police": "112107",
        "prison": "112108",
        # "secret" here is the US Secret Service, a MIL-STD-2525D entity
        # name - not a credential. Suppressions are for the scanners' own
        # keyword heuristics (1.0.0's automated review, 2026-08-17).
        "secret_service": "112109",  # nosec B105 # pragma: allowlist secret
        # Table A-XXVII reads "Transportation Security Administration";
        # key keeps its shipped spelling, label corrected 2026-08-18.
        "transportation_security_agency": "112110",
        # Coast Guard - see the note above on this key's name.
        "law_enforcement_vessel": "112111",
        "us_marshals_service": "112112",
        "emergency_operation": "112200",
        "fire_protection": "112201",
        "emergency_medical_operation": "112202",
        "home": "112300",
        "agriculture_and_food_infrastructure": "120100",
        "agricultural_laboratory": "120101",
        "animal_feedlot": "120102",
        "farm_ranch": "120104",
        "food_distribution": "120105",
        "food_distribution_production": "120106",
        "food_distribution_retail": "120107",
        "grain_storage": "120108",
        "banking_finance_and_insurance_infrastructure": "120200",
        "atm": "120201",
        "bank": "120202",
        "bullion_storage": "120203",
        "federal_reserve_bank": "120205",
        "financial_exchange": "120206",
        "financial_services_other": "120207",
        "commercial_infrastructure": "120300",
        "chemical_plant": "120301",
        "firearms_manufacturer": "120302",
        "firearms_retailer": "120303",
        "hazardous_material_production": "120304",
        "hazardous_material_storage": "120305",
        "industrial_site": "120306",
        "landfill": "120307",
        "pharmaceutical_manufacturer": "120308",
        "contaminated_hazardous_waste_site": "120309",
        "toxic_release_inventory": "120310",
        "educational_facilities_infrastructure": "120400",
        "college_university": "120401",
        "school": "120402",
        "electric_power": "120500",
        "natural_gas_facility": "120503",
        "propane_facility": "120506",
        "government_site_infrastructure": "120600",
        "medical": "120701",
        "medical_treatment_facility": "120702",
        "military_infrastructure": "120800",
        "base": "120802",
        "airport": "120803",
        "postal_service_infrastructure": "120900",
        "postal_distribution_center": "120901",
        "post_office": "120902",
        "public_venues_infrastructure": "121000",
        "enclosed_facility": "121001",
        "open_facility": "121002",
        "recreational_area": "121003",
        "religious_institution": "121004",
        "special_needs_infrastructure": "121100",
        "adult_day_care": "121101",
        "child_day_care": "121102",
        "elder_care": "121103",
        "telecommunications_infrastructure": "121200",
        "broadcast_transmitter_antenna": "121201",
        "telecommunications_tower": "121203",
        "transportation": "121300",
        "air_traffic_control_facility": "121302",
        "ferry": "121304",
        "helicopter_landing_site": "121305",
        "maintenance": "121306",
        "railhead": "121307",
        "rest_stop": "121308",
        "toll_facility": "121311",
        "traffic_inspection_facility": "121312",
        "tunnel": "121313",
        "water": "121400",
        "control_valve": "121401",
        "dam": "121402",
        "discharge_outfall": "121403",
        "ground_water_well": "121404",
        "pumping_station": "121405",
        "reservoir": "121406",
        "storage_tower": "121407",
        "surface_water_intake": "121408",
        "wastewater_treatment_facility": "121409",
        "water_purification": "121411",
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/air.js
    # (symbolSet == "01") - cross-checked directly against the standard's
    # own Table C-III (MIL-STD-2525D Appendix C, Air Equipment and
    # Platform icons) during the appendix-by-appendix completion pass.
    # Replaced 2026-08-08: the previous version here was a curated
    # 19-entry subset built for unit_layer.py's shared multi-domain
    # layer, with two entries renamed purely to dodge a key collision
    # with ground_unit's own vocabulary in that one combined dropdown.
    # Now that Air has its own dedicated layer (air_layer.py, no
    # collision risk), this is milsymbol's FULL entity list (every code
    # 110000-140000, skipping only 110106 - milsymbol's own source marks
    # it "{Reserved for Future Use}" with an empty icon list) using
    # milsymbol's own icon labels for the key names.
    "air": {
        "military": "110000",
        "fixed_wing": "110100",
        "medical_evacuation": "110101",
        "attack_strike": "110102",
        "bomber": "110103",
        "fighter": "110104",
        "fighter_bomber": "110105",
        "cargo": "110107",
        "jammer_electronic_countermeasures": "110108",
        "tanker": "110109",
        "patrol": "110110",
        "reconnaissance": "110111",
        "trainer": "110112",
        "utility": "110113",
        "vstol": "110114",
        "airborne_command_post": "110115",
        "airborne_early_warning": "110116",
        "antisurface_warfare": "110117",
        "antisubmarine_warfare": "110118",
        "communications": "110119",
        "combat_search_and_rescue": "110120",
        "electronic_support": "110121",
        "government": "110122",
        "mine_countermeasures": "110123",
        "personnel_recovery": "110124",
        "search_and_rescue": "110125",
        "special_operations_forces": "110126",
        "ultra_light": "110127",
        "photographic_reconnaissance": "110128",
        "vip": "110129",
        "suppression_of_enemy_air_defense": "110130",
        "passenger": "110131",
        "escort": "110132",
        "electronic_attack": "110133",
        "military_rotary_wing": "110200",
        "unmanned_aerial_vehicle": "110300",
        "vertical_takeoff_uav": "110400",
        "military_balloon": "110500",
        "military_airship": "110600",
        "tethered_lighter_than_air": "110700",
        "civilian": "120000",
        "civilian_fixed_wing": "120100",
        "civilian_rotary_wing": "120200",
        "civilian_unmanned_aerial_vehicle": "120300",
        "civilian_balloon": "120400",
        "civilian_airship": "120500",
        "civilian_tethered_lighter_than_air": "120600",
        "civilian_medical_evacuation": "120700",
        "weapon": "130000",
        "bomb": "130100",
        "underwater_decoy": "130200",
        "manual_track": "140000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/airmissile.js (symbolSet == "02" - Table
    # A-III: Air Missile). Only one entity code exists - see the same
    # note on ENTITIES["space_missile"] above (sector modifiers aren't
    # exposed for any symbol set yet).
    "air_missile": {
        "missile": "110000",
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/sea.js
    # (symbolSet == "30") - the FULL 93-entity vocabulary (verified via
    # a complete multi-line-aware parse of sea.js, same method used to
    # catch and fix the Land Equipment/Installation gaps), not a curated
    # subset - Sea Surface's own source is small enough (93 vs Land
    # Unit's 219/Land Equipment's 229) that full coverage is the more
    # consistent choice, avoiding a repeat of that same "curate now,
    # revisit later" gap. Includes Table E-VI/E-VII's own special
    # entries: "own_ship" (150000, CIC-internal, friend-only, 1L
    # diameter) and "fused_track" (160000, pending-status track still
    # being classified).
    "sea_surface": {
        "military": "110000",
        "combatant": "120000",
        "carrier": "120100",
        "surface_combatant_line": "120200",
        "battleship": "120201",
        "cruiser_guided_missile": "120202",
        "destroyer": "120203",
        "frigate": "120204",
        "corvette": "120205",
        "littoral_combatant_ship": "120206",
        "amphibious_warfare_ship": "120300",
        "amphibious_force_flagship": "120301",
        "amphibious_assault": "120302",
        "amphibious_assault_ship_general": "120303",
        "amphibious_assault_ship_multi_purpose": "120304",
        "amphibious_assault_ship_helicopter": "120305",
        "amphibious_transport_dock": "120306",
        "landing_ship": "120307",
        "landing_craft": "120308",
        "mine_warfare_vessel": "120400",
        "minelayer": "120401",
        "minesweeper": "120402",
        "minesweeper_drone": "120403",
        "minehunter": "120404",
        "mine_countermeasures": "120405",
        "mine_countermeasure_support_ship": "120406",
        "patrol": "120500",
        "patrol_craft": "120501",
        "patrol_gun": "120502",
        "sea_surface_decoy": "120600",
        "unmanned_surface_water_vehicle": "120700",
        "military_speedboat": "120800",
        "military_speedboat_rigid_hull_inflatable_boat": "120801",
        "military_jetski": "120900",
        "navy_task_organization_unit": "121000",
        "navy_task_element": "121001",
        "navy_task_force": "121002",
        "navy_task_group": "121003",
        "navy_task_unit": "121004",
        "convoy": "121005",
        "radar": "121100",
        "noncombatant": "130000",
        "auxiliary_ship": "130100",
        "ammunition_ship": "130101",
        "stores_ship": "130102",
        "auxiliary_flag_or_command_ship": "130103",
        "intelligence_collector": "130104",
        "ocean_research_ship": "130105",
        "survey_ship": "130106",
        "hospital_ship": "130107",
        "cargo_ship": "130108",
        "combat_support_ship_fast": "130109",
        "oiler_replenishment": "130110",
        "repair_ship": "130111",
        "submarine_tender": "130112",
        "tug_ocean_going": "130113",
        "service_craft_yard_general": "130200",
        "barge_not_self_propelled": "130201",
        "barge_self_propelled": "130202",
        "tug_harbour": "130203",
        "launch": "130204",
        "civilian": "140000",
        "merchant_ship_general": "140100",
        "cargo_general": "140101",
        "container_ship": "140102",
        "dredge": "140103",
        "roll_on_roll_off": "140104",
        "ferry": "140105",
        "heavy_lift": "140106",
        "hovercraft": "140107",
        "merchant_ship_lash_carrier": "140108",
        "oiler_tanker": "140109",
        "passenger_ship": "140110",
        "tug_ocean_going_civilian": "140111",
        "tow": "140112",
        "transport_ship_hazardous_material": "140113",
        "junk_dhow": "140114",
        "barge_not_self_propelled_civilian": "140115",
        "hospital_ship_civilian": "140116",
        "fishing_vessel": "140200",
        "drifter": "140201",
        "trawler": "140202",
        "fishing_vessel_dredge": "140203",
        "law_enforcement_vessel": "140300",
        "leisure_craft_sailing_boat": "140400",
        "leisure_craft_motorized": "140500",
        "leisure_craft_motorized_rigid_hull_inflatable_boat": "140501",
        "leisure_craft_motorized_speedboat": "140502",
        "leisure_craft_jetski": "140600",
        "civilian_unmanned_surface_water_vehicle": "140700",
        "own_ship": "150000",
        "fused_track": "160000",
        "manual_track": "170000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/subsurface.js (symbolSet == "35") - the FULL
    # 22-entity vocabulary (small enough for full coverage, same policy
    # as Sea Surface - see that dict's own comment for why this replaced
    # an earlier curated 8-entry subset). This is also where the user's
    # originally-reported bug lived ("Military Generic is in Air, Sea
    # Surface [but not working for Subsurface]") - the code itself
    # ("military": "110000") was already correct and matches
    # subsurface.js's own "SU.IC.MILITARY" exactly; the actual root
    # cause was almost certainly the old shared multi-domain layer's
    # ValueRelation-based cascading "Entity" dropdown (unit_layer.py),
    # which this module's own docstring already flags as having a
    # confirmed native-crash risk during development - resolved
    # structurally by giving Subsurface its own dedicated layer with a
    # plain ValueMap dropdown (subsurface_layer.py), not by changing
    # this code, which didn't need it.
    "subsurface": {
        "military": "110000",
        "submarine": "110100",
        "submarine_surfaced": "110101",
        "submarine_snorkeling": "110102",
        "submarine_bottomed": "110103",
        "other_submersible": "110200",
        "non_submarine": "110300",
        "autonomous_underwater_vehicle": "110400",
        "diver_military": "110500",
        "civilian": "120000",
        "submersible_civilian": "120100",
        "autonomous_underwater_vehicle_civilian": "120200",
        "diver_civilian": "120300",
        "underwater_weapon": "130000",
        "torpedo": "130100",
        "improvised_explosive_device": "130200",
        "underwater_decoy": "130300",
        "echo_tracker_classifier": "140000",
        "fused_track": "150000",
        "manual_track": "160000",
        "seabed_installation_military": "200000",
        "seabed_installation_non_military": "210000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/minewarfare.js (symbolSet == "36") - the FULL
    # 64-entity vocabulary (excludes only "140000", which milsymbol's own
    # source marks reserved with an empty icon list - the same pattern
    # as Air's "110106"). Includes MILCO's (Mine-Like Contact) own
    # confidence-level 1-5 sub-variants for each position (general/
    # bottom/moored/floating) - the exact kind of systematic sub-code
    # axis that was missed for Land Equipment's own weight-class variants
    # before the user caught it; caught here up front by the same full
    # multi-line-aware parse. No
    # sector 1/2 modifiers exist for this symbol set at all (milsymbol's
    # own source has zero sIdm1/sIdm2 entries here).
    "mine_warfare": {
        "sea_mine": "110000",
        "sea_mine_bottom": "110100",
        "sea_mine_moored": "110200",
        "sea_mine_floating": "110300",
        "sea_mine_rising": "110400",
        "sea_mine_other_position": "110500",
        "sea_mine_kingfisher": "110600",
        "sea_mine_small_object": "110700",
        "sea_mine_exercise": "110800",
        "sea_mine_exercise_bottom": "110801",
        "sea_mine_exercise_moored": "110802",
        "sea_mine_exercise_floating": "110803",
        "sea_mine_exercise_rising": "110804",
        "sea_mine_neutralized": "110900",
        "sea_mine_neutralized_bottom": "110901",
        "sea_mine_neutralized_moored": "110902",
        "sea_mine_neutralized_floating": "110903",
        "sea_mine_neutralized_rising": "110904",
        "sea_mine_other_position_neutralized": "110905",
        "unexploded_explosive_ordnance": "120000",
        "sea_mine_decoy": "130000",
        "sea_mine_decoy_bottom_ground": "130100",
        "sea_mine_decoy_moored": "130200",
        "sea_mine_milco": "140100",
        "sea_mine_milco_confidence_1": "140101",
        "sea_mine_milco_confidence_2": "140102",
        "sea_mine_milco_confidence_3": "140103",
        "sea_mine_milco_confidence_4": "140104",
        "sea_mine_milco_confidence_5": "140105",
        "sea_mine_milco_bottom": "140200",
        "sea_mine_milco_bottom_confidence_1": "140201",
        "sea_mine_milco_bottom_confidence_2": "140202",
        "sea_mine_milco_bottom_confidence_3": "140203",
        "sea_mine_milco_bottom_confidence_4": "140204",
        "sea_mine_milco_bottom_confidence_5": "140205",
        "sea_mine_milco_moored": "140300",
        "sea_mine_milco_moored_confidence_1": "140301",
        "sea_mine_milco_moored_confidence_2": "140302",
        "sea_mine_milco_moored_confidence_3": "140303",
        "sea_mine_milco_moored_confidence_4": "140304",
        "sea_mine_milco_moored_confidence_5": "140305",
        "sea_mine_milco_floating": "140400",
        "sea_mine_milco_floating_confidence_1": "140401",
        "sea_mine_milco_floating_confidence_2": "140402",
        "sea_mine_milco_floating_confidence_3": "140403",
        "sea_mine_milco_floating_confidence_4": "140404",
        "sea_mine_milco_floating_confidence_5": "140405",
        "sea_mine_milec": "150000",
        "sea_mine_milec_bottom": "150100",
        "sea_mine_milec_moored": "150200",
        "sea_mine_milec_floating": "150300",
        "sea_mine_negative_reacquisition": "160000",
        "sea_mine_negative_reacquisition_bottom": "160100",
        "sea_mine_negative_reacquisition_moored": "160200",
        "sea_mine_negative_reacquisition_floating": "160300",
        "sea_mine_general_obstructor": "170000",
        "sea_mine_general_obstructor_neutralized": "170100",
        "sea_mine_anchor": "180000",
        "sea_mine_non_mine_like_contact": "190000",
        "sea_mine_non_mine_like_contact_bottom": "190100",
        "sea_mine_non_mine_like_contact_moored": "190200",
        "sea_mine_non_mine_like_contact_floating": "190300",
        "environmental_report_location": "200000",
        "dive_report_location": "210000",
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
        "coordinating_point": "130600",
        "decision_point": "130700",
        "distress_call": "130800",
        "entry_control_point": "130900",
        "fly_to_point_sonobuoy": "131001",
        "fly_to_point_weapon": "131002",
        "fly_to_point_normal": "131003",
        "linkup_point": "131100",
        "passage_point": "131200",
        "point_of_interest": "131300",
        "point_of_interest_launch_event": "131301",
        "rally_point": "131400",
        "release_point": "131500",
        "start_point": "131600",
        "special_point": "131700",
        "waypoint": "131800",
        # **Table H-XIV names two of its own Reference Points the same
        # things**, at 213700 and 214800, and until 2026-08-14 both
        # tables used the same two keys here. A dict keeps the last
        # one, so these two H-VI codes were being silently overwritten
        # by the maritime pair and the C2 Measures layer had been
        # drawing MARITIME icons for its own Special Point and
        # Waypoint. The maritime keys now carry that module's own
        # "_reference" group suffix, the same way its Navigational
        # Reference Point already did for the same reason. Found by
        # tests/test_control_measure_point_vocabulary.py, which is
        # exactly what that sweep is for.
        # Table H-VI (Command and control points) ends here, at 131900 -
        # confirmed 2026-08-10 by reading the actual standard text
        # directly (reference/MIL-STD-2525D.pdf), after the project
        # maintainer questioned two entries that used to sit right here,
        # "target_handover" (132000) and "key_terrain" (132100). Neither
        # exists anywhere in Table H-VI, or anywhere in the standard at
        # all under any name/code - "target_handover"/132000 doesn't
        # even exist in the vendored milsymbol.js's own dispatch table,
        # and while milsymbol.js DOES define an icon for 132100 ("TP.KEY
        # TERRAIN"), that code and name appear nowhere in the actual
        # MIL-STD-2525D text - a non-standard addition of milsymbol's
        # own, not a real symbol this plugin should expose as MIL-STD-
        # 2525D-compliant. Both removed outright, not just relabelled -
        # the same "verify against the real standard, not just
        # milsymbol.js" discipline this project applies everywhere else.
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
        # Fires
        "point_target": "240601",
        "nuclear_target": "240602",
        "fire_support_station": "240900",
        "firing_point": "250100",
        "hide_point": "250200",
        "launch_point": "250300",
        "reload_point": "250400",
        "survey_control_point": "250500",
        # Protection (obstacles, mines, shelters, CBRN events)
        "abatis": "280100",
        "antipersonnel_mine": "280200",
        "antipersonnel_mine_directional": "280201",
        "antitank_mine": "280300",
        "antitank_mine_anti_handling": "280400",
        "wide_area_antitank_mine": "280500",
        "unspecified_mine": "280600",
        "booby_trap": "280700",
        "engineer_regulating_point": "280800",
        # Tetrahedrons/Dragons Teeth (281900 is the parent
        # heading row, template "N/A") and Vertical
        # Obstructions (282000, likewise) - Table H-XIX.
        "obstacle_fixed_prefabricated": "281901",
        "obstacle_movable": "281902",
        "obstacle_movable_prefabricated": "281903",
        "tower_low": "282001",
        "tower_high": "282002",
        "shelter": "280900",
        "shelter_above_ground": "281000",
        "shelter_below_ground": "281100",
        "fort": "281200",
        # CBRN defense - Table H-XXI (Mini-Phase H18). Every one of
        # these 18 is backed by a real milsymbol icon, verified against
        # its own src/numbersidc/sidc/control-measure.js entry rather
        # than assumed from the code alone.
        "chemical_event": "281300",
        "chemical_toxic_industrial_material": "281301",
        "biological_event": "281400",
        "biological_toxic_industrial_material": "281401",
        "nuclear_event": "281500",
        # 281600 shares milsymbol's own TP.NUCLEAR EVENT icon with
        # 281500 - two distinct codes, one glyph, which is the
        # standard's own doing rather than a mapping error here.
        "nuclear_fallout_producing_event": "281600",
        "radiological_event": "281700",
        "radiological_toxic_industrial_material": "281701",
        "decontamination_point": "281800",
        "decontamination_point_alternate": "281801",
        "decontamination_point_equipment": "281802",
        "decontamination_point_troops": "281803",
        "decontamination_point_equipment_troops": "281804",
        "decontamination_point_operational": "281805",
        "decontamination_point_thorough": "281806",
        "decontamination_point_main_equipment": "281807",
        "decontamination_point_forward_troop": "281808",
        "decontamination_point_wounded_personnel": "281809",
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
        # Table H-XXIII's own sixteen supply classes (Mini-Phase H20,
        # 2026-08-14). The table splits them by standard, not just by
        # number: 321701-321706 are the NATO classes, each citing its
        # own STANAG 2961 definition, and 321707-321716 are the US
        # classes I-X. Two different vocabularies that happen to share
        # roman numerals, so the keys say which is which rather than
        # leaving "class_i" ambiguous.
        "supply_point_nato_class_i": "321701",
        "supply_point_nato_class_ii": "321702",
        "supply_point_nato_class_iii": "321703",
        "supply_point_nato_class_iv": "321704",
        "supply_point_nato_class_v": "321705",
        "supply_point_nato_multiple_class": "321706",
        "supply_point_us_class_i": "321707",
        "supply_point_us_class_ii": "321708",
        "supply_point_us_class_iii": "321709",
        "supply_point_us_class_iv": "321710",
        "supply_point_us_class_v": "321711",
        "supply_point_us_class_vi": "321712",
        "supply_point_us_class_vii": "321713",
        "supply_point_us_class_viii": "321714",
        "supply_point_us_class_ix": "321715",
        "supply_point_us_class_x": "321716",
        "medical_supply_point": "321800",
        # Mission tasks (point form - a future H.5.26 mission-task
        # module separately covers the arrow/line-graphic form some of
        # these same task names also take, a different rendering
        # mechanism)
        "destroy_point": "340900",
        "interdict_point": "341400",
        "neutralize_point": "341600",
        # Airspace control points (Table H-XIII/H.5.15, Mini-Phase H7,
        # 2026-08-09) - confirmed present in milsymbol.js under each of
        # these exact numeric codes (see airspace_control_measures.py's
        # own docstring for the one point skipped, Base Defense Zone,
        # and for milsymbol's own "TP.PULL-UP POINT" display-name quirk
        # for 180400).
        #
        # 180000, the table's own generic "Airspace Control Points"
        # parent entry (printed page 459 - two vertical bars with a
        # filled centre circle), was missed on that first pass and added
        # 2026-08-12 when the whole family moved to its own layer. It is
        # present in milsymbol.js under this code as "TP.AIR CONTROL
        # POINT" - confusingly close to 180100's own "TP.AIR CONTROL
        # POINT (ACP)", but a genuinely different icon (bars + dot vs.
        # circle + "ACP" text), matching the standard's own two separate
        # template pictures.
        "airspace_control_points": "180000",
        "air_control_point": "180100",
        "communications_checkpoint": "180200",
        "downed_aircrew_pickup_point": "180300",
        "pop_up_point": "180400",
        "air_control_rendezvous": "180500",
        "tacan": "180600",
        "cap_station": "180700",
        "aew_station": "180800",
        "asw_fixed_wing_station": "180900",
        "strike_initial_point": "181000",
        "replenishment_station": "181100",
        "tanking": "181200",
        "asw_rotary_wing_station": "181300",
        "sucap_fixed_wing": "181400",
        "sucap_rotary_wing": "181500",
        "miw_fixed_wing": "181600",
        "miw_rotary_wing": "181700",
        "tomcat": "181800",
        "rescue": "181900",
        "unmanned_aerial_system": "182000",
        "vtua": "182100",
        "orbit": "182200",
        "orbit_figure_eight": "182300",
        "orbit_race_track": "182400",
        "orbit_random_closed": "182500",
        # Maritime control points (Table H-XIV/H.5.16, Mini-Phase H8/H9)
        # - printed pages 474-501, the FULL point vocabulary, expanded
        # 2026-08-12 from the 18-entry curated subset this started as.
        #
        # That original curation deliberately left out the sonobuoy and
        # anti-submarine-warfare fix/contact families as "more Navy/ASW-
        # specific", matching this dict's own standing note further up.
        # The project maintainer reversed that decision when moving the
        # whole family onto its own layer, having gone through the
        # table's own pages directly - so Sonobuoys (17 entries) and
        # Sub-Surface Warfare (17) are now built in full alongside the
        # rest. Grouped below by the table's OWN sub-headings, in its
        # own code order, which is also how the layer's dropdown reads.
        #
        # Confirmed present in milsymbol.js under each of these exact
        # numeric codes by direct probe. Four codes in the 474-501 range
        # are deliberately NOT here - see maritime_control_measures.py's
        # own docstring for the full reasoning on each: 210000 (the
        # table's own parent row, template "N/A", nothing to draw),
        # 211000/211200/211300 (marked "(AEGIS only)"), 217300
        # (milsymbol maps it to the WRONG icon and flags it TODO in its
        # own source) and 218400 (a TWO-anchor-point line symbol, not a
        # point at all).
        # General
        "plan_ship": "210100",
        "aim_point": "210200",
        "defended_asset": "210300",
        "drop_point": "210400",
        "entry_point": "210500",
        "air_detonation": "210600",
        "ground_zero": "210700",
        "impact_point": "210800",
        "predicted_impact_point": "210900",
        "missile_detection_point": "211100",
        # Sub-Surface Warfare
        "brief_contact": "211400",
        "datum_lost_contact": "211500",
        "bt_buoy_drop": "211600",
        "reported_bottomed_sub": "211700",
        "moving_haven": "211800",
        "screen_center": "211900",
        "lost_contact": "212000",
        "sinker": "212100",
        "trial_track": "212200",
        "acoustic_fix": "212300",
        "electromagnetic_fix": "212400",
        "electromagnetic_magnetic_anomaly_detection": "212500",
        "optical_fix": "212600",
        "formation": "212700",
        "harbor": "212800",
        "harbor_entrance_point": "212900",
        "harbor_entrance_point_a": "212901",
        "harbor_entrance_point_q": "212902",
        "harbor_entrance_point_x": "212903",
        "harbor_entrance_point_y": "212904",
        # Search
        "dip_position": "213000",
        "search": "213100",
        "search_area": "213200",
        "search_center": "213300",
        "navigational_reference_point": "213400",
        # Sonobuoys
        "sonobuoy": "213500",
        "ambient_noise_sonobuoy": "213501",
        "air_transportable_communication_sonobuoy": "213502",
        "barra_sonobuoy": "213503",
        "bathythermograph_transmitting_sonobuoy": "213504",
        "command_active_multi_beam_sonobuoy": "213505",
        "command_active_sonobuoy_system": "213506",
        "directional_frequency_analysis_and_recording_sonobuoy": "213507",
        "directional_command_active_sonobuoy_system": "213508",
        "expendable_reliable_acoustic_path_sonobuoy": "213509",
        "expired_sonobuoy": "213510",
        "kingpin_sonobuoy": "213511",
        "low_frequency_analysis_and_recording_sonobuoy": "213512",
        "pattern_center_sonobuoy": "213513",
        "range_only_sonobuoy": "213514",
        "vertical_line_array_directional_frequency_analysis_and_recording_sonobuoy": "213515",
        # Reference Points
        "reference_point": "213600",
        "special_point_reference": "213700",
        "navigational_reference_point_reference": "213800",
        "data_link_reference_point": "213900",
        "vital_area_center": "214100",
        "corridor_tab_point": "214200",
        "enemy_point": "214300",
        "marshall_point": "214400",
        "position_and_intended_movement": "214500",
        "pre_landfall_waypoint": "214600",
        "estimated_position": "214700",
        "waypoint_reference": "214800",
        # Subsurface Stations
        "general_subsurface_station": "214900",
        "submarine_subsurface_station": "215000",
        "submarine_antisubmarine_warfare_subsurface_station": "215100",
        "unmanned_underwater_vehicle_subsurface_station": "215200",
        "antisubmarine_warfare_unmanned_underwater_vehicle_subsurface_station": "215300",
        "mine_warfare_unmanned_underwater_vehicle_subsurface_station": "215400",
        "surface_warfare_unmanned_underwater_vehicle_subsurface_station": "215500",
        # Surface Stations
        "general_surface_station": "215600",
        "antisubmarine_warfare_surface_station": "215700",
        "mine_warfare_surface_station": "215800",
        "non_combatant_surface_station": "215900",
        "picket_surface_station": "216000",
        "rendezvous_surface_station": "216100",
        "replenishment_at_sea_surface_station": "216200",
        "rescue_surface_station": "216300",
        "surface_warfare_surface_station": "216400",
        "unmanned_underwater_vehicle_surface_station": "216500",
        "antisubmarine_warfare_unmanned_underwater_vehicle_surface_station": "216600",
        "mine_warfare_unmanned_underwater_vehicle_surface_station": "216700",
        "remote_multi_mission_vehicle_unmanned_underwater_vehicle_surface_station": "216800",
        "surface_warfare_unmanned_underwater_vehicle_surface_station": "216900",
        "shore_control_station": "217000",
        # Routes
        "general_route": "217100",
        "diversion_route": "217200",
        "picket_route": "217400",
        "point_r_route": "217500",
        "rendezvous_route": "217600",
        "waypoint_route": "217700",
        "clutter_stationary_or_cease_reporting": "217800",
        "tentative_or_provisional_track": "217900",
        # Emergency
        "distressed_vessel": "218000",
        "downed_aircraft": "218100",
        "person_in_water_bailout": "218200",
        # Hazard
        "iceberg": "218300",
        "oil_rig": "218500",
        "sea_mine_like_contact": "218600",
        # Sea Subsurface Returns
        "bottom_return_non_mine_mine_like_bottom_object": "218700",
        "bottom_return_installation_manmade": "218800",
        "marine_life": "218900",
        "sea_anomaly": "219000",
        "bottom_return_non_milco_wreck_dangerous": "219100",
        "bottom_return_non_milco_wreck_non_dangerous": "219200",
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/space.js
    # (symbolSet == "05") - cross-checked directly against the standard's
    # own Table B-III (MIL-STD-2525D Appendix B, Space Equipment and
    # Platform icons) during the appendix-by-appendix completion pass,
    # not just copied from milsymbol.js. Unlike ground_unit's curated
    # subset, this is the FULL vocabulary space.js exposes - nothing here
    # reads as peripheral/administrative the way band/postal did for
    # ground units, so nothing was excluded.
    "space": {
        "military": "110000",
        "space_vehicle": "110100",
        "re_entry_vehicle": "110200",
        "planet_lander": "110300",
        "orbiter_shuttle": "110400",
        "capsule": "110500",
        "satellite_general": "110600",
        "satellite": "110700",
        "antisatellite_weapon": "110800",
        "astronomical_satellite": "110900",
        "biosatellite": "111000",
        "communications_satellite": "111100",
        "earth_observation_satellite": "111200",
        "miniaturized_satellite": "111300",
        "navigational_satellite": "111400",
        "reconnaissance_satellite": "111500",
        "space_station": "111600",
        "tethered_satellite": "111700",
        "weather_satellite": "111800",
        "space_launch_vehicle": "111900",
        "civilian": "120000",
        "civilian_orbiter_shuttle": "120100",
        "civilian_capsule": "120200",
        "civilian_satellite": "120300",
        "civilian_astronomical_satellite": "120400",
        "civilian_biosatellite": "120500",
        "civilian_communications_satellite": "120600",
        "civilian_earth_observation_satellite": "120700",
        "civilian_miniaturized_satellite": "120800",
        "civilian_navigational_satellite": "120900",
        "civilian_space_station": "121000",
        "civilian_tethered_satellite": "121100",
        "civilian_weather_satellite": "121200",
        "civilian_planetary_lander": "121300",
        "civilian_space_vehicle": "121400",
        "manual_track": "130000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/spacemissile.js (symbolSet == "06"). Only one
    # entity code exists at this level - every distinction (ballistic/
    # interceptor/hypersonic, range class) lives in sector 1/2 modifiers
    # - see MODIFIERS["space_missile"] below.
    "space_missile": {
        "missile": "110000",
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/activites.js (symbolSet == "40") - the FULL
    # 153-entity vocabulary, cross-checked against the standard's own
    # Table G-III (Appendix G, Activities icons, printed pages 357-363).
    # Labels below use the standard's own DESCRIPTION-column wording
    # where it was legible in the PDF and meaningfully different from
    # milsymbol's internal icon-part constant strings (e.g. milsymbol's
    # "ST.IC.RIOT" is the standard's "Riot" - close enough to keep as-is;
    # this is NOT the same kind of mismatch as Land Equipment's short/
    # long-range-vs-light/medium/heavy bug, where the internal name
    # encoded a genuinely different, wrong category - here milsymbol's
    # constants are already literal descriptive entity names, just
    # sometimes abbreviated). Includes the hierarchy-only parent codes
    # (110000/130000/150000/180000/etc.) that milsymbol's own source
    # marks with an empty icon list ("No icon is associated with this
    # entity. It is for hierarchal purposes only.", per Table G-III's own
    # remarks column) - these still render as a valid frame-only symbol,
    # same as similar hierarchy-only codes elsewhere (e.g. Air's/Space's
    # top-level "military").
    "activities": {
        "criminal_activity_incident": "110000",
        "criminal_activity_incident_type": "110100",
        "arrest": "110101",
        "arson_fire": "110102",
        "attempted_criminal_activity": "110103",
        "drive_by_shooting": "110104",
        "drug_related_activities": "110105",
        "extortion": "110106",
        "graffiti": "110107",
        "killing_victim": "110108",
        "poisoning": "110109",
        "riot": "110110",
        "booby_trap": "110111",
        "eviction": "110112",
        "black_marketing": "110113",
        "vandalism_loot_ransack_plunder_sack": "110114",
        "jail_break": "110115",
        "robbery": "110116",
        "theft": "110117",
        "burglary": "110118",
        "smuggling": "110119",
        "rock_throwing": "110120",
        "dead_body": "110121",
        "sabotage": "110122",
        "threat_of_criminal_activity": "110123",
        "bomb": "110200",
        "bomb_threat": "110201",
        "ied": "110300",
        "ied_explosion": "110301",
        "premature_ied_explosion": "110302",
        "ied_supply_cache": "110303",
        "individual_with_ied": "110304",
        "shooting": "110400",
        "sniping": "110401",
        "illegal_drug_operation": "110500",
        "drug_trafficking": "110501",
        "drug_laboratory": "110502",
        "explosion": "110600",
        "grenade_explosion": "110601",
        "incendiary_explosion": "110602",
        "mine_explosion": "110603",
        "mortar_fire_explosion": "110604",
        "rocket_explosion": "110605",
        "bomb_explosion": "110606",
        "home": "110700",
        "civil_disturbance": "120000",
        "demonstration": "120100",
        "operations": "130000",
        "patrolling": "130100",
        "psychological_operations": "130200",
        "radio_and_television_psychological_operations": "130201",
        "searching": "130300",
        "willing_coerced_qualifier": "130400",
        "willing": "130401",
        "coerced_impressed": "130402",
        "mine_laying": "130500",
        "spy": "130600",
        "warrant_served": "130700",
        "exfiltration": "130800",
        "infiltration": "130900",
        "meeting": "131000",
        "polling_place_election": "131001",
        "raid": "131100",
        "emergency_operation": "131200",
        "emergency_collection_evacuation_point": "131201",
        "food_distribution": "131202",
        "emergency_incident_command_center": "131203",
        "emergency_operations_center": "131204",
        "emergency_public_information_center": "131205",
        "emergency_shelter": "131206",
        "emergency_staging_area": "131207",
        "water_distribution_center": "131208",
        "emergency_medical_operation": "131300",
        "emt_station_location": "131301",
        "health_department_facility": "131302",
        "medical_facilities_outpatient": "131303",
        "emergency_medical_operation_facility": "131304",
        "pharmacy": "131305",
        "triage": "131306",
        "fire_protection": "131400",
        "fire_hydrant": "131401",
        "fire_station": "131402",
        "other_water_supply_location": "131403",
        "law_enforcement": "131500",
        "bureau_of_alcohol_tobacco_firearms_and_explosives": "131501",
        "border_patrol": "131502",
        "customs_service": "131503",
        "drug_enforcement_administration": "131504",
        "department_of_justice": "131505",
        "federal_bureau_of_investigation": "131506",
        "police": "131507",
        "prison": "131508",
        # "secret" here is the US Secret Service, a MIL-STD-2525D entity
        # name - not a credential. Suppressions are for the scanners' own
        # keyword heuristics (1.0.0's automated review, 2026-08-17).
        "united_states_secret_service": "131509",  # nosec B105 # pragma: allowlist secret
        "transportation_security_administration": "131510",
        "law_enforcement_vessel": "131511",
        "us_marshals_service": "131512",
        "internal_security_force": "131513",
        "fire_event": "140000",
        "fire_origin": "140100",
        "smoke": "140200",
        "hot_spot": "140300",
        "non_residential_fire": "140400",
        "residential_fire": "140500",
        "school_fire": "140600",
        "special_needs_fire": "140700",
        "wild_fire": "140800",
        "hazardous_materials": "150000",
        "hazardous_materials_incident": "150100",
        "chemical_agent": "150101",
        "corrosive_material": "150102",
        "hazardous_when_wet": "150103",
        "explosive_material": "150104",
        "flammable_gas": "150105",
        "flammable_liquid": "150106",
        "flammable_solid": "150107",
        "non_flammable_gas": "150108",
        "organic_peroxide": "150109",
        "oxidizer": "150110",
        "radioactive_material": "150111",
        "spontaneously_combustible_material": "150112",
        "toxic_gas": "150113",
        "toxic_infectious_material": "150114",
        "unexploded_ordnance": "150115",
        "transportation": "160000",
        "hijacking_airplane": "160100",
        "hijacking_boat": "160200",
        "train_locomotive": "160300",
        "known_insurgent_vehicle": "160400",
        "vehicle_explosion": "160500",
        "natural_event": "170000",
        "geologic": "170100",
        "aftershock": "170101",
        "avalanche": "170102",
        "earthquake_epicenter": "170103",
        "landslide": "170104",
        "subsidence": "170105",
        "volcanic_eruption": "170106",
        "volcanic_threat": "170107",
        "cave_entrance": "170108",
        "hydro_meteorological": "170200",
        "drought": "170201",
        "flood": "170202",
        "tsunami": "170203",
        "infestation": "170300",
        "bird": "170301",
        "insect": "170302",
        "microbial": "170303",
        "reptile": "170304",
        "rodent": "170305",
        "personalities": "180000",
        "religious_leader": "180100",
        "spokesperson": "180200",
        "isolated_personnel": "180300",
    },
    # See _SIGINT_ENTITIES above (Appendix J) - the same dict object
    # under all five dimension-specific symbol_set keys, since
    # build_sidc() looks entities up as ENTITIES[symbol_set][entity] and
    # sigint_layer.py resolves symbol_set from a separate "dimension"
    # field rather than from the entity itself (see
    # military_symbology/_point_symbol_layer.py's dimension_symbol_sets
    # mechanism).
    "sigint_space": _SIGINT_ENTITIES,
    "sigint_air": _SIGINT_ENTITIES,
    "sigint_land": _SIGINT_ENTITIES,
    "sigint_sea_surface": _SIGINT_ENTITIES,
    "sigint_subsurface": _SIGINT_ENTITIES,
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/cyberspace.js (symbolSet == "60") - the FULL
    # vocabulary Table L-II (Appendix L, printed pages 801-807) actually
    # defines: 50 of milsymbol's own 72 sId entries. milsymbol's source
    # is itself edition-aware (several codes resolve differently
    # depending on `edition == "D"` vs its MIL-STD-2525E/APP-6E branch -
    # e.g. code 110100 is "Command and Control (C2)" in D, "Combat
    # Mission Team" in E) - this project's own build_sidc() always sets
    # SIDC version "10", which milsymbol's own metadata.js maps to
    # edition "D" unconditionally, so the "D" branch is always what
    # actually renders; codes below use that branch's own icon choice,
    # cross-checked directly against Table L-II's own printed text (not
    # just picked because it's labeled "D"). The 22 excluded codes fall
    # into two groups, both confirmed absent from Table L-II by the
    # table's own physical page boundary (ends at code 160900, blank
    # page, then the standard's INDEX begins - no Appendix L content
    # after): six mid-range codes (110500-111000) that are either
    # explicitly commented "// Disused" in milsymbol's own source or
    # simply have no D-edition value at all, and the entire 170000-180000
    # block (Server/Workstation/Mobile/Tablet/Laptop/IoT device-type
    # entries), which reads like a 2525E/APP-6E-only addition never
    # actually part of 2525D's own Appendix L.
    "cyberspace": {
        "botnet": "110000",
        "command_and_control": "110100",
        "herder": "110200",
        "callback_domain": "110300",
        "zombie": "110400",
        "infection": "120000",
        "advanced_persistent_threat": "120100",
        "apt_with_c2": "120101",
        "apt_with_self_propagation": "120102",
        "apt_with_c2_and_self_propagation": "120103",
        "apt_other": "120104",
        "non_advanced_persistent_threat": "120200",
        "napt_with_c2": "120201",
        "napt_with_self_propagation": "120202",
        "napt_with_c2_and_self_propagation": "120203",
        "napt_other": "120204",
        "health_and_status": "130000",
        "normal": "130100",
        "network_outage_health_status": "130200",
        "unknown": "130300",
        "impaired": "130400",
        "device_type": "140000",
        "core_router": "140100",
        "router": "140200",
        "cross_domain_solution": "140300",
        "mail_server": "140400",
        "web_server": "140500",
        "domain_server": "140600",
        "file_server": "140700",
        "peer_to_peer_node": "140800",
        "firewall": "140900",
        "switch": "141000",
        "host": "141100",
        "virtual_private_network": "141200",
        "device_domain": "150000",
        "department_of_defense": "150100",
        "government": "150200",
        "contractor": "150300",
        "supervisory_control_and_data_acquisition": "150400",
        "non_government": "150500",
        "effect": "160000",
        "infection_effect": "160100",
        "degradation": "160200",
        "data_spoofing": "160300",
        "data_manipulation": "160400",
        "exfiltration": "160500",
        "power_outage": "160600",
        "network_outage_effect": "160700",
        "service_outage": "160800",
        "device_outage": "160900",
    },
}


# Sector 1 / sector 2 modifier codes (SIDC positions 17-18/19-20),
# keyed by symbol_set then "sector1"/"sector2" - real codes from each
# symbol set's own milsymbol-3.0.4 source (sIdm1/sIdm2 in the same files
# ENTITIES above is sourced from). Added 2026-08-08: every layer built
# before this only ever set these to "00" (no modifier) - a real,
# previously-undocumented gap, since e.g. Space's orbit type or Air's
# heavy/medium/light tanker class live entirely in these two fields, not
# in the base entity. Only symbol sets actually wired into a layer's own
# UI need an entry here - a symbol_set absent from this dict simply has
# no modifier support yet (build_sidc() only raises if a caller actually
# passes a non-None modifier for such a symbol_set).

# Real codes from milsymbol-3.0.4's own
# src/numbersidc/sidc/signalsintelligence.js sIdm1 (symbolSet == "50"
# through "54"), cross-checked against the standard's own Table J-III
# (Appendix J, printed pages 774-782) - ONLY codes "01" through "64"
# ("Experimental") match an actual row in that table; milsymbol's own
# source has one more, sIdm1["65"] ("Cyber"), with no corresponding row
# - Table J-III physically ends at code 64 (next page is blank, then
# Appendix K begins) - so "65" is excluded here, same "trust the
# standard's own table over milsymbol.js's extra entries" call already
# made for Activities' own sector 1 modifiers. milsymbol's source also
# has a single sIdm2["01"] ("Cyber") with likewise no table at all -
# J.5.3.2's own text states explicitly "There are no sector 2 modifiers
# in SIGINT", so no MODIFIERS["sigint_*"]["sector2"] entry exists either.
# One shared dict (not five copies) referenced under all five
# MODIFIERS["sigint_*"] keys below, same reasoning as _SIGINT_ENTITIES
# above - Table J-III's own modifiers apply identically across all five
# SIGINT symbol sets (each row's own "Symbol Set Code" column just lists
# which subset of the five dimensions that particular modifier is
# meaningful for - a doctrinal usage note this plugin doesn't enforce,
# same as it doesn't enforce which sector modifiers pair with which
# entities anywhere else either).
_SIGINT_SECTOR1_MODIFIERS = {
    "anti_aircraft_fire_control": "01",
    "airborne_search_and_bombing": "02",
    "airborne_intercept": "03",
    "altimeter": "04",
    "airborne_reconnaissance_and_mapping": "05",
    "air_traffic_control": "06",
    "beacon_transponder_not_iff": "07",
    "battlefield_surveillance": "08",
    "controlled_approach": "09",
    "controlled_intercept": "10",
    "cellular_mobile": "11",
    "coastal_surveillance": "12",
    "decoy_mimic": "13",
    "data_transmission": "14",
    "earth_surveillance": "15",
    "early_warning": "16",
    "fire_control": "17",
    "ground_mapping": "18",
    "height_finding": "19",
    "harbor_surveillance": "20",
    "identification_friend_or_foe_interrogator": "21",
    "instrument_landing_system": "22",
    "ionospheric_sounding": "23",
    "identification_friend_or_foe_transponder": "24",
    "barrage_jammer": "25",
    "click_jammer": "26",
    "deceptive_jammer": "27",
    "frequency_swept_jammer": "28",
    "jammer_general": "29",
    "noise_jammer": "30",
    "pulsed_jammer": "31",
    "repeater_jammer": "32",
    "spot_noise_jammer": "33",
    "transponder_jammer": "34",
    "missile_acquisition": "35",
    "missile_control": "36",
    "missile_downlink": "37",
    "meteorological": "38",
    "multi_function": "39",
    "missile_guidance": "40",
    "missile_homing": "41",
    "missile_tracking": "42",
    "navigational_general": "43",
    "navigational_distance_measuring_equipment": "44",
    "navigation_terrain_following": "45",
    "navigational_weather_avoidance": "46",
    "omni_line_of_sight_los": "47",
    "proximity_use": "48",
    "point_to_point_line_of_sight_los": "49",
    "instrumentation": "50",
    "range_only": "51",
    "sonobuoy": "52",
    "satellite_downlink": "53",
    "space": "54",
    "surface_search": "55",
    "shell_tracking": "56",
    "satellite_uplink": "57",
    "target_acquisition": "58",
    "target_illumination": "59",
    "tropospheric_scatter": "60",
    "target_tracking": "61",
    "unknown": "62",
    "video_remoting": "63",
    "experimental": "64",
}

MODIFIERS = {
    "space": {
        "sector1": {
            "low_earth_orbit": "01",
            "medium_earth_orbit": "02",
            "high_earth_orbit": "03",
            "geosynchronous_orbit": "04",
            "geostationary_orbit": "05",
            "molniya_orbit": "06",
            "cyberspace": "07",
        },
        "sector2": {
            "optical": "01",
            "infrared": "02",
            "radar": "03",
            "signals_intelligence": "04",
            "cyberspace": "05",
            "electromagnetic_warfare": "06",
            "high_power_microwave": "07",
            "laser": "08",
            "mine": "09",
            "maintenance": "10",
            "refuel": "11",
            "tug": "12",
        },
    },
    "space_missile": {
        "sector1": {
            "ballistic": "01",
            "space": "02",
            "interceptor": "03",
            "hypersonic": "04",
        },
        "sector2": {
            "short_range": "01",
            "medium_range": "02",
            "intermediate_range": "03",
            "long_range": "04",
            "intercontinental": "05",
            "arrow": "06",
            "ground_based_interceptor": "07",
            "patriot": "08",
            "standard_missile_terminal_phase": "09",
            "standard_missile_3": "10",
            "terminal_high_altitude_area_defense": "11",
            "space": "12",
            "close_range": "13",
            "debris": "14",
            "unknown": "15",
        },
    },
    "air": {
        "sector1": {
            "attack": "01",
            "bomber": "02",
            "cargo": "03",
            "fighter": "04",
            "interceptor": "05",
            "tanker": "06",
            "utility": "07",
            "vstol": "08",
            "passenger": "09",
            "ultra_light": "10",
            "airborne_command_post": "11",
            "airborne_early_warning": "12",
            "government": "13",
            "medevac": "14",
            "escort": "15",
            "jammer_electronic_countermeasures": "16",
            "patrol": "17",
            "reconnaissance": "18",
            "trainer": "19",
            "photographic": "20",
            "personnel_recovery": "21",
            "antisubmarine_warfare": "22",
            "communications": "23",
            "electronic_support": "24",
            "mine_countermeasures": "25",
            "search_and_rescue": "26",
            "special_operations_forces": "27",
            "surface_warfare": "28",
            "vip": "29",
            "combat_search_and_rescue": "30",
            "suppression_of_enemy_air_defense": "31",
            "antisurface_warfare": "32",
            "fighter_bomber": "33",
            "intensive_care": "34",
            "electronic_attack": "35",
            "multimission": "36",
            "hijacking": "37",
            "asw_helo_lamps": "38",
            "asw_helo_sh_60r": "39",
            "hijacker": "40",
            "cyberspace": "41",
        },
        "sector2": {
            "heavy": "01",
            "medium": "02",
            "light": "03",
            "boom_only": "04",
            "drogue_only": "05",
            "boom_and_drogue": "06",
            "close_range": "07",
            "short_range": "08",
            "medium_range": "09",
            "long_range": "10",
            "downlinked": "11",
            "cyberspace": "12",
        },
    },
    "air_missile": {
        "sector1": {
            "air": "01",
            "surface": "02",
            "subsurface": "03",
            "space": "04",
            "anti_ballistic": "05",
            "ballistic": "06",
            "cruise": "07",
            "interceptor": "08",
            "hypersonic": "09",
        },
        "sector2": {
            "air": "01",
            "surface": "02",
            "subsurface": "03",
            "space": "04",
            "launched": "05",
            "missile": "06",
            "patriot": "07",
            "standard_missile_2": "08",
            "standard_missile_6": "09",
            "evolved_sea_sparrow_missile": "10",
            "rolling_airframe_missile": "11",
            "short_range": "12",
            "medium_range": "13",
            "intermediate_range": "14",
            "long_range": "15",
            "intercontinental": "16",
        },
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/sea.js
    # sIdm1/sIdm2 (symbolSet == "30"). Per the standard's own E.6.4:
    # sector 2 modifiers "are not permitted with civilian sea surface
    # symbols" - not enforced in code (this plugin doesn't restrict
    # modifier availability by entity), a documented, deliberate
    # simplification rather than an oversight.
    "sea_surface": {
        "sector1": {
            "own_ship": "01",
            "antiair_warfare": "02",
            "antisubmarine_warfare": "03",
            "escort": "04",
            "electronic_warfare": "05",
            "intelligence_surveillance_reconnaissance": "06",
            "mine_countermeasures": "07",
            "missile_defense": "08",
            "medical": "09",
            "mine_warfare": "10",
            "remote_multi_mission_vehicle": "11",
            "special_operations_force": "12",
            "surface_warfare": "13",
            "ballistic_missile": "14",
            "guided_missile": "15",
            "other_guided_missile": "16",
            "torpedo": "17",
            "drone_equipped": "18",
            "helicopter_equipped": "19",
            "ballistic_missile_defense_shooter": "20",
            "ballistic_missile_defense_long_range_surveillance_and_track": "21",
            "sea_base_x_band": "22",
            "hijacking_hijacked": "23",
            "hijacker": "24",
            "cyberspace": "25",
        },
        "sector2": {
            "nuclear_powered": "01",
            "heavy": "02",
            "light": "03",
            "medium": "04",
            "dock": "05",
            "logistics": "06",
            "tank": "07",
            "vehicle": "08",
            "fast": "09",
            "air_cushioned_us": "10",
            "air_cushioned": "11",
            "hydrofoil": "12",
            "autonomous_control": "13",
            "remotely_piloted": "14",
            "expendable": "15",
            "cyberspace": "16",
        },
    },
    # Real codes from milsymbol-3.0.4's own
    # src/numbersidc/sidc/subsurface.js sIdm1/sIdm2 (symbolSet == "35")
    # - the complete set (22 sector1 + 17 sector2). No MODIFIERS entry
    # for "mine_warfare" - its own source has zero sIdm1/sIdm2 entries.
    "subsurface": {
        "sector1": {
            "antisubmarine_warfare": "01",
            "auxiliary": "02",
            "command_and_control": "03",
            "intelligence_surveillance_reconnaissance": "04",
            "mine_countermeasures": "05",
            "mine_warfare": "06",
            "surface_warfare": "07",
            "attack": "08",
            "ballistic_missile": "09",
            "guided_missile": "10",
            "other_guided_missiles_point_defence": "11",
            "special_operations_force": "12",
            "possible_submarine_low_1": "13",
            "possible_submarine_low_2": "14",
            "possible_submarine_high_3": "15",
            "possible_submarine_high_4": "16",
            "probable_submarine": "17",
            "certain_submarine": "18",
            "anti_torpedo_torpedo": "19",
            "hijacking_hijacked": "20",
            "hijacker": "21",
            "cyberspace": "22",
        },
        "sector2": {
            "air_independent_propulsion": "01",
            "diesel_propulsion": "02",
            "diesel_type_1": "03",
            "diesel_type_2": "04",
            "diesel_type_3": "05",
            "nuclear_powered": "06",
            "nuclear_type_1": "07",
            "nuclear_type_2": "08",
            "nuclear_type_3": "09",
            "nuclear_type_4": "10",
            "nuclear_type_5": "11",
            "nuclear_type_6": "12",
            "nuclear_type_7": "13",
            "autonomous_control": "14",
            "remotely_piloted": "15",
            "expendable": "16",
            "cyberspace": "17",
        },
    },
    # Real codes from milsymbol-3.0.4's own src/numbersidc/sidc/
    # activites.js sIdm1 (symbolSet == "40"), cross-checked against the
    # standard's own Table G-IV (Appendix G, printed pages 383-385) -
    # ONLY sector1 codes "01" through "18" ("theft") match an actual row
    # in Table G-IV. milsymbol's own source defines four more sIdm1
    # entries ("19"-"22": hijacker, cyberspace, eviction, raid) and two
    # sIdm2 entries ("01"-"02": cyberspace, security force assistance)
    # that have NO corresponding row in Table G-IV - the appendix's own
    # text explicitly states "Note: There are no sector 2 modifiers in
    # activities symbols" (G.5.3.1 step 3), and the table itself
    # physically ends at code 18 (next page is blank, then Appendix H
    # begins) - so those six milsymbol entries are excluded here as
    # unsanctioned by the standard, trusting the standard's own text/
    # table over milsymbol.js's source per this project's standing
    # verification policy. Code "09"'s label uses the standard's own
    # wording ("Written Military Information Support Operations", per
    # Table G-IV's own category column) rather than milsymbol's older
    # "WRITTEN PSYCHOLOGICAL OPERATIONS" constant name.
    "activities": {
        "sector1": {
            "assassination": "01",
            "execution": "02",
            "hijacking_hijacked": "03",
            "house_to_house": "04",
            "kidnapping": "05",
            "murder": "06",
            "piracy": "07",
            "rape": "08",
            "written_military_information_support_operations": "09",
            "pirate": "10",
            "false": "11",
            "find": "12",
            "found_and_cleared": "13",
            "hoax_decoy": "14",
            "attempted": "15",
            "accident": "16",
            "incident": "17",
            "theft_modifier": "18",
        },
    },
    # See _SIGINT_SECTOR1_MODIFIERS above (Appendix J) - the same dict
    # object under all five dimension-specific symbol_set keys. No
    # "sector2" entry for any of them - SIGINT has none.
    "sigint_space": {"sector1": _SIGINT_SECTOR1_MODIFIERS},
    "sigint_air": {"sector1": _SIGINT_SECTOR1_MODIFIERS},
    "sigint_land": {"sector1": _SIGINT_SECTOR1_MODIFIERS},
    "sigint_sea_surface": {"sector1": _SIGINT_SECTOR1_MODIFIERS},
    "sigint_subsurface": {"sector1": _SIGINT_SECTOR1_MODIFIERS},
}


def build_sidc(
    affiliation,
    entity,
    symbol_set="ground_unit",
    echelon="unspecified",
    status="present",
    headquarters=False,
    sector1_modifier=None,
    sector2_modifier=None,
):

    """
    A 20-character SIDC string for the given components. Raises KeyError
    (with the invalid value's own field name in the message) for any
    unrecognised affiliation/symbol_set/entity/echelon/status/
    sector1_modifier/sector2_modifier - callers should validate against
    this module's own vocabulary dicts before calling, rather than
    relying on typo-tolerant behaviour here.
    sector1_modifier/sector2_modifier are None (or falsy, e.g. "") by
    default - "no modifier", SIDC code "00" - since most symbols are
    built without one; pass a real key from MODIFIERS[symbol_set]
    ["sector1"/"sector2"] to set one. A symbol_set with no MODIFIERS
    entry at all simply has no modifier support yet - passing None/""
    for it is fine (produces "00", same as "no modifiers built yet" did
    before this parameter existed); passing an actual value for it
    raises KeyError.
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

    modifiers_for_set = MODIFIERS.get(symbol_set, {})

    sector1_code = _modifier_code(
        sector1_modifier,
        modifiers_for_set.get("sector1", {}),
        "sector1_modifier",
        symbol_set,
    )

    sector2_code = _modifier_code(
        sector2_modifier,
        modifiers_for_set.get("sector2", {}),
        "sector2_modifier",
        symbol_set,
    )

    version = "10"
    context = "0"
    affiliation_code = AFFILIATIONS[affiliation]
    symbol_set_code = SYMBOL_SETS[symbol_set]
    status_code = STATUS[status]
    hq_code = HEADQUARTERS_CODE if headquarters else NO_HEADQUARTERS_CODE
    echelon_code = ECHELONS[echelon]
    function_id = entities_for_set[entity] + sector1_code + sector2_code

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


def _modifier_code(modifier, modifiers_for_sector, field_name, symbol_set):

    """
    "00" (no modifier) if `modifier` is None/falsy; otherwise the real
    2-digit code for `modifier` in `modifiers_for_sector` (a symbol
    set's own MODIFIERS[...]["sector1"/"sector2"] dict), raising
    KeyError if it's not a valid key there.
    """

    if not modifier:
        return "00"

    if modifier not in modifiers_for_sector:

        raise KeyError(
            f"Unknown {field_name} {modifier!r} for symbol_set "
            f"{symbol_set!r} - expected one of "
            f"{sorted(modifiers_for_sector)}"
        )

    return modifiers_for_sector[modifier]
