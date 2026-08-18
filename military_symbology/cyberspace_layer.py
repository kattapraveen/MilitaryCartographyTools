# -*- coding: utf-8 -*-

"""
Builds the "Cyberspace" point layer - MIL-STD-2525D
Appendix L (Cyberspace Symbols), symbol set "60" (Table A-III). A single
symbol set (unlike Appendix J/SIGINT's five) - every entry in Table L-II
lists exactly one SymbolSetCode ("60"), so this is a plain single-domain
layer, no Dimension field needed despite L.5.3.3's own boilerplate text
about a cyberspace symbol's dimension (see below).

No modifier fields at all - L.5.3.2's own text states explicitly "There
are no modifiers in cyberspace symbols" (also noted in Table L-I's own
step 2). milsymbol's own cyberspace.js source does define 13 sIdm1 and
8 sIdm2 codes, but these read as 2525E/APP-6E-only additions with no
sanction in 2525D's own Table L-II/L-III (there is no Table L-III at
all in this appendix) - excluded entirely, the same "trust the
standard's own text over milsymbol.js's extra entries" call already
made for Activities/SIGINT.

No echelon/headquarters fields either - L.5.3.3 says a cyberspace
symbol's amplifiers "follow the amplifier requirements as stated in
[whichever dimension's] appendix" it's associated with (space/air/land/
sea surface/subsurface), the same cross-reference text Appendix J's own
SIGINT symbols use - but unlike SIGINT, Cyberspace entities are NOT
actually split across five symbol sets (Table L-II uses only "60"
throughout), so this text reads as general amplifier guidance rather
than a real per-dimension field requirement this plugin needs to model.
Combined with the same genuine ambiguity already documented in
sigint_layer.py (which of Appendix D's four different field sets "the
land appendix" would even mean), this plugin does not attempt a
per-dimension conditional field set here either - a deliberate,
documented simplification, not a guessed rule.

Entity vocabulary is sidc.py's ENTITIES["cyberspace"] - the FULL
50-entity vocabulary Table L-II actually defines (milsymbol's own
source has 72 sId entries; 22 are excluded as absent from the standard's
own table - see sidc.py's own comment on ENTITIES["cyberspace"] for the
full breakdown, including the edition-dependent icon selection this
project's SIDC version always resolves to the "D" branch of).

Military Cartography Tools
"""

from ._point_symbol_layer import add_single_domain_point_layer


OUTPUT_LAYER_NAME = "Cyberspace"

DEFAULT_ENTITY = "web_server"

_ENTITY_LABELS = {
    "botnet": "Botnet (Generic)",
    "command_and_control": "Command and Control (C2)",
    "herder": "Herder",
    "callback_domain": "Callback Domain",
    "zombie": "Zombie",
    "infection": "Infection (Generic)",
    "advanced_persistent_threat": "Advanced Persistent Threat (APT)",
    "apt_with_c2": "APT with C2",
    "apt_with_self_propagation": "APT with Self Propagation",
    "apt_with_c2_and_self_propagation": "APT with C2 and Self Propagation",
    "apt_other": "APT Other",
    "non_advanced_persistent_threat": "Non-Advanced Persistent Threat (NAPT)",
    "napt_with_c2": "NAPT with C2",
    "napt_with_self_propagation": "NAPT with Self Propagation",
    "napt_with_c2_and_self_propagation": "NAPT with C2 and Self Propagation",
    "napt_other": "NAPT Other",
    "health_and_status": "Health and Status (Generic)",
    "normal": "Normal",
    "network_outage_health_status": "Network Outage (Health and Status)",
    "unknown": "Unknown",
    "impaired": "Impaired",
    "device_type": "Device Type (Generic)",
    "core_router": "Core Router",
    "router": "Router",
    "cross_domain_solution": "Cross Domain Solution",
    "mail_server": "Mail Server",
    "web_server": "Web Server",
    "domain_server": "Domain Server",
    "file_server": "File Server",
    "peer_to_peer_node": "Peer-to-Peer Node",
    "firewall": "Firewall",
    "switch": "Switch",
    "host": "Host",
    "virtual_private_network": "Virtual Private Network (VPN)",
    "device_domain": "Device Domain (Generic)",
    "department_of_defense": "Department of Defense (DOD)",
    "government": "Government",
    "contractor": "Contractor",
    "supervisory_control_and_data_acquisition": "Supervisory Control and Data Acquisition (SCADA)",
    "non_government": "Non-Government",
    "effect": "Effect (Generic)",
    "infection_effect": "Infection (Effect)",
    "degradation": "Degradation",
    "data_spoofing": "Data Spoofing",
    "data_manipulation": "Data Manipulation",
    "exfiltration": "Exfiltration",
    "power_outage": "Power Outage",
    "network_outage_effect": "Network Outage (Effect)",
    "service_outage": "Service Outage",
    "device_outage": "Device Outage",
}


def add_cyberspace_layer(iface, edition=None):

    """
    Add the "Cyberspace" layer - warns and does
    nothing if one already exists, same data-safety guard as every other
    hand-digitized layer in this plugin.
    """

    return add_single_domain_point_layer(
        iface,
        OUTPUT_LAYER_NAME,
        "cyberspace",
        _ENTITY_LABELS,
        DEFAULT_ENTITY,
        include_echelon=False,
        include_headquarters=False,
        edition=edition,
    )
