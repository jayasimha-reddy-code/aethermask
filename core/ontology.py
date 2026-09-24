"""
AetherMask (CipherShift) :: core.ontology
=========================================
Bundled, 100% offline semantic ontology graphs and domain-shift matrices.

NOTHING in this module performs I/O, network access, or dynamic imports.
Every mapping is a literal, auditable, deterministic Python data structure so
that an air-gapped accreditation authority can diff it byte-for-byte.

Structure
---------
    TOKEN_SHIFTS      : per-domain-profile token->token lexical rewrite rules
                        (applied to column headers / identifier fragments)
    ENTITY_POOLS      : per-domain-profile surrogate pools used for bijective
                        categorical + narrative-entity replacement
    SENSITIVITY_RULES : deterministic regex/gazetteer sensitivity profiler rules
    NER_PATTERNS      : rule-based Named Entity Recognition patterns (offline)
    DOMAIN_PROFILES   : registry binding all of the above together

Design invariant
----------------
Token shifts are *lexical* and order-stable: the engine sorts rewrite keys by
descending length so that "missile_control" wins over "missile" and the output
is independent of dict iteration order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Sequence, Tuple

__all__ = [
    "DomainProfile",
    "DOMAIN_PROFILES",
    "list_profiles",
    "get_profile",
    "SENSITIVITY_RULES",
    "NER_PATTERNS",
    "CLASSIFICATION_TOKENS",
]


# --------------------------------------------------------------------------- #
#  1. LEXICAL TOKEN SHIFT MATRICES  (column headers, identifier fragments)
# --------------------------------------------------------------------------- #

#: Kinetic defense  ->  civil freight / supply-chain logistics
_SHIFT_DEFENSE_TO_LOGISTICS: Dict[str, str] = {
    # --- platforms & organisation -----------------------------------------
    "strike_squadron": "logistics_fleet",
    "strike_package": "delivery_batch",
    "strike_group": "distribution_group",
    "task_force": "service_division",
    "battle_group": "carrier_group",
    "squadron": "fleet",
    "battalion": "depot_network",
    "regiment": "district_network",
    "brigade": "regional_hub",
    "platoon": "crew_team",
    "company": "crew_unit",
    "garrison": "warehouse_site",
    "wing": "terminal",
    "flight": "shipment_run",
    "sortie": "dispatch_run",
    "sorties": "dispatch_runs",
    "mission": "consignment",
    "operation": "programme",
    "campaign": "seasonal_plan",
    "command": "control_centre",
    "commander": "site_manager",
    "unit": "depot",
    "detachment": "sub_depot",
    "crew": "crew",
    # --- weapons & effects -------------------------------------------------
    "missile_control": "mission_control",
    "missile": "cargo_pod",
    "munition": "cargo_unit",
    "munitions": "cargo_units",
    "ordnance": "freight_class",
    "warhead_yield": "cargo_capacity",
    "warhead": "cargo_module",
    "payload_weight": "net_weight",
    "payload": "payload",
    "yield": "capacity",
    "explosive": "hazmat",
    "detonation": "unloading_event",
    "detonate": "unload",
    "launch_time": "dispatch_time",
    "launch": "dispatch",
    "launcher": "dispatch_bay",
    "fire_mission": "delivery_order",
    "firing": "dispatching",
    "weapon_system": "handling_system",
    "weapon": "handling_asset",
    "armament": "equipment_load",
    "kinetic": "throughput",
    "lethality": "efficiency",
    "kill_probability": "completion_probability",
    "kill_chain": "fulfilment_chain",
    "kill": "completion",
    "casualty": "exception_event",
    "casualties": "exception_events",
    "collateral": "secondary_impact",
    "blast_radius": "service_radius",
    "impact_point": "delivery_point",
    "impact": "delivery",
    # --- targeting & geodesy ----------------------------------------------
    "target_latitude": "waypoint_lat",
    "target_longitude": "waypoint_lon",
    "target_altitude": "waypoint_alt",
    "target_designation": "waypoint_designation",
    "target_id": "waypoint_id",
    "target_name": "waypoint_name",
    "target_priority": "waypoint_priority",
    "target": "waypoint",
    "targeting": "routing",
    "aimpoint": "dropoff_point",
    "designator": "reference_code",
    "grid_reference": "grid_reference",
    "bearing": "heading",
    "azimuth": "heading_angle",
    "elevation": "altitude",
    "range_to_target": "distance_to_waypoint",
    "standoff_range": "transit_range",
    "engagement_zone": "service_zone",
    "engagement": "service_event",
    "engage": "service",
    "threat_axis": "route_axis",
    "threat_level": "risk_level",
    "threat": "risk",
    "hostile": "external",
    "enemy": "competitor",
    "friendly": "internal",
    "adversary": "counterparty",
    # --- intelligence, clearance, comms ------------------------------------
    "classification": "handling_tier",
    "classified": "restricted",
    "clearance_level": "access_tier",
    "clearance": "access_tier",
    "compartment": "workstream",
    "caveat": "handling_note",
    "codeword": "project_word",
    "callsign": "vehicle_tag",
    "call_sign": "vehicle_tag",
    "sigint": "signal_analytics",
    "humint": "field_reporting",
    "geoint": "geo_analytics",
    "elint": "emitter_analytics",
    "osint": "open_reporting",
    "intel": "analysis",
    "intelligence": "analysis",
    "reconnaissance": "site_survey",
    "recon": "survey",
    "surveillance": "monitoring",
    "covert": "internal",
    "clandestine": "confidential",
    "asset_handler": "account_manager",
    "operative": "field_agent",
    "agent": "field_agent",
    "informant": "contact",
    "safehouse": "field_office",
    "exfiltration": "return_transit",
    "infiltration": "inbound_transit",
    "extraction": "recovery",
    # --- sensors / telemetry ------------------------------------------------
    "radar_cross_section": "profile_index",
    "radar": "scanner",
    "sonar": "acoustic_sensor",
    "emitter": "transmitter",
    "jamming": "interference",
    "countermeasure": "mitigation",
    "stealth": "low_profile",
    "telemetry_rate": "telemetry_rate",
    "burst_rate": "sample_rate",
    "encryption_key": "access_token",
    "frequency_hopping": "channel_rotation",
    # --- readiness & logistics ---------------------------------------------
    "readiness": "availability",
    "sustainment": "maintenance",
    "attrition": "wastage",
    "expenditure": "consumption",
    "stockpile": "inventory",
    "magazine": "storage_bay",
    "depot": "depot",
    "convoy": "convoy",
    "airlift": "air_freight",
    "sealift": "sea_freight",
    "resupply": "replenishment",
    "deployment": "allocation",
    "deployed": "allocated",
    "mobilization": "activation",
    "troop": "personnel",
    "troops": "personnel",
    "soldier": "operator",
    "personnel": "personnel",
    "rank": "grade",
    "service_number": "employee_number",
    "combat": "field",
    "battlefield": "field_site",
    "theater": "region",
    "theatre": "region",
    "front_line": "forward_site",
    "airbase": "terminal_hub",
    "base": "hub",
    "installation": "facility",
    "bunker": "vault_store",
    "silo": "storage_tower",
}

#: Aerospace / military aviation  ->  commercial aviation
_SHIFT_AEROSPACE_TO_CIVIL_AVIATION: Dict[str, str] = {
    "fighter_squadron": "carrier_fleet",
    "fighter": "airframe",
    "bomber": "freighter",
    "interceptor": "express_carrier",
    "airframe_tail": "aircraft_registration",
    "tail_number": "registration_number",
    "sortie_rate": "rotation_rate",
    "sortie": "rotation",
    "combat_air_patrol": "scheduled_patrol_route",
    "air_superiority": "route_dominance",
    "dogfight": "close_manoeuvre",
    "afterburner": "climb_thrust",
    "ordnance_load": "cargo_load",
    "weapons_bay": "cargo_bay",
    "hardpoint": "mount_point",
    "pylon": "mount_pylon",
    "ejection": "evacuation",
    "cockpit": "flight_deck",
    "pilot_callsign": "crew_tag",
    "pilot": "captain",
    "wingman": "first_officer",
    "flight_lead": "lead_captain",
    "no_fly_zone": "restricted_airspace",
    "air_defense": "airspace_management",
    "sam_site": "ground_station",
    "radar_lock": "tracking_lock",
    "intercept": "rendezvous",
    "scramble": "rapid_dispatch",
    "mission_profile": "flight_profile",
    "strike_mission": "cargo_flight",
    "refuel_track": "tanker_track",
    "aerial_refueling": "in_flight_servicing",
    "loiter_time": "holding_time",
    "ingress_route": "arrival_route",
    "egress_route": "departure_route",
    "target_area": "destination_area",
    "bingo_fuel": "reserve_fuel",
    "classified_airfield": "regional_airfield",
    "airfield": "airport",
    "runway": "runway",
    "squadron": "fleet",
    "wing": "division",
    "sensor_pod": "instrument_pod",
    "threat_emitter": "signal_source",
    "countermeasure_dispenser": "diagnostic_dispenser",
}

#: Cyber warfare / offensive cyber  ->  smart-grid telemetry & SCADA ops
_SHIFT_CYBERWAR_TO_SMARTGRID: Dict[str, str] = {
    "cyber_operation": "grid_operation",
    "offensive_cyber": "grid_maintenance",
    "attack_vector": "fault_vector",
    "attack_surface": "exposure_surface",
    "attack": "fault_event",
    "exploit_chain": "diagnostic_chain",
    "exploit": "diagnostic_probe",
    "zero_day": "unclassified_fault",
    "payload_hash": "package_hash",
    "malware_family": "firmware_family",
    "malware": "anomalous_firmware",
    "implant": "sensor_module",
    "beacon_interval": "heartbeat_interval",
    "beacon": "heartbeat",
    "command_and_control": "supervisory_control",
    "c2_server": "scada_master",
    "c2": "scada_link",
    "exfil_volume": "telemetry_volume",
    "exfiltration": "telemetry_upload",
    "lateral_movement": "segment_traversal",
    "privilege_escalation": "role_elevation",
    "persistence": "retention",
    "dropper": "installer",
    "backdoor": "service_channel",
    "botnet": "device_mesh",
    "victim_host": "endpoint_node",
    "victim": "endpoint",
    "target_network": "substation_network",
    "intrusion": "irregular_access",
    "breach": "threshold_breach",
    "compromise": "degradation",
    "threat_actor": "operating_entity",
    "apt_group": "vendor_group",
    "apt": "vendor",
    "tradecraft": "procedure",
    "obfuscator": "encoder",
    "ransom_note": "service_notice",
    "encryption_routine": "encoding_routine",
    "kill_switch": "safety_interlock",
    "denial_of_service": "load_shedding",
    "ddos": "load_surge",
    "botmaster": "mesh_controller",
    "cve_id": "defect_id",
    "vulnerability": "defect",
    "patch_level": "firmware_level",
    "honeypot": "test_node",
    "sandbox_detonation": "test_execution",
    "operator_handle": "technician_handle",
}

#: Nuclear / strategic forces  ->  civil energy utility operations
_SHIFT_NUCLEAR_TO_CIVIL_ENERGY: Dict[str, str] = {
    "warhead_count": "turbine_count",
    "warhead": "turbine_module",
    "yield_kt": "output_mw",
    "fissile_mass": "fuel_mass",
    "fissile": "fuel_grade",
    "enrichment_level": "purity_level",
    "enrichment": "purity",
    "centrifuge": "separator",
    "reactor_core": "reactor_core",
    "criticality": "peak_load",
    "detonation_altitude": "stack_height",
    "silo_id": "plant_id",
    "silo": "plant",
    "launch_authority": "dispatch_authority",
    "launch_code": "dispatch_code",
    "two_man_rule": "dual_authorisation",
    "alert_level": "readiness_level",
    "strategic_deterrent": "baseload_capacity",
    "counterforce": "peak_response",
    "second_strike": "reserve_capacity",
    "megaton": "gigawatt",
    "kiloton": "megawatt",
    "fallout": "emissions",
    "radiation_dose": "exposure_index",
    "test_site": "test_facility",
    "weapons_grade": "industrial_grade",
    "stockpile_stewardship": "asset_stewardship",
}

#: Maritime / naval  ->  commercial shipping
_SHIFT_NAVAL_TO_COMMERCIAL_SHIPPING: Dict[str, str] = {
    "destroyer": "container_vessel",
    "frigate": "feeder_vessel",
    "corvette": "coastal_vessel",
    "submarine": "subsea_survey_vessel",
    "carrier_strike_group": "liner_service_group",
    "torpedo": "survey_probe",
    "depth_charge": "sonar_buoy",
    "hull_number": "imo_number",
    "naval_base": "port_terminal",
    "port_call": "port_call",
    "blockade": "embargo_hold",
    "patrol_zone": "service_lane",
    "sea_control": "lane_coverage",
    "anti_submarine": "subsea_survey",
    "sonar_contact": "acoustic_contact",
    "battle_damage": "hull_damage",
    "fleet_admiral": "fleet_director",
    "shore_bombardment": "shore_transfer",
    "amphibious_assault": "ro_ro_transfer",
    "convoy_escort": "convoy_support",
    "deck_crew": "deck_crew",
    "mine_field": "restricted_area",
}

#: Generic PII  ->  neutral corporate directory (always merged into every profile)
_SHIFT_PII_COMMON: Dict[str, str] = {
    "social_security_number": "member_reference",
    "ssn": "member_reference",
    "national_id": "member_reference",
    "passport_number": "travel_document_ref",
    "passport": "travel_document",
    "date_of_birth": "enrollment_date",
    "dob": "enrollment_date",
    "home_address": "registered_address",
    "residential_address": "registered_address",
    "personal_email": "contact_email",
    "email_address": "contact_email",
    "email": "contact_email",
    "phone_number": "contact_number",
    "mobile_number": "contact_number",
    "phone": "contact_number",
    "full_name": "display_name",
    "first_name": "given_label",
    "last_name": "family_label",
    "surname": "family_label",
    "middle_name": "middle_label",
    "maiden_name": "prior_label",
    "next_of_kin": "emergency_contact",
    "biometric_hash": "template_hash",
    "fingerprint": "template_id",
    "medical_record": "wellness_record",
    "diagnosis": "assessment_code",
    "salary": "compensation",
    "bank_account": "settlement_account",
    "iban": "settlement_iban",
    "credit_card": "payment_token",
    "tax_id": "registry_id",
    "badge_number": "pass_number",
    "employee_id": "employee_id",
    "username": "account_handle",
    "password_hash": "secret_hash",
    "ip_address": "node_address",
    "mac_address": "hardware_address",
    "device_imei": "device_serial",
}


# --------------------------------------------------------------------------- #
#  2. SURROGATE ENTITY POOLS  (bijective categorical / narrative replacement)
# --------------------------------------------------------------------------- #
# Pools are intentionally large, realistic, non-classified and *disjoint per
# semantic class* so that a masked dataset reads like a genuine civil dataset.

_POOL_LOGISTICS_ORG: List[str] = [
    "Northbridge Freight", "Cascade Haulage", "Meridian Cargo Lines", "Verdant Logistics",
    "Harborline Distribution", "Ironwood Transport", "Silverpine Freightways", "Brightpath Carriers",
    "Stonegate Supply", "Copperfield Shipping", "Larkspur Logistics", "Redwood Intermodal",
    "Clearwater Freight", "Summit Ridge Carriers", "Blue Heron Transport", "Amberline Cargo",
    "Kestrel Distribution", "Fairview Freight", "Granite Bay Haulage", "Willowbrook Supply",
    "Thornhill Logistics", "Evergreen Intermodal", "Sandpiper Cargo", "Highmark Transport",
    "Lakeshore Freightways", "Oakvale Distribution", "Pinecrest Carriers", "Juniper Supply Chain",
    "Foxglove Logistics", "Marbleton Freight", "Sable Creek Transport", "Windmere Cargo",
]

_POOL_LOGISTICS_SITE: List[str] = [
    "Ashford Depot", "Bellweather Hub", "Cedar Junction", "Dunmore Terminal", "Eastport Yard",
    "Fairhaven Depot", "Glenmoor Hub", "Hallbrook Terminal", "Inverness Yard", "Jarvis Crossing",
    "Kingsley Depot", "Lowfield Hub", "Marlow Terminal", "Netherton Yard", "Oakridge Crossing",
    "Pemberton Depot", "Quarry Lane Hub", "Rosemont Terminal", "Stanmore Yard", "Tarnbrook Crossing",
    "Uplands Depot", "Vinegrove Hub", "Westmere Terminal", "Yarrow Yard", "Zellwood Crossing",
    "Alderman Depot", "Brackenridge Hub", "Coldharbour Terminal", "Draycott Yard", "Elmsworth Crossing",
]

_POOL_LOGISTICS_ROUTE: List[str] = [
    "Route Alderline", "Route Beacon", "Route Cobblestone", "Route Driftwood", "Route Elmgate",
    "Route Foxrun", "Route Goldleaf", "Route Hazelford", "Route Ivyway", "Route Junipark",
    "Route Kelpline", "Route Lanternway", "Route Milestone", "Route Northgale", "Route Orchard",
    "Route Pathfinder", "Route Quarrygate", "Route Riverbend", "Route Stonemill", "Route Tidewater",
    "Route Umberfield", "Route Valeway", "Route Westford", "Route Yewbridge", "Route Zephyr",
]

_POOL_LOGISTICS_ASSET: List[str] = [
    "Hauler-Alpine", "Hauler-Basalt", "Hauler-Cinder", "Hauler-Dovetail", "Hauler-Ember",
    "Hauler-Flint", "Hauler-Granite", "Hauler-Hearth", "Hauler-Ironbark", "Hauler-Jetstream",
    "Hauler-Kindling", "Hauler-Limestone", "Hauler-Marble", "Hauler-Nickel", "Hauler-Obsidian",
    "Hauler-Pumice", "Hauler-Quartz", "Hauler-Rivet", "Hauler-Slate", "Hauler-Timber",
    "Hauler-Umber", "Hauler-Vellum", "Hauler-Wicker", "Hauler-Xenolith", "Hauler-Yardarm", "Hauler-Zinc",
]

_POOL_LOGISTICS_PROGRAMME: List[str] = [
    "Programme Clearview", "Programme Driftline", "Programme Evenkeel", "Programme Foldout",
    "Programme Gatepost", "Programme Halyard", "Programme Ledger", "Programme Manifest",
    "Programme Nightshift", "Programme Overland", "Programme Palletwise", "Programme Quayside",
    "Programme Roundtrip", "Programme Shelfline", "Programme Tailgate", "Programme Unitload",
    "Programme Viaduct", "Programme Waybill", "Programme Yardstick", "Programme Zoning",
]

_POOL_AVIATION_ORG: List[str] = [
    "Aurora Air Cargo", "Beacon Airlines", "Crestwind Aviation", "Dawnstar Airways",
    "Eastwind Air", "Falconridge Airlines", "Goldenvale Air", "Highcloud Aviation",
    "Isleway Airlines", "Jetstream Regional", "Kitewing Air", "Lumen Airways",
    "Mistral Air Cargo", "Northlight Airlines", "Orbitwing Aviation", "Pinnacle Air",
    "Quicksilver Airways", "Ridgeline Air", "Skylark Airlines", "Trailwind Aviation",
]

_POOL_AVIATION_SITE: List[str] = [
    "Ashgrove Regional Airport", "Brightfield Airport", "Cliffside Airport", "Deepwater Airport",
    "Elmhurst Regional", "Fernvale Airport", "Glasshouse Airport", "Harrowgate Regional",
    "Inletview Airport", "Jamesport Airport", "Kirkwall Regional", "Longmeadow Airport",
    "Moorside Airport", "Newhaven Regional", "Ospreyfield Airport", "Portmeadow Airport",
    "Quinnbury Regional", "Rushmere Airport", "Stillwater Airport", "Thornbury Regional",
]

_POOL_AVIATION_ASSET: List[str] = [
    "Airframe Arclight", "Airframe Bluefin", "Airframe Cirrus", "Airframe Daybreak",
    "Airframe Everest", "Airframe Fairwind", "Airframe Glider", "Airframe Horizon",
    "Airframe Ionosphere", "Airframe Jubilee", "Airframe Keystone", "Airframe Lattice",
    "Airframe Mariner", "Airframe Nimbus", "Airframe Overcast", "Airframe Polaris",
    "Airframe Quill", "Airframe Rainshadow", "Airframe Stratus", "Airframe Trailblazer",
    "Airframe Updraft", "Airframe Vantage", "Airframe Windrose", "Airframe Zenith",
]

_POOL_GRID_ORG: List[str] = [
    "Northfield Power Cooperative", "Baywater Utilities", "Cedarline Energy", "Dunfield Grid Services",
    "Eastmoor Electric", "Fallbrook Energy", "Greenhollow Utilities", "Highvale Power",
    "Ironvale Grid", "Junction Power Authority", "Kernwood Energy", "Lakevale Electric",
    "Millstream Utilities", "Norvale Grid Co", "Overbrook Energy", "Pinehaven Power",
]

_POOL_GRID_SITE: List[str] = [
    "Substation Alderwood", "Substation Brookmill", "Substation Coalfield", "Substation Draper",
    "Substation Eastgate", "Substation Fenwick", "Substation Granby", "Substation Hollowell",
    "Substation Ironbridge", "Substation Jessup", "Substation Kelvin", "Substation Lindum",
    "Substation Marsden", "Substation Northcote", "Substation Orwell", "Substation Pennington",
    "Substation Quarrydale", "Substation Renshaw", "Substation Stanhope", "Substation Tilbury",
]

_POOL_GRID_ASSET: List[str] = [
    "Feeder-A1", "Feeder-A2", "Feeder-B1", "Feeder-B2", "Feeder-C1", "Feeder-C2",
    "Transformer-TX01", "Transformer-TX02", "Transformer-TX03", "Transformer-TX04",
    "Recloser-RC11", "Recloser-RC12", "Recloser-RC13", "Capacitor-CB21", "Capacitor-CB22",
    "Regulator-VR31", "Regulator-VR32", "Inverter-INV41", "Inverter-INV42", "Meter-MTR51",
]

_POOL_ENERGY_ORG: List[str] = [
    "Ardenne Power Works", "Blackridge Generation", "Coldstream Energy Board", "Deanfield Power",
    "Ellerby Generation", "Fairlow Energy", "Grangewood Power", "Hartsmere Generation",
    "Inglewood Energy", "Kirkbourne Power", "Lyndale Generation", "Maybridge Energy",
]

_POOL_ENERGY_SITE: List[str] = [
    "Ravensworth Plant", "Sableford Plant", "Tamworth Plant", "Underhill Plant", "Vale End Plant",
    "Wrenbury Plant", "Yealand Plant", "Ashcombe Plant", "Barrowdale Plant", "Cranfield Plant",
    "Dorrington Plant", "Edgewater Plant", "Foxdale Plant", "Grimsby Point Plant",
]

_POOL_SHIPPING_ORG: List[str] = [
    "Anchorline Shipping", "Bayreach Maritime", "Coralway Lines", "Deepharbour Maritime",
    "Ebbtide Shipping", "Fathomline Maritime", "Gulfstar Lines", "Headland Maritime",
    "Isobar Shipping", "Jetsam Lines", "Keelwater Maritime", "Longshore Lines",
    "Mooringside Shipping", "Netloft Maritime", "Offing Lines", "Portbow Maritime",
]

_POOL_SHIPPING_SITE: List[str] = [
    "Port Ardmore", "Port Beltane", "Port Carrick", "Port Dunmara", "Port Elmsgate",
    "Port Fairlight", "Port Glenbay", "Port Havenrock", "Port Ilfracombe", "Port Jetland",
    "Port Kilnsea", "Port Lyndhaven", "Port Marnock", "Port Newquay", "Port Oysterbed",
    "Port Pellow", "Port Quayhead", "Port Ravensbay", "Port Saltmarsh", "Port Trevose",
]

_POOL_SHIPPING_ASSET: List[str] = [
    "MV Arbourfield", "MV Brentmoor", "MV Calderstone", "MV Dunholme", "MV Eskdale",
    "MV Fenhurst", "MV Garrowby", "MV Hollinwood", "MV Inglestone", "MV Jervaulx",
    "MV Kirkstall", "MV Laverton", "MV Marsdale", "MV Newlyn", "MV Oxhey",
    "MV Pickhill", "MV Quernmore", "MV Rothbury", "MV Speeton", "MV Thurlby",
]

#: Neutral person surrogates (never real public figures) - used for PII / NER
_POOL_PERSON: List[str] = [
    "A. Halloran", "B. Ingersoll", "C. Marchetti", "D. Fenwick", "E. Okonkwo", "F. Lindqvist",
    "G. Baptiste", "H. Sorensen", "I. Kavanagh", "J. Petrossian", "K. Ashworth", "L. Duvall",
    "M. Thorsen", "N. Calloway", "O. Rhodes", "P. Vasquez", "Q. Ellingham", "R. Nakamura",
    "S. Belanger", "T. Achebe", "U. Kostas", "V. Almeida", "W. Bramley", "X. Ferreira",
    "Y. Sandoval", "Z. Oyelaran", "A. Whitcombe", "B. Larsson", "C. Nazario", "D. Ferris",
    "E. Brightwell", "F. Cardoso", "G. Hallstrom", "H. Ravenscroft", "I. Delacroix", "J. Mbeki",
    "K. Sunderland", "L. Moreau", "M. Castellano", "N. Aldridge", "O. Kirchner", "P. Sandhu",
    "Q. Marlowe", "R. Ostrander", "S. Kalinski", "T. Beaumont", "U. Navarro", "V. Hirsch",
]

#: Neutral geo-political place surrogates (fictional civil districts)
_POOL_PLACE: List[str] = [
    "Ardenvale District", "Brackwater District", "Calderon District", "Dunmoor District",
    "Ellinsworth District", "Fairbourne District", "Greymouth District", "Halverton District",
    "Ironford District", "Jessamine District", "Kilbride District", "Lanmoor District",
    "Marchwood District", "Northaven District", "Oakhampton District", "Pemberley District",
    "Quenby District", "Ridgefield District", "Stonebury District", "Tarnwick District",
    "Uttoxbridge District", "Vearnham District", "Westhollow District", "Yarnbury District",
]

_POOL_ORG_GENERIC: List[str] = [
    "Alderpoint Holdings", "Brightmoor Group", "Cindercrest Industries", "Dovetail Partners",
    "Emberly Corporation", "Foxhollow Group", "Glimmerfield Industries", "Hartwell Holdings",
    "Ivorygate Partners", "Jackdaw Industries", "Kingfisher Group", "Lambourne Holdings",
    "Mosswood Partners", "Nettlefield Group", "Oriel Industries", "Pardoe Holdings",
]

_POOL_PROJECT_GENERIC: List[str] = [
    "Project Almanac", "Project Beltline", "Project Cornerstone", "Project Dovetail",
    "Project Evergreen", "Project Foundry", "Project Greenfield", "Project Hearthstone",
    "Project Ironclad", "Project Juniper", "Project Keystone", "Project Lighthouse",
    "Project Meridian", "Project Northstar", "Project Openfield", "Project Pinewood",
    "Project Quarry", "Project Redwood", "Project Skyline", "Project Trellis",
    "Project Umbrella", "Project Vantage", "Project Waypoint", "Project Yardline",
]

#: Handling tiers replacing classification markings (ordinal order preserved)
_POOL_HANDLING_TIER: List[str] = [
    "TIER-1 PUBLIC", "TIER-2 INTERNAL", "TIER-3 RESTRICTED", "TIER-4 CONTROLLED",
    "TIER-5 PRIVILEGED", "TIER-6 SEALED", "TIER-7 ESCROW", "TIER-8 ARCHIVE",
]

_POOL_STATUS_GENERIC: List[str] = [
    "STATE-ALPHA", "STATE-BRAVO", "STATE-CHARLIE", "STATE-DELTA", "STATE-ECHO",
    "STATE-FOXTROT", "STATE-GOLF", "STATE-HOTEL", "STATE-INDIA", "STATE-JULIET",
    "STATE-KILO", "STATE-LIMA", "STATE-MIKE", "STATE-NOVEMBER", "STATE-OSCAR", "STATE-PAPA",
]

_POOL_CATEGORY_GENERIC: List[str] = [
    "Category Ashen", "Category Bramble", "Category Cobalt", "Category Dunlin", "Category Elmwood",
    "Category Ferrite", "Category Gossamer", "Category Halcyon", "Category Indigo", "Category Jasper",
    "Category Kelvin", "Category Lichen", "Category Mulberry", "Category Nutmeg", "Category Onyx",
    "Category Pewter", "Category Quince", "Category Russet", "Category Sorrel", "Category Teal",
    "Category Umber", "Category Verdigris", "Category Wheaten", "Category Xanthic", "Category Yarrow",
    "Category Zephyr",
]


# --------------------------------------------------------------------------- #
#  3. DOMAIN PROFILE REGISTRY
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DomainProfile:
    """An immutable, offline domain-shift specification."""

    key: str
    title: str
    source_domain: str
    cover_domain: str
    description: str
    token_shifts: Mapping[str, str]
    pools: Mapping[str, Sequence[str]]
    #: Ordered rewrite keys (longest first) - precomputed for determinism.
    _ordered_keys: Tuple[str, ...] = field(default=(), repr=False, compare=False)

    def ordered_shift_keys(self) -> Tuple[str, ...]:
        if self._ordered_keys:
            return self._ordered_keys
        keys = tuple(sorted(self.token_shifts.keys(), key=lambda k: (-len(k), k)))
        object.__setattr__(self, "_ordered_keys", keys)
        return keys

    def pool(self, semantic_class: str) -> Sequence[str]:
        """Return the surrogate pool for a semantic class, with safe fallback."""
        return self.pools.get(semantic_class) or self.pools["GENERIC"]


def _merge(*dicts: Mapping[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for d in dicts:
        out.update(d)
    return out


_COMMON_POOLS: Dict[str, Sequence[str]] = {
    "PERSON": _POOL_PERSON,
    "PLACE": _POOL_PLACE,
    "PROJECT": _POOL_PROJECT_GENERIC,
    "HANDLING_TIER": _POOL_HANDLING_TIER,
    "STATUS": _POOL_STATUS_GENERIC,
    "GENERIC": _POOL_CATEGORY_GENERIC,
}

DOMAIN_PROFILES: Dict[str, DomainProfile] = {
    "defense_to_logistics": DomainProfile(
        key="defense_to_logistics",
        title="Kinetic Defense → Civil Freight Logistics",
        source_domain="Kinetic defense / joint fires / targeting",
        cover_domain="Commercial freight, haulage and supply-chain operations",
        description=(
            "Projects kinetic-effects vocabulary (strike packages, warheads, targets, "
            "callsigns, clearances) into a civil freight logistics domain. Aggregates, "
            "cardinalities and join topology are preserved exactly."
        ),
        token_shifts=_merge(_SHIFT_DEFENSE_TO_LOGISTICS, _SHIFT_PII_COMMON),
        pools={
            **_COMMON_POOLS,
            "ORG": _POOL_LOGISTICS_ORG,
            "SITE": _POOL_LOGISTICS_SITE,
            "ROUTE": _POOL_LOGISTICS_ROUTE,
            "ASSET": _POOL_LOGISTICS_ASSET,
            "PROJECT": _POOL_LOGISTICS_PROGRAMME,
        },
    ),
    "aerospace_to_civil_aviation": DomainProfile(
        key="aerospace_to_civil_aviation",
        title="Military Aerospace → Commercial Aviation",
        source_domain="Combat aviation, air tasking orders, air defence",
        cover_domain="Scheduled commercial and cargo aviation operations",
        description=(
            "Projects air-tasking and combat-aviation vocabulary into scheduled civil "
            "aviation (rotations, flight profiles, registrations, airports)."
        ),
        token_shifts=_merge(
            _SHIFT_AEROSPACE_TO_CIVIL_AVIATION, _SHIFT_DEFENSE_TO_LOGISTICS, _SHIFT_PII_COMMON
        ),
        pools={
            **_COMMON_POOLS,
            "ORG": _POOL_AVIATION_ORG,
            "SITE": _POOL_AVIATION_SITE,
            "ROUTE": _POOL_LOGISTICS_ROUTE,
            "ASSET": _POOL_AVIATION_ASSET,
        },
    ),
    "cyberwar_to_smartgrid": DomainProfile(
        key="cyberwar_to_smartgrid",
        title="Cyber Warfare → Smart-Grid Telemetry",
        source_domain="Offensive/defensive cyber operations, C2 infrastructure",
        cover_domain="Distribution-grid SCADA telemetry and asset health monitoring",
        description=(
            "Projects offensive-cyber tradecraft (implants, C2, exfiltration, exploits) "
            "into benign smart-grid SCADA telemetry and fault-diagnostics language."
        ),
        token_shifts=_merge(_SHIFT_CYBERWAR_TO_SMARTGRID, _SHIFT_PII_COMMON),
        pools={
            **_COMMON_POOLS,
            "ORG": _POOL_GRID_ORG,
            "SITE": _POOL_GRID_SITE,
            "ROUTE": _POOL_LOGISTICS_ROUTE,
            "ASSET": _POOL_GRID_ASSET,
        },
    ),
    "nuclear_to_civil_energy": DomainProfile(
        key="nuclear_to_civil_energy",
        title="Strategic Forces → Civil Energy Utility",
        source_domain="Strategic deterrent, fissile inventory, alert posture",
        cover_domain="Civil power generation, plant output and asset stewardship",
        description=(
            "Projects strategic-forces inventory and posture data into civil power "
            "generation capacity, purity grades and plant readiness."
        ),
        token_shifts=_merge(
            _SHIFT_NUCLEAR_TO_CIVIL_ENERGY, _SHIFT_DEFENSE_TO_LOGISTICS, _SHIFT_PII_COMMON
        ),
        pools={
            **_COMMON_POOLS,
            "ORG": _POOL_ENERGY_ORG,
            "SITE": _POOL_ENERGY_SITE,
            "ROUTE": _POOL_LOGISTICS_ROUTE,
            "ASSET": _POOL_GRID_ASSET,
        },
    ),
    "naval_to_commercial_shipping": DomainProfile(
        key="naval_to_commercial_shipping",
        title="Naval Operations → Commercial Shipping",
        source_domain="Surface/subsurface naval operations and sea control",
        cover_domain="Container liner services, port calls and maritime logistics",
        description=(
            "Projects naval order-of-battle and sea-control vocabulary into commercial "
            "liner shipping, port terminals and vessel scheduling."
        ),
        token_shifts=_merge(
            _SHIFT_NAVAL_TO_COMMERCIAL_SHIPPING, _SHIFT_DEFENSE_TO_LOGISTICS, _SHIFT_PII_COMMON
        ),
        pools={
            **_COMMON_POOLS,
            "ORG": _POOL_SHIPPING_ORG,
            "SITE": _POOL_SHIPPING_SITE,
            "ROUTE": _POOL_LOGISTICS_ROUTE,
            "ASSET": _POOL_SHIPPING_ASSET,
        },
    ),
    "generic_pii_redaction": DomainProfile(
        key="generic_pii_redaction",
        title="Generic Proprietary / PII → Neutral Corporate",
        source_domain="Enterprise proprietary records containing PII",
        cover_domain="Neutral corporate directory and programme records",
        description=(
            "Domain-agnostic profile for enterprise R&D and HR datasets: renames PII "
            "headers and bijectively substitutes person, org and project entities."
        ),
        token_shifts=dict(_SHIFT_PII_COMMON),
        pools={
            **_COMMON_POOLS,
            "ORG": _POOL_ORG_GENERIC,
            "SITE": _POOL_PLACE,
            "ROUTE": _POOL_LOGISTICS_ROUTE,
            "ASSET": _POOL_LOGISTICS_ASSET,
        },
    ),
}


# --------------------------------------------------------------------------- #
#  3b. LEXICON EXPANSION
# --------------------------------------------------------------------------- #
# `core.lexicon` supplies large, deterministically-composed surrogate pools and
# two additional cover domains. They are merged in here rather than inlined
# above so the base ontology stays small enough to review by hand.
#
# Merge policy: the ORIGINAL v1.0 pool entries are kept FIRST, with the
# expanded entries appended and de-duplicated. Because the engine allocates
# surrogates by walking a pool in order, this means every mapping produced by
# v1.0 for a given (profile, seed, entity-count) prefix remains reproducible,
# while large datasets gain hundreds or thousands of extra natural-looking
# surrogates instead of falling back to numeric suffixing.

from core import lexicon as _lexicon  # noqa: E402  (deliberate late import)


def _extend_pool(
    original: Sequence[str], expanded: Sequence[str]
) -> Tuple[str, ...]:
    """Append `expanded` to `original`, de-duplicating, order-stable."""
    seen: set = set()
    out: List[str] = []
    for item in list(original) + list(expanded):
        if item not in seen:
            seen.add(item)
            out.append(item)
    return tuple(out)


def _apply_lexicon_expansion() -> None:
    """Merge lexicon pools into existing profiles and register new domains."""
    # --- 1. widen the pools of the six base profiles ----------------------
    for profile_key, extra_pools in _lexicon.EXPANDED_POOLS.items():
        profile = DOMAIN_PROFILES.get(profile_key)
        if profile is None:
            continue
        widened: Dict[str, Sequence[str]] = dict(profile.pools)
        for semantic_class, pool in extra_pools.items():
            widened[semantic_class] = _extend_pool(
                widened.get(semantic_class, ()), pool
            )
        object.__setattr__(profile, "pools", widened)

    # --- 2. register the additional cover domains -------------------------
    for spec in _lexicon.EXTRA_PROFILE_SPECS:
        key = str(spec["key"])
        if key in DOMAIN_PROFILES:
            continue
        spec_pools: Mapping[str, Sequence[str]] = spec["pools"]  # type: ignore[assignment]
        merged_pools: Dict[str, Sequence[str]] = {**_COMMON_POOLS}
        for semantic_class, pool in spec_pools.items():
            merged_pools[semantic_class] = _extend_pool(
                merged_pools.get(semantic_class, ()), pool
            )
        DOMAIN_PROFILES[key] = DomainProfile(
            key=key,
            title=str(spec["title"]),
            source_domain=str(spec["source_domain"]),
            cover_domain=str(spec["cover_domain"]),
            description=str(spec["description"]),
            token_shifts=_merge(
                spec["token_shifts"],  # type: ignore[arg-type]
                _SHIFT_PII_COMMON,
            ),
            pools=merged_pools,
        )


_apply_lexicon_expansion()


def profile_pool_sizes(key: str) -> Dict[str, int]:
    """Return the surrogate pool size per semantic class for one profile."""
    profile = get_profile(key)
    return {name: len(vals) for name, vals in sorted(profile.pools.items())}


def lexicon_report() -> Dict[str, object]:
    """Aggregate lexicon capacity, surfaced by /api/v1/attestation."""
    unique: set = set()
    per_profile: Dict[str, Dict[str, int]] = {}
    for key, profile in DOMAIN_PROFILES.items():
        per_profile[key] = {n: len(v) for n, v in sorted(profile.pools.items())}
        for vals in profile.pools.values():
            unique.update(vals)
    return {
        "profiles": len(DOMAIN_PROFILES),
        "surrogate_pools_per_profile": per_profile,
        "total_unique_surrogates": len(unique),
        "total_token_shift_rules": sum(
            len(p.token_shifts) for p in DOMAIN_PROFILES.values()
        ),
        "sensitivity_rules": len(SENSITIVITY_RULES),
        "ner_patterns": len(NER_PATTERNS),
    }


def list_profiles() -> List[Dict[str, str]]:
    """Return a JSON-serialisable catalogue of available domain profiles."""
    return [
        {
            "key": p.key,
            "title": p.title,
            "source_domain": p.source_domain,
            "cover_domain": p.cover_domain,
            "description": p.description,
            "token_rules": str(len(p.token_shifts)),
        }
        for p in DOMAIN_PROFILES.values()
    ]


def get_profile(key: str) -> DomainProfile:
    """Fetch a domain profile, raising a precise error for unknown keys."""
    try:
        return DOMAIN_PROFILES[key]
    except KeyError:
        raise KeyError(
            f"Unknown domain profile '{key}'. Available: {sorted(DOMAIN_PROFILES)}"
        ) from None


# --------------------------------------------------------------------------- #
#  4. SENSITIVITY PROFILER RULES  (deterministic, regex + gazetteer, offline)
# --------------------------------------------------------------------------- #
# Each rule: (rule_id, severity 1-5, target 'name'|'value'|'both', regex source)
# Regexes are compiled once by core.profiler; kept as raw strings here so the
# ruleset can be exported and reviewed as data by an accreditor.

SENSITIVITY_RULES: List[Dict[str, object]] = [
    # --- classification & handling markings --------------------------------
    {
        "id": "CLASSIFICATION_MARKING",
        "severity": 5,
        "target": "both",
        "category": "classification",
        "pattern": r"\b(TOP\s?SECRET|SECRET|CONFIDENTIAL|NOFORN|ORCON|REL\s?TO|FOUO|CUI|"
                   r"UNCLASSIFIED|RESTRICTED|COSMIC|ATOMAL|SCI|SAP|TS/SCI|NATO\s+SECRET)\b",
        "explain": "Security classification or handling caveat marking detected.",
    },
    {
        "id": "CLEARANCE_TAG",
        "severity": 5,
        "target": "both",
        "category": "classification",
        "pattern": r"\b(clearance|cleared|compartment|codeword|caveat|bigot\s?list|need[_\s-]?to[_\s-]?know)\b",
        "explain": "Personnel clearance / compartment indicator.",
    },
    # --- kinetic / weapons --------------------------------------------------
    {
        "id": "KINETIC_IDENTIFIER",
        "severity": 5,
        "target": "both",
        "category": "kinetic",
        "pattern": r"\b(warhead|missile|munition[s]?|ordnance|payload[_\s-]?yield|detonat\w*|"
                   r"explosive|torpedo|kill[_\s-]?chain|kill[_\s-]?probability|lethality|"
                   r"strike|sortie[s]?|fire[_\s-]?mission|weapon[s]?[_\s-]?system|aimpoint)\b",
        "explain": "Kinetic weapons/effects identifier.",
    },
    {
        "id": "TARGETING_SEMANTICS",
        "severity": 4,
        "target": "both",
        "category": "kinetic",
        "pattern": r"\b(target(ing)?|engagement[_\s-]?zone|threat[_\s-]?axis|hostile|adversary|"
                   r"enemy|blast[_\s-]?radius|standoff|no[_\s-]?fly[_\s-]?zone)\b",
        "explain": "Targeting or threat-engagement semantics.",
    },
    # --- callsigns & unit designators --------------------------------------
    {
        "id": "NATO_PHONETIC_CALLSIGN",
        "severity": 4,
        "target": "value",
        "category": "callsign",
        "pattern": r"\b(ALPHA|BRAVO|CHARLIE|DELTA|ECHO|FOXTROT|GOLF|HOTEL|INDIA|JULIETT?|KILO|"
                   r"LIMA|MIKE|NOVEMBER|OSCAR|PAPA|QUEBEC|ROMEO|SIERRA|TANGO|UNIFORM|VICTOR|"
                   r"WHISKEY|XRAY|X-RAY|YANKEE|ZULU)[\s\-]?\d{1,3}\b",
        "explain": "NATO phonetic callsign with numeric suffix.",
    },
    {
        "id": "UNIT_DESIGNATOR",
        "severity": 4,
        "target": "both",
        "category": "orbat",
        "pattern": r"\b(\d{1,3}(st|nd|rd|th)\s+(Squadron|Battalion|Regiment|Brigade|Wing|Fleet|Division)|"
                   r"squadron|battalion|regiment|brigade|task[_\s-]?force|battle[_\s-]?group)\b",
        "explain": "Order-of-battle unit designator.",
    },
    # --- geospatial ---------------------------------------------------------
    {
        "id": "MGRS_GRID",
        "severity": 5,
        "target": "value",
        "category": "geospatial",
        "pattern": r"\b\d{1,2}[C-HJ-NP-X][A-HJ-NP-Z]{2}\d{4,10}\b",
        "explain": "MGRS / USNG military grid reference.",
    },
    {
        "id": "DMS_COORDINATE",
        "severity": 4,
        "target": "value",
        "category": "geospatial",
        "pattern": r"\b\d{1,3}[°:]\s?\d{1,2}['′:]\s?\d{1,2}(\.\d+)?[\"″]?\s?[NSEW]\b",
        "explain": "Degree-minute-second geographic coordinate.",
    },
    {
        "id": "GEO_COLUMN",
        "severity": 3,
        "target": "name",
        "category": "geospatial",
        "pattern": r"\b(lat(itude)?|lon(g|gitude)?|coord(inate)?s?|geohash|mgrs|utm|easting|northing|"
                   r"grid[_\s-]?ref\w*|waypoint|bearing|azimuth)\b",
        "explain": "Geospatial column - precise location may be sensitive.",
    },
    # --- telemetry / signatures --------------------------------------------
    {
        "id": "TELEMETRY_RATE",
        "severity": 3,
        "target": "name",
        "category": "telemetry",
        "pattern": r"\b(telemetry[_\s-]?rate|sample[_\s-]?rate|burst[_\s-]?rate|pulse[_\s-]?width|"
                   r"prf|duty[_\s-]?cycle|freq(uency)?[_\s-]?hop\w*|emitter|rcs|radar[_\s-]?cross)\b",
        "explain": "Emitter/telemetry performance parameter (signature-revealing).",
    },
    # --- intelligence tradecraft -------------------------------------------
    {
        "id": "INT_DISCIPLINE",
        "severity": 5,
        "target": "both",
        "category": "intelligence",
        "pattern": r"\b(sigint|humint|geoint|elint|masint|osint|imint|source[_\s-]?code[_\s-]?name|"
                   r"safe[_\s-]?house|handler|operative|asset[_\s-]?id|exfil\w*|infil\w*|covert|clandestine)\b",
        "explain": "Intelligence discipline or tradecraft term.",
    },
    # --- PII ---------------------------------------------------------------
    {
        "id": "EMAIL_ADDRESS",
        "severity": 4,
        "target": "value",
        "category": "pii",
        "pattern": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
        "explain": "E-mail address (direct identifier).",
    },
    {
        "id": "US_SSN",
        "severity": 5,
        "target": "value",
        "category": "pii",
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "explain": "US Social Security Number pattern.",
    },
    {
        "id": "PHONE_NUMBER",
        "severity": 3,
        "target": "value",
        "category": "pii",
        "pattern": r"(?<!\d)(\+\d{1,3}[\s\-.]?)?(\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)",
        "explain": "Telephone number pattern.",
    },
    {
        "id": "IPV4_ADDRESS",
        "severity": 3,
        "target": "value",
        "category": "network",
        "pattern": r"\b((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b",
        "explain": "IPv4 address (infrastructure disclosure).",
    },
    {
        "id": "MAC_ADDRESS",
        "severity": 3,
        "target": "value",
        "category": "network",
        "pattern": r"\b([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}\b",
        "explain": "Hardware MAC address.",
    },
    {
        "id": "PII_COLUMN",
        "severity": 4,
        "target": "name",
        "category": "pii",
        "pattern": r"\b(ssn|social[_\s-]?security|national[_\s-]?id|passport|dob|date[_\s-]?of[_\s-]?birth|"
                   r"first[_\s-]?name|last[_\s-]?name|surname|full[_\s-]?name|email|phone|mobile|"
                   r"address|postcode|zip[_\s-]?code|salary|iban|bank[_\s-]?account|credit[_\s-]?card|"
                   r"biometric|fingerprint|medical|diagnosis|next[_\s-]?of[_\s-]?kin)\b",
        "explain": "Column name indicates personally identifiable information.",
    },
    # --- credentials & keys -------------------------------------------------
    {
        "id": "SECRET_MATERIAL",
        "severity": 5,
        "target": "both",
        "category": "credential",
        "pattern": r"\b(api[_\s-]?key|secret[_\s-]?key|private[_\s-]?key|password|passphrase|token|"
                   r"credential|BEGIN\s+(RSA|EC|OPENSSH|PGP)\s+PRIVATE\s+KEY)\b",
        "explain": "Credential or key material.",
    },
    # --- proprietary / export control --------------------------------------
    {
        "id": "EXPORT_CONTROL",
        "severity": 5,
        "target": "both",
        "category": "export_control",
        "pattern": r"\b(ITAR|EAR99|ECCN|USML|export[_\s-]?control(led)?|dual[_\s-]?use)\b",
        "explain": "Export-control marking (ITAR/EAR).",
    },
    {
        "id": "PROPRIETARY_MARKER",
        "severity": 3,
        "target": "both",
        "category": "proprietary",
        "pattern": r"\b(proprietary|trade[_\s-]?secret|internal[_\s-]?only|company[_\s-]?confidential|"
                   r"patent[_\s-]?pending|do[_\s-]?not[_\s-]?distribute)\b",
        "explain": "Proprietary / trade-secret marker.",
    },
    # --- cyber offensive ----------------------------------------------------
    {
        "id": "CYBER_OFFENSIVE",
        "severity": 5,
        "target": "both",
        "category": "cyber",
        "pattern": r"\b(implant|c2|command[_\s-]?and[_\s-]?control|beacon|dropper|zero[_\s-]?day|"
                   r"0day|exploit|payload[_\s-]?hash|malware|backdoor|rootkit|lateral[_\s-]?movement|"
                   r"privilege[_\s-]?escalation)\b",
        "explain": "Offensive cyber tooling or tradecraft reference.",
    },
]

#: Explicit gazetteer used by the profiler for exact-token classification hits.
CLASSIFICATION_TOKENS: Tuple[str, ...] = (
    "TOP SECRET", "TOPSECRET", "TS", "SECRET", "CONFIDENTIAL", "RESTRICTED", "UNCLASSIFIED",
    "NOFORN", "ORCON", "FOUO", "CUI", "SCI", "SAP", "NATO SECRET", "COSMIC TOP SECRET",
)


# --------------------------------------------------------------------------- #
#  5. OFFLINE RULE-BASED NER PATTERNS
# --------------------------------------------------------------------------- #
# Deterministic, dependency-free entity recognition for narrative free-text
# columns. Each pattern maps a matched span to a semantic class, which selects
# the surrogate pool used for bijective replacement.
#
# If spaCy + a locally-bundled en_core_web_sm wheel is present in the air-gapped
# image, core.nlp will additionally use it; these rules remain the deterministic
# backbone and always run first so output is reproducible with or without spaCy.

NER_PATTERNS: List[Dict[str, object]] = [
    {
        "label": "PERSON",
        "priority": 30,
        "pattern": r"\b(?:Col|Colonel|Gen|General|Maj|Major|Capt|Captain|Lt|Lieutenant|Sgt|Sergeant|"
                   r"Adm|Admiral|Cdr|Commander|Dr|Mr|Mrs|Ms|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
    },
    {
        "label": "PERSON",
        "priority": 20,
        "pattern": r"\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?=\s+(?:reported|stated|confirmed|signed|"
                   r"authorised|authorized|approved|led|commanded|briefed))",
    },
    {
        "label": "ORG",
        "priority": 28,
        "pattern": r"\b[A-Z][A-Za-z&.\-]+(?:\s+[A-Z][A-Za-z&.\-]+){0,3}\s+"
                   r"(?:Corporation|Corp|Incorporated|Inc|Limited|Ltd|LLC|GmbH|PLC|Group|Holdings|"
                   r"Industries|Systems|Technologies|Defence|Defense|Aerospace|Command|Agency|Bureau|Directorate)\b",
    },
    {
        "label": "ASSET",
        "priority": 34,
        "pattern": r"\b(?:USS|HMS|MV|SS|RFA)\s+[A-Z][A-Za-z\-]+\b",
    },
    {
        "label": "ASSET",
        "priority": 33,
        "pattern": r"\b(?:F|B|A|C|E|KC|MQ|RQ|AH|UH|CH|SH)[\-‑]\d{1,3}[A-Z]?\b",
    },
    {
        "label": "PROJECT",
        "priority": 32,
        "pattern": r"\b(?:Operation|Project|Programme|Program|Exercise|Task\s+Force)\s+"
                   r"[A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+)?\b",
    },
    {
        # "Target BASTION", "Objective REDLINE", "Waypoint IRONGATE"
        "label": "SITE",
        "priority": 39,
        "pattern": r"\b(?:Target|Objective|Waypoint|Aimpoint|Checkpoint|Sector)\s+"
                   r"(?:[A-Z][A-Z0-9\-]{2,}|[A-Z][a-z]+)\b",
    },
    {
        "label": "SITE",
        "priority": 26,
        "pattern": r"\b(?:Camp|Fort|Base|Airbase|Air\s+Base|Naval\s+Station|Station|Depot|Facility|"
                   r"Installation|Site)\s+[A-Z][A-Za-z\-]+\b",
    },
    {
        # Bare all-caps operational codewords: BASTION, IRONGATE, NIGHTFALL.
        # Deliberately low priority so that any longer, more specific span
        # (e.g. "Target BASTION" above) always wins arbitration.
        "label": "PROJECT",
        "priority": 12,
        "pattern": r"\b[A-Z]{5,}(?:[\-_][A-Z0-9]+)?\b",
    },
    {
        "label": "SITE",
        "priority": 25,
        "pattern": r"\b[A-Z][A-Za-z\-]+\s+(?:Airfield|Airbase|Shipyard|Arsenal|Proving\s+Ground|Range)\b",
    },
    {
        "label": "CALLSIGN",
        "priority": 36,
        "pattern": r"\b(?:ALPHA|BRAVO|CHARLIE|DELTA|ECHO|FOXTROT|GOLF|HOTEL|INDIA|JULIET|JULIETT|KILO|"
                   r"LIMA|MIKE|NOVEMBER|OSCAR|PAPA|QUEBEC|ROMEO|SIERRA|TANGO|UNIFORM|VICTOR|WHISKEY|"
                   r"XRAY|YANKEE|ZULU)[\s\-]?\d{1,3}\b",
    },
    {
        "label": "GRID",
        "priority": 38,
        "pattern": r"\b\d{1,2}[C-HJ-NP-X][A-HJ-NP-Z]{2}\d{4,10}\b",
    },
    {
        "label": "COORD",
        "priority": 37,
        "pattern": r"\b\d{1,3}\.\d{3,}\s*[,/]\s*[\-]?\d{1,3}\.\d{3,}\b",
    },
    {
        "label": "CLASSIFICATION",
        "priority": 40,
        "pattern": r"\b(?:TOP\s?SECRET(?://[A-Z]+)*|SECRET(?://[A-Z]+)*|CONFIDENTIAL|NOFORN|CUI|FOUO)\b",
    },
    {
        "label": "EMAIL",
        "priority": 35,
        "pattern": r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
    },
    {
        "label": "IP",
        "priority": 31,
        "pattern": r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b",
    },
    {
        "label": "SERIAL",
        "priority": 22,
        "pattern": r"\b[A-Z]{2,5}[\-/]?\d{3,8}(?:[\-/][A-Z0-9]{1,5})?\b",
    },
]

#: Map NER labels onto surrogate pools.
NER_LABEL_TO_POOL: Dict[str, str] = {
    "PERSON": "PERSON",
    "ORG": "ORG",
    "ASSET": "ASSET",
    "PROJECT": "PROJECT",
    "SITE": "SITE",
    "CALLSIGN": "ASSET",
    "GRID": "SITE",
    "COORD": "SITE",
    "CLASSIFICATION": "HANDLING_TIER",
    "EMAIL": "GENERIC",
    "IP": "GENERIC",
    "SERIAL": "GENERIC",
    "PLACE": "PLACE",
}


# --------------------------------------------------------------------------- #
#  7. LEXICON-SUPPLIED SENSITIVITY RULES
# --------------------------------------------------------------------------- #
# Additional detectors (CBRN, financial-intelligence, PHI, biometrics, embedded
# credentials, overhead-collection tasking, legal privilege) live in
# `core.lexicon` as reviewable data and are appended here so `core.profiler`
# compiles them alongside the base ruleset. Duplicate rule ids are ignored so
# repeated imports remain idempotent.

def _append_lexicon_rules() -> None:
    existing = {str(rule["id"]) for rule in SENSITIVITY_RULES}
    for rule in _lexicon.EXTRA_SENSITIVITY_RULES:
        if str(rule["id"]) not in existing:
            SENSITIVITY_RULES.append(dict(rule))
            existing.add(str(rule["id"]))


_append_lexicon_rules()


#: Additional rule-based NER patterns unlocked by the expanded lexicon.
_EXTRA_NER_PATTERNS: List[Dict[str, object]] = [
    {
        "label": "IBAN",
        "priority": 34,
        "pattern": r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}[A-Z0-9]{1,4}\b",
    },
    {
        "label": "WALLET",
        "priority": 33,
        "pattern": r"\b(?:bc1[a-z0-9]{25,62}|0x[a-fA-F0-9]{40})\b",
    },
    {
        "label": "SECRET",
        "priority": 36,
        "pattern": r"\b(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,})\b",
    },
    {
        "label": "MRN",
        "priority": 30,
        "pattern": r"\bMRN[\-: ]?\d{6,10}\b",
    },
    {
        "label": "PHONE",
        "priority": 29,
        "pattern": r"(?<!\d)\+?\d{1,3}[ \-.]?\(?\d{2,4}\)?[ \-.]?\d{3,4}[ \-.]?\d{3,4}(?!\d)",
    },
    {
        "label": "URL",
        "priority": 28,
        "pattern": r"\bhttps?://[^\s<>\"']{4,}\b",
    },
    {
        "label": "MAC",
        "priority": 27,
        "pattern": r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
    },
    {
        "label": "IMO",
        "priority": 26,
        "pattern": r"\bIMO[\s\-]?\d{7}\b",
    },
    {
        "label": "ICAO24",
        "priority": 25,
        "pattern": r"\b(?:ICAO|HEX)[\s\-]?[0-9A-F]{6}\b",
    },
    {
        "label": "NDC",
        "priority": 24,
        "pattern": r"\bNDC[\s\-]?\d{4,5}-\d{3,4}-\d{1,2}\b",
    },
]


def _append_lexicon_ner_patterns() -> None:
    existing = {str(p["label"]) for p in NER_PATTERNS}
    for pattern in _EXTRA_NER_PATTERNS:
        if str(pattern["label"]) not in existing:
            NER_PATTERNS.append(dict(pattern))
            existing.add(str(pattern["label"]))
    NER_PATTERNS.sort(key=lambda p: (-int(p["priority"]), str(p["label"])))


_append_lexicon_ner_patterns()

#: Extend the label→pool routing for the new detectors.
NER_LABEL_TO_POOL.update(
    {
        "IBAN": "GENERIC",
        "WALLET": "GENERIC",
        "SECRET": "GENERIC",
        "MRN": "GENERIC",
        "PHONE": "GENERIC",
        "URL": "GENERIC",
        "MAC": "GENERIC",
        "IMO": "ASSET",
        "ICAO24": "ASSET",
        "NDC": "GENERIC",
    }
)
