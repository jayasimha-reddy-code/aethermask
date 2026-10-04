"""
AetherMask (CipherShift) :: core.lexicon
========================================
Expanded surrogate lexicon and additional domain-shift matrices.

Why this module exists
----------------------
`core.ontology` defines the *structure* of a domain projection (profiles,
rules, NER patterns). This module supplies the *volume*: large, realistic
surrogate pools and extra cover domains. Keeping them separate lets an
accreditation authority review the lexicon as pure data without wading
through engine wiring.

Pool construction policy
------------------------
Pools are built from curated stems and expanded **deterministically** via
`_compose()`, which produces a sorted, de-duplicated cartesian product. This
yields large pools (hundreds to thousands of surrogates) that are:

  * fully reproducible - no RNG, no host entropy, no ordering dependence
  * auditable - the stems are short, human-reviewable lists
  * realistic - every surrogate reads like a genuine civil-sector name
  * collision-resistant - large pools mean the engine rarely needs to fall
    back to numeric suffixing, so masked data stays natural-looking

All pools are plain tuples of `str`. No I/O, no network, no imports beyond
the standard library.
"""

from __future__ import annotations

from collections.abc import Sequence

__all__ = [
    "EXPANDED_POOLS",
    "EXTRA_PROFILE_SPECS",
    "EXTRA_SENSITIVITY_RULES",
    "EXTRA_TOKEN_SHIFTS",
    "pool_statistics",
]


# --------------------------------------------------------------------------- #
#  Deterministic composition helper
# --------------------------------------------------------------------------- #
def _compose(*parts: Sequence[str], sep: str = " ") -> tuple[str, ...]:
    """
    Deterministic cartesian product of stem lists.

    Sorted and de-duplicated so the resulting pool ordering is identical on
    every host and every Python build, which is a hard requirement for
    reproducible `.ciphermap` files.
    """
    out: list[str] = []
    seen: set[str] = set()

    def walk(idx: int, acc: list[str]) -> None:
        if idx == len(parts):
            s = sep.join(acc)
            if s not in seen:
                seen.add(s)
                out.append(s)
            return
        for token in parts[idx]:
            acc.append(token)
            walk(idx + 1, acc)
            acc.pop()

    walk(0, [])
    return tuple(sorted(out))


def _merge_pools(*pools: Sequence[str]) -> tuple[str, ...]:
    """Concatenate pools, de-duplicating while preserving deterministic order."""
    seen: set[str] = set()
    out: list[str] = []
    for pool in pools:
        for item in pool:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return tuple(out)


# --------------------------------------------------------------------------- #
#  Shared geographic / descriptive stems (British + North American civil flavour)
# --------------------------------------------------------------------------- #
_STEM_PLACE_A: tuple[str, ...] = (
    "Alder", "Ash", "Aspen", "Bay", "Birch", "Black", "Bram", "Bridge", "Bright",
    "Brook", "Cedar", "Chester", "Clay", "Clear", "Cold", "Copper", "Corn",
    "Cross", "Dale", "Deer", "Dun", "East", "Elm", "Ember", "Fair", "Fall",
    "Fern", "Field", "Flint", "Fox", "Glen", "Gold", "Grange", "Granite",
    "Green", "Grey", "Hart", "Harbour", "Haven", "Hazel", "High", "Holly",
    "Iron", "Ivy", "Kes", "King", "Lake", "Lark", "Laurel", "Lime", "Long",
    "Maple", "Marsh", "Mead", "Mill", "Moor", "Moss", "North", "Oak", "Orchard",
    "Pine", "Quarry", "Raven", "Red", "Ridge", "River", "Rose", "Rush", "Sand",
    "Shore", "Silver", "Spring", "Stone", "Summer", "Sun", "Thorn", "Tide",
    "Vale", "Walnut", "West", "Wheat", "White", "Willow", "Wind", "Wood", "Yew",
    "Abbey", "Amber", "Arbor", "Barrow", "Beacon", "Bell", "Bracken", "Briar",
    "Cairn", "Chapel", "Clover", "Cobble", "Crane", "Dove", "Elder", "Falcon",
    "Fallow", "Foundry", "Gable", "Garland", "Hallow", "Hammer", "Harvest",
    "Heron", "Hollow", "Juniper", "Kestrel", "Lantern", "Linden", "Marble",
    "Market", "Merchant", "Midway", "Nettle", "Osprey", "Otter", "Pebble",
    "Pepper", "Pilgrim", "Plover", "Pryor", "Rowan", "Saddle", "Sable",
    "Sparrow", "Stag", "Sterling", "Swift", "Tanner", "Teal", "Thistle",
    "Timber", "Tinder", "Verge", "Warren", "Weaver", "Whisper", "Winter",
)

_STEM_PLACE_B: tuple[str, ...] = (
    "bank", "bourne", "brook", "burn", "bury", "combe", "croft", "dale", "den",
    "field", "ford", "gate", "grove", "haven", "hill", "holm", "hurst", "ley",
    "mead", "mere", "moor", "mouth", "port", "ridge", "shaw", "side", "stead",
    "stone", "thorpe", "ton", "vale", "view", "ward", "water", "well", "wick",
    "wood", "worth",
    "beck", "berry", "borough", "bridge", "brae", "cliff", "cote", "dean",
    "downs", "fell", "garth", "glen", "green", "hampton", "haugh", "head",
    "heath", "keep", "knowe", "lake", "landing", "meadow", "mill", "park",
    "reach", "ridge", "row", "sands", "slade", "strand", "thwaite", "vane",
    "walk", "way", "weir", "wharf", "yard",
)

#: ~3,200 realistic civil place names, deterministic.
_PLACE_NAMES: tuple[str, ...] = _compose(_STEM_PLACE_A, _STEM_PLACE_B, sep="")


# --------------------------------------------------------------------------- #
#  ORGANISATION pools
# --------------------------------------------------------------------------- #
_ORG_QUALIFIER: tuple[str, ...] = (
    "Allied", "Anchor", "Apex", "Atlas", "Beacon", "Cardinal", "Cascade",
    "Central", "Chartered", "Consolidated", "Continental", "Crescent",
    "Crown", "Delta", "Eastern", "Endeavour", "Everline", "Fidelity",
    "Foundation", "Gateway", "Granite", "Harbour", "Heritage", "Horizon",
    "Imperial", "Integrated", "Keystone", "Landmark", "Legacy", "Liberty",
    "Lighthouse", "Meridian", "Midland", "National", "Northern", "Oakline",
    "Pacific", "Paramount", "Pinnacle", "Pioneer", "Premier", "Provincial",
    "Regent", "Reliance", "Sentinel", "Southern", "Sovereign", "Standard",
    "Sterling", "Summit", "Tidewater", "Trident", "Unified", "Vanguard",
    "Verdant", "Western", "Westfield", "Windward",
    "Accord", "Aldgate", "Ashford", "Auburn", "Bedrock", "Belmont", "Bishop",
    "Blackwell", "Brightstone", "Cambria", "Camden", "Caspian", "Chandler",
    "Clearwater", "Colonial", "Concord", "Covenant", "Dominion", "Eastgate",
    "Elmhurst", "Fairmont", "Fieldstone", "Fulton", "Garrison", "Glenmore",
    "Hartwell", "Hawthorne", "Ironwood", "Kingsbridge", "Lakeshore", "Langley",
    "Mayfair", "Millbrook", "Norwood", "Oakhaven", "Overton", "Parkland",
    "Pembroke", "Quarryhill", "Radcliffe", "Redstone", "Ridgeway", "Rockford",
    "Rosewood", "Saltaire", "Sheffield", "Stonegate", "Thornbury", "Truewind",
    "Whitfield", "Winslow", "Wycombe",
)

_ORG_LOGISTICS_SUFFIX: tuple[str, ...] = (
    "Freight", "Freightways", "Haulage", "Logistics", "Cargo Lines",
    "Distribution", "Transport", "Intermodal", "Supply Chain", "Carriers",
    "Forwarding", "Fulfilment", "Warehousing", "Courier Group",
)

_ORG_AVIATION_SUFFIX: tuple[str, ...] = (
    "Airlines", "Airways", "Air Cargo", "Aviation", "Air Services",
    "Air Freight", "Regional Air", "Air Transport", "Charter Air",
)

_ORG_GRID_SUFFIX: tuple[str, ...] = (
    "Power", "Energy", "Utilities", "Grid Services", "Electric",
    "Power Cooperative", "Energy Networks", "Distribution Networks",
)

_ORG_SHIPPING_SUFFIX: tuple[str, ...] = (
    "Shipping", "Maritime", "Lines", "Marine Services", "Shipping Group",
    "Container Lines", "Marine Logistics", "Port Services",
)

_ORG_GENERIC_SUFFIX: tuple[str, ...] = (
    "Group", "Holdings", "Industries", "Partners", "Corporation", "Systems",
    "Technologies", "Solutions", "Enterprises", "Associates", "Ventures",
    "Consolidated", "Works", "Laboratories",
)

_ORG_AGRI_SUFFIX: tuple[str, ...] = (
    "Agriculture", "Farms", "Agronomy", "Crop Sciences", "Growers",
    "Seed Company", "Harvest Group", "Nutrition", "Agri-Services",
)

_ORG_RETAIL_SUFFIX: tuple[str, ...] = (
    "Retail Group", "Stores", "Markets", "Trading", "Commerce",
    "Merchandising", "Outlets", "Consumer Brands", "Distribution Retail",
)

POOL_ORG_LOGISTICS = _compose(_ORG_QUALIFIER, _ORG_LOGISTICS_SUFFIX)
POOL_ORG_AVIATION = _compose(_ORG_QUALIFIER, _ORG_AVIATION_SUFFIX)
POOL_ORG_GRID = _compose(_ORG_QUALIFIER, _ORG_GRID_SUFFIX)
POOL_ORG_SHIPPING = _compose(_ORG_QUALIFIER, _ORG_SHIPPING_SUFFIX)
POOL_ORG_GENERIC = _compose(_ORG_QUALIFIER, _ORG_GENERIC_SUFFIX)
POOL_ORG_AGRI = _compose(_ORG_QUALIFIER, _ORG_AGRI_SUFFIX)
POOL_ORG_RETAIL = _compose(_ORG_QUALIFIER, _ORG_RETAIL_SUFFIX)


# --------------------------------------------------------------------------- #
#  SITE pools
# --------------------------------------------------------------------------- #
_SITE_LOGISTICS_KIND: tuple[str, ...] = (
    "Depot", "Hub", "Terminal", "Yard", "Crossing", "Distribution Centre",
    "Freight Park", "Transfer Station", "Cross-Dock", "Sorting Centre",
    "Warehouse", "Logistics Park",
)
_SITE_AVIATION_KIND: tuple[str, ...] = (
    "Airport", "Regional Airport", "Airfield", "Air Terminal", "Cargo Terminal",
    "Aerodrome", "Flight Centre", "Maintenance Base",
)
_SITE_GRID_KIND: tuple[str, ...] = (
    "Substation", "Switching Station", "Feeder Station", "Grid Node",
    "Distribution Point", "Transformer Yard", "Control Centre",
)
_SITE_ENERGY_KIND: tuple[str, ...] = (
    "Plant", "Generating Station", "Power Station", "Energy Centre",
    "Turbine Hall", "Fuel Depot", "Cooling Facility",
)
_SITE_PORT_KIND: tuple[str, ...] = (
    "Port", "Harbour", "Quay", "Wharf", "Container Terminal", "Dockyard",
    "Marine Terminal", "Berth Complex",
)
_SITE_AGRI_KIND: tuple[str, ...] = (
    "Farm", "Estate", "Grain Store", "Processing Plant", "Research Station",
    "Greenhouse Complex", "Trial Site", "Silo Park",
)
_SITE_RETAIL_KIND: tuple[str, ...] = (
    "Store", "Retail Park", "Fulfilment Centre", "Showroom", "Outlet",
    "Regional Depot", "Service Point",
)

POOL_SITE_LOGISTICS = _compose(_PLACE_NAMES[:420], _SITE_LOGISTICS_KIND)
POOL_SITE_AVIATION = _compose(_PLACE_NAMES[420:800], _SITE_AVIATION_KIND)
POOL_SITE_GRID = _compose(_SITE_GRID_KIND, _PLACE_NAMES[800:1180])
POOL_SITE_ENERGY = _compose(_PLACE_NAMES[1180:1560], _SITE_ENERGY_KIND)
POOL_SITE_PORT = _compose(_SITE_PORT_KIND, _PLACE_NAMES[1560:1940])
POOL_SITE_AGRI = _compose(_PLACE_NAMES[1940:2320], _SITE_AGRI_KIND)
POOL_SITE_RETAIL = _compose(_PLACE_NAMES[2320:2700], _SITE_RETAIL_KIND)

#: Neutral civil administrative districts.
POOL_PLACE = _compose(
    _PLACE_NAMES[2700:],
    ("District", "County", "Region", "Borough", "Precinct", "Ward", "Zone"),
)


# --------------------------------------------------------------------------- #
#  ROUTE pools
# --------------------------------------------------------------------------- #
_ROUTE_KIND: tuple[str, ...] = (
    "Route", "Corridor", "Lane", "Service Route", "Trunk Route", "Link",
    "Circuit", "Loop", "Line",
)
_ROUTE_NAME: tuple[str, ...] = (
    "Alderline", "Beacon", "Birchway", "Bramble", "Cobblestone", "Copperway",
    "Cornfield", "Crossgate", "Driftwood", "Eastgate", "Elmgate", "Fairway",
    "Fenland", "Flintway", "Foxrun", "Glenway", "Goldleaf", "Granitepath",
    "Hazelford", "Highmoor", "Hollybank", "Ironway", "Ivyway", "Junipark",
    "Kelpline", "Kingsway", "Lanternway", "Larkspur", "Limegrove", "Longmoor",
    "Maplerun", "Marshgate", "Meadowline", "Milestone", "Millrace", "Northgale",
    "Oakpath", "Orchard", "Pathfinder", "Pinewalk", "Quarrygate", "Ravensway",
    "Redgate", "Ridgeline", "Riverbend", "Rosewalk", "Rushford", "Sandway",
    "Shoreline", "Silverpath", "Springline", "Stonemill", "Sunfield",
    "Thornway", "Tidewater", "Umberfield", "Valeway", "Walnutway", "Westford",
    "Wheatline", "Whitegate", "Willowrun", "Windrose", "Woodline", "Yewbridge",
    "Zephyr",
)
POOL_ROUTE = _compose(_ROUTE_KIND, _ROUTE_NAME)


# --------------------------------------------------------------------------- #
#  ASSET pools
# --------------------------------------------------------------------------- #
_MATERIAL_STEM: tuple[str, ...] = (
    "Alpine", "Amber", "Basalt", "Birchwood", "Bronze", "Cedar", "Cinder",
    "Cobalt", "Copper", "Coral", "Cypress", "Dovetail", "Driftwood", "Ember",
    "Flint", "Garnet", "Granite", "Gypsum", "Hearth", "Indigo", "Ironbark",
    "Jade", "Jasper", "Jetstream", "Kindling", "Lantern", "Limestone",
    "Marble", "Mica", "Nickel", "Oakwood", "Obsidian", "Onyx", "Opal",
    "Pewter", "Pumice", "Quartz", "Redwood", "Rivet", "Sable", "Sandstone",
    "Sapphire", "Sequoia", "Shale", "Slate", "Spruce", "Teak", "Timber",
    "Topaz", "Umber", "Vellum", "Wicker", "Willow", "Xenolith", "Yardarm",
    "Zinc",
)

#: Trim/series designators give asset pools a second dimension so that
#: high-cardinality fleet columns never exhaust the pool.
_ASSET_SERIES: tuple[str, ...] = (
    "Mk I", "Mk II", "Mk III", "Mk IV", "Mk V", "Mk VI",
    "Series 100", "Series 200", "Series 300", "Series 400", "Series 500",
    "LR", "SR", "XL", "HD", "Lite", "Pro", "Flex", "Max", "Eco",
)

_AIRFRAME_STEM: tuple[str, ...] = (
    "Arclight", "Altostratus", "Beacon", "Bluefin", "Cirrus", "Contrail",
    "Daybreak", "Everest", "Fairwind", "Glider", "Horizon", "Ionosphere",
    "Jubilee", "Keystone", "Lattice", "Mariner", "Nimbus", "Northwind",
    "Overcast", "Polaris", "Quill", "Rainshadow", "Skyline", "Stratus",
    "Tailwind", "Trailblazer", "Updraft", "Vantage", "Windrose", "Zenith",
    "Aurora", "Clearsky", "Dawnrun", "Eastwind", "Featherlight", "Gustline",
    "Highpass", "Jetsam", "Longhaul", "Meridian",
)

_HAULER_KIND: tuple[str, ...] = (
    "Hauler", "Tractor", "Trailer", "Vanline", "Boxliner", "Flatbed",
    "Reefer", "Tanker-Road", "Curtainer", "Skeletal",
)

#: 56 × 10 × 20 → capped composition keeps pools large but bounded.
POOL_ASSET_HAULER = _compose(_HAULER_KIND, _MATERIAL_STEM, _ASSET_SERIES)
POOL_ASSET_AIRFRAME = _compose(_AIRFRAME_STEM, _ASSET_SERIES)
POOL_ASSET_VESSEL = _merge_pools(
    _compose(("MV",), _PLACE_NAMES[:900]),
    _compose(("MSC", "MT", "SS"), _PLACE_NAMES[900:1800]),
)
#: Grid assets are enumerated per substation zone so the pool scales with
#: real distribution-network cardinality (thousands of metered devices).
_GRID_ZONE: tuple[str, ...] = tuple(f"Z{n:02d}" for n in range(1, 25))

POOL_ASSET_GRID = _merge_pools(
    _compose(("Feeder",), _GRID_ZONE,
             tuple(f"{c}{n}" for c in "ABCDEFGH" for n in range(1, 9)), sep="-"),
    _compose(("Transformer",), _GRID_ZONE, tuple(f"TX{n:02d}" for n in range(1, 41)), sep="-"),
    _compose(("Recloser",), _GRID_ZONE, tuple(f"RC{n:02d}" for n in range(1, 41)), sep="-"),
    _compose(("Capacitor",), _GRID_ZONE, tuple(f"CB{n:02d}" for n in range(1, 31)), sep="-"),
    _compose(("Regulator",), _GRID_ZONE, tuple(f"VR{n:02d}" for n in range(1, 31)), sep="-"),
    _compose(("Inverter",), _GRID_ZONE, tuple(f"INV{n:02d}" for n in range(1, 31)), sep="-"),
    _compose(("Meter",), _GRID_ZONE, tuple(f"MTR{n:03d}" for n in range(1, 61)), sep="-"),
)
POOL_ASSET_GENERIC = _compose(
    ("Unit", "Asset", "Module", "Rig", "Kit", "Node", "Array", "Bay"),
    _MATERIAL_STEM,
    _ASSET_SERIES,
)


# --------------------------------------------------------------------------- #
#  PERSON pool (neutral surrogates, globally plausible, never real figures)
# --------------------------------------------------------------------------- #
_GIVEN_INITIAL: tuple[str, ...] = tuple(f"{c}." for c in "ABCDEFGHIJKLMNOPRSTVWZ")

_FAMILY_NAME: tuple[str, ...] = (
    "Achebe", "Aldridge", "Almeida", "Andersen", "Ashworth", "Baptiste",
    "Beaumont", "Belanger", "Bramley", "Brightwell", "Calloway", "Cardoso",
    "Castellano", "Chandra", "Corrigan", "Dalgaard", "Delacroix", "Duvall",
    "Eklund", "Ellingham", "Fairbairn", "Ferreira", "Ferris", "Gallagher",
    "Hallstrom", "Halloran", "Hirsch", "Ingersoll", "Iqbal", "Kalinski",
    "Kavanagh", "Kirchner", "Kostas", "Larsson", "Lindqvist", "Marchetti",
    "Marlowe", "Mbeki", "Moreau", "Nakamura", "Navarro", "Nazario", "Okonkwo",
    "Ostrander", "Oyelaran", "Pereira", "Petrossian", "Ravenscroft", "Rhodes",
    "Sandhu", "Sandoval", "Sorensen", "Sunderland", "Thorsen", "Vasquez",
    "Whitcombe", "Yusupova", "Zieliński", "Fenwick", "Kowalczyk", "Moreno",
    "Ndiaye", "Olsen", "Rahman", "Silva", "Tanaka", "Ueda", "Valenti",
    "Weatherby", "Yildiz",
    "Abadi", "Adeyemi", "Aguilar", "Ahmadi", "Alvarsson", "Amrani", "Ansari",
    "Arnesen", "Bacchus", "Bergqvist", "Bhattacharya", "Bianchi", "Bjornstad",
    "Boateng", "Bonnet", "Brennan", "Cabrera", "Caldwell", "Chaudhry", "Cheng",
    "Cisneros", "Dabrowski", "Dagnall", "Demir", "Descoteaux", "Dimitrova",
    "Dubois", "Eriksen", "Escalante", "Fabron", "Farrugia", "Fontaine",
    "Gasparyan", "Goswami", "Grimaldi", "Haddad", "Hagen", "Hartmann",
    "Holloway", "Ibrahimovic", "Ivanova", "Jankowski", "Jimenez", "Kaczmarek",
    "Kandel", "Karlsen", "Keita", "Khoury", "Kimura", "Kolarov", "Laurent",
    "Leclerc", "Lindstrom", "Maalouf", "Magnusson", "Mancini", "Mbala",
    "Mehdi", "Mensah", "Mikkelsen", "Montoya", "Mwangi", "Nakagawa",
    "Nilsson", "Novotny", "Oyelowo", "Pappas", "Pedersen", "Quintero",
    "Rasmussen", "Reyes", "Rosenthal", "Salazar", "Sarkisian", "Schneider",
    "Sokolov", "Stavros", "Suzuki", "Tremblay", "Vargas", "Virtanen",
    "Wojcik", "Yamamoto", "Zaman", "Zhao",
)
POOL_PERSON = _compose(_GIVEN_INITIAL, _FAMILY_NAME)


# --------------------------------------------------------------------------- #
#  PROJECT / PROGRAMME pools
# --------------------------------------------------------------------------- #
_PROJECT_KIND: tuple[str, ...] = ("Project", "Programme", "Initiative", "Workstream")
_PROJECT_NAME: tuple[str, ...] = (
    "Almanac", "Beltline", "Blueprint", "Cornerstone", "Clearview", "Compass",
    "Daybook", "Driftline", "Evenkeel", "Evergreen", "Foldout", "Foundry",
    "Gatepost", "Greenfield", "Halyard", "Hearthstone", "Inkwell", "Ironclad",
    "Juniper", "Keystone", "Ledger", "Lighthouse", "Longboat", "Manifest",
    "Meridian", "Milestone", "Nightshift", "Northstar", "Openfield", "Overland",
    "Palletwise", "Pinewood", "Quarry", "Quayside", "Redwood", "Roundtrip",
    "Shelfline", "Skyline", "Tailgate", "Trellis", "Umbrella", "Unitload",
    "Vantage", "Viaduct", "Waybill", "Waypoint", "Yardstick", "Yardline",
    "Zoning", "Anvil", "Beacon", "Cartwheel", "Dovetail", "Elmgate",
    "Aperture", "Ballast", "Benchmark", "Bookend", "Brickwork", "Canopy",
    "Capstone", "Cascade", "Clearing", "Cobbler", "Crosswalk", "Dockside",
    "Drawbridge", "Eastline", "Fieldnote", "Flagstone", "Footbridge",
    "Gridiron", "Handrail", "Harbourlight", "Headwater", "Innkeeper",
    "Jetty", "Kiln", "Landmark", "Lattice", "Lockstep", "Loftline",
    "Masthead", "Millstone", "Mooring", "Northfield", "Outrigger", "Pathway",
    "Pierhead", "Quarrystone", "Rampart", "Ridgeline", "Rooftop", "Sandbar",
    "Shorewall", "Signpost", "Slipway", "Stonework", "Tollgate", "Towpath",
    "Trackbed", "Turnstile", "Watermark", "Waypost", "Wharfside", "Woodshed",
)
POOL_PROJECT = _compose(_PROJECT_KIND, _PROJECT_NAME)


# --------------------------------------------------------------------------- #
#  HANDLING TIER / STATUS / CATEGORY pools
# --------------------------------------------------------------------------- #
_TIER_LABEL: tuple[str, ...] = (
    "PUBLIC", "INTERNAL", "RESTRICTED", "CONTROLLED", "PRIVILEGED",
    "SEALED", "ESCROW", "ARCHIVE", "CUSTODIAL", "EMBARGOED",
    "REGULATED", "PROTECTED", "LIMITED", "RESERVED", "SUPERVISED",
    "ATTESTED", "WITNESSED", "NOTARISED", "QUARANTINED", "RETAINED",
)
_TIER_SCOPE: tuple[str, ...] = (
    "", "/COMMERCIAL", "/PARTNER", "/AUDIT", "/RETENTION", "/EXPORT",
)
POOL_HANDLING_TIER: tuple[str, ...] = tuple(
    f"TIER-{i} {label}{scope}"
    for scope in _TIER_SCOPE
    for i, label in enumerate(_TIER_LABEL, start=1)
)

_NATO_WORD: tuple[str, ...] = (
    "ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL",
    "INDIA", "JULIET", "KILO", "LIMA", "MIKE", "NOVEMBER", "OSCAR", "PAPA",
    "QUEBEC", "ROMEO", "SIERRA", "TANGO", "UNIFORM", "VICTOR", "WHISKEY",
    "XRAY", "YANKEE", "ZULU",
)
POOL_STATUS = _compose(
    ("STATE", "PHASE", "STAGE", "MODE", "STEP", "CYCLE"),
    _NATO_WORD,
    ("", "0", "1", "2", "3"),
    sep="-",
)

_COLOUR_WORD: tuple[str, ...] = (
    "Ashen", "Amber", "Bramble", "Cobalt", "Copper", "Crimson", "Dunlin",
    "Elmwood", "Ferrite", "Gossamer", "Halcyon", "Indigo", "Jasper", "Kelvin",
    "Lichen", "Mulberry", "Nutmeg", "Ochre", "Onyx", "Pewter", "Quince",
    "Russet", "Saffron", "Sorrel", "Teal", "Umber", "Verdigris", "Wheaten",
    "Xanthic", "Yarrow", "Zephyr",
    "Alabaster", "Almond", "Basalt", "Bistre", "Bronze", "Burgundy", "Celadon",
    "Cerulean", "Chartreuse", "Cinnabar", "Claret", "Ebony", "Fawn", "Flaxen",
    "Garnet", "Glaucous", "Heather", "Ivory", "Juniper", "Khaki", "Lavender",
    "Magenta", "Mahogany", "Marigold", "Mauve", "Moss", "Oatmeal", "Olive",
    "Pearl", "Periwinkle", "Porcelain", "Rosewood", "Sage", "Sandstone",
    "Sepia", "Slate", "Taupe", "Terracotta", "Thistle", "Vermilion", "Walnut",
)
POOL_CATEGORY = _compose(
    ("Category", "Class", "Band", "Segment", "Grade", "Tier", "Group",
     "Division", "Cohort", "Bracket"),
    _COLOUR_WORD,
    ("", "I", "II", "III", "IV", "V"),
)


# --------------------------------------------------------------------------- #
#  Domain-specific pools for the two NEW cover domains
# --------------------------------------------------------------------------- #
POOL_ASSET_AGRI = _compose(
    ("Cultivar", "Varietal", "Strain-Line", "Hybrid", "Rootstock"),
    ("Amberwheat", "Blueharvest", "Coppergrain", "Dawnbarley", "Eastfield",
     "Fieldgold", "Greenspike", "Harvestmoon", "Ironroot", "Jadeleaf",
     "Kernelrich", "Longstalk", "Meadowgold", "Northgrain", "Oatcrest",
     "Prairiegold", "Quickgrow", "Redhusk", "Sunstalk", "Tallgrain",
     "Umberseed", "Valleycrop", "Wheatcrown", "Yieldmax"),
    _ASSET_SERIES,
)
POOL_ASSET_RETAIL = _compose(
    ("SKU-Line", "Product-Line", "Range", "Assortment", "Collection"),
    ("Everyday", "Premium", "Essentials", "Signature", "Classic", "Select",
     "Value", "Heritage", "Modern", "Fresh", "Core", "Seasonal", "Artisan",
     "Standard", "Deluxe", "Basics"),
    _ASSET_SERIES,
)



# --- pools for the space / earth-observation cover domain ------------------
_ORG_EO_SUFFIX: tuple[str, ...] = (
    "Earth Imaging", "Geospatial", "Earth Observation", "Imaging Services",
    "Remote Sensing", "Mapping Group", "Survey Systems", "Orbital Imaging",
    "Geo Analytics",
)
_SITE_EO_KIND: tuple[str, ...] = (
    "Ground Station", "Downlink Facility", "Operations Centre", "Antenna Park",
    "Processing Centre", "Archive Facility", "Calibration Site", "Teleport",
)
POOL_ORG_EO = _compose(_ORG_QUALIFIER, _ORG_EO_SUFFIX)
POOL_SITE_EO = _compose(_PLACE_NAMES[2700:3100], _SITE_EO_KIND)
POOL_ASSET_EO = _merge_pools(
    _compose(("Sat",), tuple(f"{c}{n:02d}" for c in "ABCDEFGH" for n in range(1, 13)), sep="-"),
    _compose(("Platform",), _MATERIAL_STEM, _ASSET_SERIES),
    _compose(("Sensor",), tuple(f"OPT{n:02d}" for n in range(1, 41)), sep="-"),
    _compose(("Sensor",), tuple(f"SAR{n:02d}" for n in range(1, 41)), sep="-"),
)

# --- pools for the facilities-management cover domain ----------------------
_ORG_FM_SUFFIX: tuple[str, ...] = (
    "Facilities", "Estates", "Property Services", "Site Services",
    "Building Management", "Estate Management", "Maintenance Group",
    "Infrastructure Services",
)
_SITE_FM_KIND: tuple[str, ...] = (
    "Campus", "Facility", "Building", "Site", "Works", "Complex",
    "Service Centre", "Plant Room", "Annexe", "Compound",
)
POOL_ORG_FM = _compose(_ORG_QUALIFIER, _ORG_FM_SUFFIX)
POOL_SITE_FM = _compose(_PLACE_NAMES[3100:3500], _SITE_FM_KIND)
POOL_ASSET_FM = _merge_pools(
    _compose(("Plant",), _MATERIAL_STEM, _ASSET_SERIES),
    _compose(("HVAC",), tuple(f"AHU{n:02d}" for n in range(1, 41)), sep="-"),
    _compose(("Pump",), tuple(f"P{n:03d}" for n in range(1, 61)), sep="-"),
    _compose(("Panel",), tuple(f"DB{n:02d}" for n in range(1, 41)), sep="-"),
)

# --------------------------------------------------------------------------- #
#  EXPANDED POOL REGISTRY
# --------------------------------------------------------------------------- #
#: Per-cover-domain pool overrides merged into the ontology profiles.
EXPANDED_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "defense_to_logistics": {
        "ORG": POOL_ORG_LOGISTICS,
        "SITE": POOL_SITE_LOGISTICS,
        "ROUTE": POOL_ROUTE,
        "ASSET": POOL_ASSET_HAULER,
        "PROJECT": POOL_PROJECT,
        "PERSON": POOL_PERSON,
        "PLACE": POOL_PLACE,
        "HANDLING_TIER": POOL_HANDLING_TIER,
        "STATUS": POOL_STATUS,
        "GENERIC": POOL_CATEGORY,
    },
    "aerospace_to_civil_aviation": {
        "ORG": POOL_ORG_AVIATION,
        "SITE": POOL_SITE_AVIATION,
        "ROUTE": POOL_ROUTE,
        "ASSET": POOL_ASSET_AIRFRAME,
        "PROJECT": POOL_PROJECT,
        "PERSON": POOL_PERSON,
        "PLACE": POOL_PLACE,
        "HANDLING_TIER": POOL_HANDLING_TIER,
        "STATUS": POOL_STATUS,
        "GENERIC": POOL_CATEGORY,
    },
    "cyberwar_to_smartgrid": {
        "ORG": POOL_ORG_GRID,
        "SITE": POOL_SITE_GRID,
        "ROUTE": POOL_ROUTE,
        "ASSET": POOL_ASSET_GRID,
        "PROJECT": POOL_PROJECT,
        "PERSON": POOL_PERSON,
        "PLACE": POOL_PLACE,
        "HANDLING_TIER": POOL_HANDLING_TIER,
        "STATUS": POOL_STATUS,
        "GENERIC": POOL_CATEGORY,
    },
    "nuclear_to_civil_energy": {
        "ORG": POOL_ORG_GRID,
        "SITE": POOL_SITE_ENERGY,
        "ROUTE": POOL_ROUTE,
        "ASSET": POOL_ASSET_GRID,
        "PROJECT": POOL_PROJECT,
        "PERSON": POOL_PERSON,
        "PLACE": POOL_PLACE,
        "HANDLING_TIER": POOL_HANDLING_TIER,
        "STATUS": POOL_STATUS,
        "GENERIC": POOL_CATEGORY,
    },
    "naval_to_commercial_shipping": {
        "ORG": POOL_ORG_SHIPPING,
        "SITE": POOL_SITE_PORT,
        "ROUTE": POOL_ROUTE,
        "ASSET": POOL_ASSET_VESSEL,
        "PROJECT": POOL_PROJECT,
        "PERSON": POOL_PERSON,
        "PLACE": POOL_PLACE,
        "HANDLING_TIER": POOL_HANDLING_TIER,
        "STATUS": POOL_STATUS,
        "GENERIC": POOL_CATEGORY,
    },
    "generic_pii_redaction": {
        "ORG": POOL_ORG_GENERIC,
        "SITE": POOL_SITE_RETAIL,
        "ROUTE": POOL_ROUTE,
        "ASSET": POOL_ASSET_GENERIC,
        "PROJECT": POOL_PROJECT,
        "PERSON": POOL_PERSON,
        "PLACE": POOL_PLACE,
        "HANDLING_TIER": POOL_HANDLING_TIER,
        "STATUS": POOL_STATUS,
        "GENERIC": POOL_CATEGORY,
    },
}


# --------------------------------------------------------------------------- #
#  ADDITIONAL TOKEN SHIFT MATRICES  (two new cover domains)
# --------------------------------------------------------------------------- #

#: Biomedical / CBRN defence  ->  commercial agriculture & crop science
_SHIFT_BIODEFENCE_TO_AGRI: dict[str, str] = {
    "pathogen_strain": "cultivar_line",
    "pathogen": "cultivar",
    "biological_agent": "crop_input",
    "bioweapon": "crop_treatment",
    "select_agent": "regulated_input",
    "virulence_factor": "vigour_factor",
    "virulence": "vigour",
    "infectivity": "germination_rate",
    "transmissibility": "spread_rate",
    "incubation_period": "growth_period",
    "lethal_dose": "application_dose",
    "ld50": "ed50",
    "toxin_yield": "extract_yield",
    "toxin": "extract",
    "aerosolization": "dispersal",
    "dispersal_pattern": "dispersal_pattern",
    "contamination_zone": "treatment_zone",
    "contamination": "residue",
    "decontamination": "cleaning",
    "quarantine_zone": "containment_block",
    "quarantine": "containment",
    "outbreak": "incidence_event",
    "casualty_estimate": "loss_estimate",
    "exposure_route": "uptake_route",
    "biosafety_level": "containment_grade",
    "bsl4": "grade_four",
    "bsl3": "grade_three",
    "containment_breach": "seal_failure",
    "vaccine_stockpile": "treatment_inventory",
    "vaccine": "treatment",
    "prophylaxis": "preventive_care",
    "antidote": "corrective_input",
    "chemical_agent": "soil_agent",
    "nerve_agent": "growth_regulator",
    "blister_agent": "surface_agent",
    "precursor_chemical": "feedstock_chemical",
    "precursor": "feedstock",
    "synthesis_route": "production_route",
    "weaponization": "formulation",
    "delivery_system": "application_system",
    "detection_threshold": "detection_threshold",
    "assay_result": "assay_result",
    "sample_custody": "sample_custody",
    "clinical_trial": "field_trial",
    "patient_id": "plot_id",
    "subject_id": "specimen_id",
    "genome_sequence": "genome_sequence",
    "gene_edit": "trait_edit",
    "laboratory": "research_station",
    "researcher": "agronomist",
    "principal_investigator": "lead_agronomist",
}

#: Financial intelligence / sanctions  ->  retail commerce analytics
_SHIFT_FININT_TO_RETAIL: dict[str, str] = {
    "sanctioned_entity": "restricted_supplier",
    "sanctions_list": "restricted_list",
    "sanction": "restriction",
    "designated_person": "flagged_account",
    "watchlist": "review_list",
    "beneficial_owner": "account_principal",
    "shell_company": "holding_entity",
    "front_company": "intermediary_entity",
    "money_laundering": "irregular_settlement",
    "laundering": "irregular_settlement",
    "terrorist_financing": "prohibited_funding",
    "illicit_finance": "irregular_finance",
    "illicit": "irregular",
    "suspicious_transaction": "flagged_transaction",
    "suspicious_activity": "flagged_activity",
    "sar_filing": "review_filing",
    "typology": "pattern_class",
    "predicate_offence": "policy_breach",
    "asset_freeze": "account_hold",
    "seizure": "hold_action",
    "forfeiture": "write_off",
    "correspondent_bank": "partner_institution",
    "wire_transfer": "settlement_transfer",
    "layering": "routing_stage",
    "placement": "entry_stage",
    "integration": "settlement_stage",
    "smurfing": "split_deposits",
    "structuring": "split_transactions",
    "high_risk_jurisdiction": "tier_three_market",
    "jurisdiction": "market",
    "offshore_account": "external_account",
    "tax_haven": "low_duty_market",
    "kyc_status": "verification_status",
    "cdd_level": "diligence_level",
    "pep_status": "priority_status",
    "politically_exposed": "priority_customer",
    "adverse_media": "public_signal",
    "risk_rating": "risk_rating",
    "transaction_monitoring": "transaction_monitoring",
    "investigator": "analyst",
    "case_officer": "case_manager",
    "informant_payment": "referral_payment",
    "undercover_account": "test_account",
    "intercepted_transfer": "held_transfer",
    "source_of_funds": "source_of_funds",
    "cryptocurrency_wallet": "digital_wallet",
    "mixer_service": "aggregation_service",
    "darknet_market": "unlisted_marketplace",
}


#: Space / satellite reconnaissance  ->  commercial earth-observation services
_SHIFT_SPACE_TO_EO: dict[str, str] = {
    "satellite_tasking": "acquisition_request",
    "tasking_order": "acquisition_order",
    "collection_deck": "capture_schedule",
    "collection_requirement": "capture_requirement",
    "reconnaissance_pass": "survey_pass",
    "recon_pass": "survey_pass",
    "overhead_asset": "survey_platform",
    "national_asset": "commercial_platform",
    "orbital_element": "orbital_element",
    "tle_set": "ephemeris_set",
    "revisit_rate": "revisit_rate",
    "nadir_pass": "nadir_pass",
    "ground_sample_distance": "ground_sample_distance",
    "imagery_intelligence": "earth_observation",
    "imint": "eo_analytics",
    "sigint_payload": "rf_payload",
    "target_deck": "site_list",
    "target_folder": "site_folder",
    "denied_area": "restricted_airspace",
    "exploitation_report": "analysis_report",
    "first_phase_report": "preliminary_report",
    "bomb_damage_assessment": "change_assessment",
    "battle_damage_assessment": "change_detection",
    "change_detection": "change_detection",
    "classified_imagery": "licensed_imagery",
    "downlink_station": "ground_station",
    "ground_segment": "ground_segment",
    "crypto_key_load": "session_key_load",
    "covert_payload": "secondary_payload",
    "constellation": "constellation",
    "dwell_time": "dwell_time",
    "slew_rate": "slew_rate",
    "cloud_cover": "cloud_cover",
    "resolution_class": "resolution_class",
    "analyst_notes": "analyst_notes",
    "priority_intelligence_requirement": "priority_service_request",
    "warning_order": "advisory_notice",
    "mission_planner": "capture_planner",
    "orbit_adjust": "orbit_adjust",
    "sensor_mode": "sensor_mode",
}

#: Critical national infrastructure protection  ->  facilities management
_SHIFT_CNI_TO_FACILITIES: dict[str, str] = {
    "critical_infrastructure": "priority_estate",
    "critical_national_infrastructure": "priority_estate",
    "vulnerability_assessment": "condition_survey",
    "threat_assessment": "risk_survey",
    "attack_surface": "exposure_surface",
    "attack_vector": "failure_pathway",
    "single_point_of_failure": "single_point_of_failure",
    "cascading_failure": "cascading_outage",
    "blast_radius": "impact_radius",
    "hardening_measure": "resilience_measure",
    "perimeter_security": "perimeter_control",
    "intrusion_detection": "access_monitoring",
    "guard_force": "site_team",
    "access_control_list": "access_roster",
    "clearance_level": "access_tier",
    "restricted_zone": "controlled_area",
    "exclusion_zone": "closed_area",
    "standoff_distance": "setback_distance",
    "chokepoint": "bottleneck",
    "redundancy_path": "backup_path",
    "failover_site": "alternate_site",
    "continuity_of_operations": "business_continuity",
    "emergency_action_plan": "emergency_plan",
    "incident_commander": "duty_manager",
    "response_time": "response_time",
    "sabotage": "tampering",
    "insider_threat": "internal_risk",
    "security_incident": "site_incident",
    "surveillance_log": "monitoring_log",
    "patrol_route": "inspection_round",
    "asset_criticality": "asset_priority",
    "mission_essential": "service_essential",
    "denial_of_service": "service_interruption",
    "physical_breach": "access_breach",
    "countermeasure": "mitigation",
    "red_team": "review_team",
    "penetration_test": "assurance_test",
    "site_survey": "site_survey",
    "maintenance_window": "maintenance_window",
}

EXTRA_TOKEN_SHIFTS: dict[str, dict[str, str]] = {
    "biodefence_to_agriculture": _SHIFT_BIODEFENCE_TO_AGRI,
    "finint_to_retail_analytics": _SHIFT_FININT_TO_RETAIL,
    "space_recon_to_earth_observation": _SHIFT_SPACE_TO_EO,
    "cni_to_facilities_management": _SHIFT_CNI_TO_FACILITIES,
}


# --------------------------------------------------------------------------- #
#  NEW DOMAIN PROFILE SPECIFICATIONS
# --------------------------------------------------------------------------- #
#: Consumed by core.ontology to register additional DomainProfile objects.
EXTRA_PROFILE_SPECS: list[dict[str, object]] = [
    {
        "key": "biodefence_to_agriculture",
        "title": "Biodefence / CBRN → Commercial Agriculture",
        "source_domain": "Biological and chemical defence research, select agents",
        "cover_domain": "Commercial crop science, agronomy trials and field operations",
        "description": (
            "Projects biodefence and CBRN research vocabulary (pathogens, "
            "toxins, containment grades, exposure routes) into commercial crop "
            "science: cultivars, treatments, field trials and containment blocks."
        ),
        "token_shifts": _SHIFT_BIODEFENCE_TO_AGRI,
        "pools": {
            "ORG": POOL_ORG_AGRI,
            "SITE": POOL_SITE_AGRI,
            "ROUTE": POOL_ROUTE,
            "ASSET": POOL_ASSET_AGRI,
            "PROJECT": POOL_PROJECT,
            "PERSON": POOL_PERSON,
            "PLACE": POOL_PLACE,
            "HANDLING_TIER": POOL_HANDLING_TIER,
            "STATUS": POOL_STATUS,
            "GENERIC": POOL_CATEGORY,
        },
    },
    {
        "key": "space_recon_to_earth_observation",
        "title": "Space Reconnaissance → Commercial Earth Observation",
        "source_domain": "Overhead collection, satellite tasking, imagery intelligence",
        "cover_domain": "Commercial earth-observation and geospatial analytics services",
        "description": (
            "Projects overhead-collection tradecraft (tasking orders, collection "
            "decks, exploitation reports, denied areas) into commercial "
            "earth-observation: acquisition requests, capture schedules and "
            "change-detection analytics."
        ),
        "token_shifts": _SHIFT_SPACE_TO_EO,
        "pools": {
            "ORG": POOL_ORG_EO,
            "SITE": POOL_SITE_EO,
            "ROUTE": POOL_ROUTE,
            "ASSET": POOL_ASSET_EO,
            "PROJECT": POOL_PROJECT,
            "PERSON": POOL_PERSON,
            "PLACE": POOL_PLACE,
            "HANDLING_TIER": POOL_HANDLING_TIER,
            "STATUS": POOL_STATUS,
            "GENERIC": POOL_CATEGORY,
        },
    },
    {
        "key": "cni_to_facilities_management",
        "title": "Critical Infrastructure Protection → Facilities Management",
        "source_domain": "CNI protection, vulnerability and threat assessment",
        "cover_domain": "Corporate facilities and estate management",
        "description": (
            "Projects critical-infrastructure protection vocabulary "
            "(attack surfaces, exclusion zones, insider threat, hardening) into "
            "routine facilities management: condition surveys, controlled areas "
            "and planned maintenance."
        ),
        "token_shifts": _SHIFT_CNI_TO_FACILITIES,
        "pools": {
            "ORG": POOL_ORG_FM,
            "SITE": POOL_SITE_FM,
            "ROUTE": POOL_ROUTE,
            "ASSET": POOL_ASSET_FM,
            "PROJECT": POOL_PROJECT,
            "PERSON": POOL_PERSON,
            "PLACE": POOL_PLACE,
            "HANDLING_TIER": POOL_HANDLING_TIER,
            "STATUS": POOL_STATUS,
            "GENERIC": POOL_CATEGORY,
        },
    },
    {
        "key": "finint_to_retail_analytics",
        "title": "Financial Intelligence / Sanctions → Retail Analytics",
        "source_domain": "Financial intelligence, sanctions enforcement, AML casework",
        "cover_domain": "Retail commerce analytics, supplier risk and settlement flows",
        "description": (
            "Projects sanctions-enforcement and AML casework vocabulary "
            "(designated persons, laundering typologies, asset freezes) into "
            "benign retail analytics: supplier reviews, flagged settlements and "
            "customer verification tiers."
        ),
        "token_shifts": _SHIFT_FININT_TO_RETAIL,
        "pools": {
            "ORG": POOL_ORG_RETAIL,
            "SITE": POOL_SITE_RETAIL,
            "ROUTE": POOL_ROUTE,
            "ASSET": POOL_ASSET_RETAIL,
            "PROJECT": POOL_PROJECT,
            "PERSON": POOL_PERSON,
            "PLACE": POOL_PLACE,
            "HANDLING_TIER": POOL_HANDLING_TIER,
            "STATUS": POOL_STATUS,
            "GENERIC": POOL_CATEGORY,
        },
    },
]


# --------------------------------------------------------------------------- #
#  ADDITIONAL SENSITIVITY RULES
# --------------------------------------------------------------------------- #
EXTRA_SENSITIVITY_RULES: list[dict[str, object]] = [
    {
        "id": "BIOLOGICAL_AGENT",
        "severity": 5,
        "target": "both",
        "category": "cbrn",
        "pattern": r"\b(pathogen|select[_\s-]?agent|bioweapon|biological[_\s-]?agent|"
                   r"anthrax|botulinum|ricin|tularemia|variola|filovirus|"
                   r"bsl[\s-]?[34]|biosafety[_\s-]?level|virulence|ld50)\b",
        "explain": "Biological agent or biosafety containment reference.",
    },
    {
        "id": "CHEMICAL_AGENT",
        "severity": 5,
        "target": "both",
        "category": "cbrn",
        "pattern": r"\b(nerve[_\s-]?agent|blister[_\s-]?agent|sarin|soman|tabun|"
                   r"vx[_\s-]?agent|mustard[_\s-]?gas|chemical[_\s-]?weapon|"
                   r"precursor[_\s-]?chemical|cwc[_\s-]?schedule)\b",
        "explain": "Chemical warfare agent or precursor reference.",
    },
    {
        "id": "NUCLEAR_MATERIAL",
        "severity": 5,
        "target": "both",
        "category": "cbrn",
        "pattern": r"\b(fissile|enrichment|centrifuge|weapons[_\s-]?grade|"
                   r"plutonium|uranium[\s-]?23[58]|hEU|warhead[_\s-]?yield|"
                   r"kiloton|megaton|criticality)\b",
        "explain": "Nuclear material or weapons-physics reference.",
    },
    {
        "id": "SANCTIONS_ENTITY",
        "severity": 5,
        "target": "both",
        "category": "financial_intel",
        "pattern": r"\b(ofac|sdn[_\s-]?list|sanction(ed|s)?|designated[_\s-]?person|"
                   r"asset[_\s-]?freeze|watchlist|embargo|denied[_\s-]?party)\b",
        "explain": "Sanctions enforcement or denied-party reference.",
    },
    {
        "id": "AML_TYPOLOGY",
        "severity": 4,
        "target": "both",
        "category": "financial_intel",
        "pattern": r"\b(money[_\s-]?laundering|terrorist[_\s-]?financing|"
                   r"suspicious[_\s-]?(activity|transaction)|sar[_\s-]?filing|"
                   r"structuring|smurfing|beneficial[_\s-]?owner|shell[_\s-]?company|"
                   r"politically[_\s-]?exposed|\bpep\b|kyc|aml)\b",
        "explain": "Anti-money-laundering casework or typology reference.",
    },
    {
        "id": "CRYPTO_WALLET",
        "severity": 4,
        "target": "value",
        "category": "financial_intel",
        "pattern": r"\b(bc1[a-z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b",
        "explain": "Cryptocurrency wallet address.",
    },
    {
        "id": "IBAN_ACCOUNT",
        "severity": 4,
        "target": "value",
        "category": "pii",
        "pattern": r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
        "explain": "IBAN-format bank account identifier.",
    },
    {
        "id": "CREDIT_CARD_PAN",
        "severity": 5,
        "target": "value",
        "category": "pii",
        "pattern": r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6(?:011|5\d{2})\d{12})\b",
        "explain": "Payment card primary account number (PAN).",
    },
    {
        "id": "MEDICAL_IDENTIFIER",
        "severity": 5,
        "target": "both",
        "category": "phi",
        "pattern": r"\b(patient[_\s-]?id|mrn|medical[_\s-]?record[_\s-]?number|nhs[_\s-]?number|"
                   r"icd[\s-]?10|diagnosis[_\s-]?code|treatment[_\s-]?plan|prescription)\b",
        "explain": "Protected health information identifier.",
    },
    {
        "id": "BIOMETRIC_TEMPLATE",
        "severity": 5,
        "target": "both",
        "category": "pii",
        "pattern": r"\b(biometric|fingerprint|iris[_\s-]?scan|facial[_\s-]?template|"
                   r"retina|voiceprint|dna[_\s-]?profile|gait[_\s-]?signature)\b",
        "explain": "Biometric template or identifier (irrevocable if disclosed).",
    },
    {
        "id": "SOURCE_CODE_SECRET",
        "severity": 4,
        "target": "value",
        "category": "credential",
        "pattern": r"\b(AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9]{20,}|"
                   r"xox[baprs]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b",
        "explain": "Embedded API key, access token or JWT.",
    },
    {
        "id": "SATELLITE_TASKING",
        "severity": 5,
        "target": "both",
        "category": "geospatial",
        "pattern": r"\b(nro|satellite[_\s-]?tasking|orbital[_\s-]?element|tle[_\s-]?set|"
                   r"collection[_\s-]?deck|imagery[_\s-]?request|nadir[_\s-]?pass|"
                   r"revisit[_\s-]?rate|ground[_\s-]?sample[_\s-]?distance)\b",
        "explain": "Overhead collection tasking or orbital parameter.",
    },
    {
        "id": "SUPPLY_CHAIN_CRITICAL",
        "severity": 3,
        "target": "both",
        "category": "proprietary",
        "pattern": r"\b(single[_\s-]?source|sole[_\s-]?source|critical[_\s-]?supplier|"
                   r"bill[_\s-]?of[_\s-]?materials|bom[_\s-]?revision|tooling[_\s-]?spec|"
                   r"yield[_\s-]?rate|process[_\s-]?recipe)\b",
        "explain": "Critical supply-chain or manufacturing process detail.",
    },
    {
        "id": "LEGAL_PRIVILEGE",
        "severity": 4,
        "target": "both",
        "category": "legal",
        "pattern": r"\b(attorney[\s-]?client|legal[_\s-]?privilege|privileged[_\s-]?"
                   r"communication|work[_\s-]?product|under[_\s-]?seal|"
                   r"protective[_\s-]?order|in[_\s-]?camera)\b",
        "explain": "Legally privileged or sealed material.",
    },
]


# --------------------------------------------------------------------------- #
#  Diagnostics
# --------------------------------------------------------------------------- #
def pool_statistics() -> dict[str, object]:
    """Report pool sizes for the attestation / capability UI."""
    per_domain: dict[str, dict[str, int]] = {}
    unique: set[str] = set()
    for domain, pools in EXPANDED_POOLS.items():
        per_domain[domain] = {name: len(vals) for name, vals in pools.items()}
        for vals in pools.values():
            unique.update(vals)
    for spec in EXTRA_PROFILE_SPECS:
        pools = spec["pools"]  # type: ignore[index]
        per_domain[str(spec["key"])] = {n: len(v) for n, v in pools.items()}  # type: ignore[union-attr]
        for v in pools.values():  # type: ignore[union-attr]
            unique.update(v)
    return {
        "per_domain": per_domain,
        "total_unique_surrogates": len(unique),
        "extra_token_shift_rules": sum(len(v) for v in EXTRA_TOKEN_SHIFTS.values()),
        "extra_sensitivity_rules": len(EXTRA_SENSITIVITY_RULES),
        "place_name_stems": len(_PLACE_NAMES),
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    print(json.dumps(pool_statistics(), indent=2))
