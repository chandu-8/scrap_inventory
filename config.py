# --- Constants ---
CUTTING_ALLOWANCE = 20  # mm
FRAME_CUTTING_ALLOWANCE = 50
NEW_PROFILE_LENGTH = 6000  # mm
MIN_SCRAP_LENGTH = 1000  # mm - minimum length to keep as scrap

PROFILE_MAP = {
    "K11I001007": "P.C.E. PROFILE LAD F-75",
    "K11I001032": "BOX TYPE SAND TRAP BLADE PROFILE",
    "K11I001009": "FRAME PROFILE FOR LAD F-75",
    "K11I001014": "PCE PROFILE LAD F-100",
    "K11I001034": "BOX TYPE LOUVER BLADE PROFILE",
    "K11I002007": "INNERVANE PROFILE LAD F-100",
    "K11I001033": "BOX TYPE SAND TRAP FRAME PROFILE",
    "K11I008007": "FRAME PROFILE XDG",
    "K15I011002": "FRAME PROFILE FOR OBD - BLACK ANODISED",
    "K11I007008": "LBG (AIR LINE) BLADE 0°",
    "K11L001007": "MOVEMENT BAR PROFILE - BLACK ANODISED",
    "K11I008008": "BLADE PROFILE XDG",
    "K11L001001": "LBG 15 DEG BLADE PROFILE",
    "K11I001035": "BOX TYPE LOUVER FRAME PROFILE",
    "K11I001015": "VCD PROFILE LAD F-100",
    "K15I011001": "BLADE PROFILE FOR OBD - BLACK ANODISED",
    "K11I113007": "FLY SCREEN FRAME",
    "K11I007009": "FRAME PROFILE LBG",
    "K11I005003": "I BEAM BAR - AIRLINE",
    "K11L001008": "ENDCAP PROFILE",
    "K11I001031": "BOX TYPE SAND TRAP BOTTOM FRAME PROFILE",
    "K11I001012": "FRAME PROFILE LAD F-100",
    "K11I001006": "INNERVANE PROFILE LAD F-75",
    "K11I001011": "VCD PROFILE LAD F-75",
    "K11I009002": "BLADE PROFILE FOR KX3",
    # add the rest of your mapping here...
}

PRODUCTS = {
    "LAD F-75": [
        {"component": "FRAME PROFILE FOR LAD F-75", "unit_weight": 2.166},
        {"component": "INNERVANE PROFILE LAD F-75", "unit_weight": 1.452},
        {"component": "P.C.E. PROFILE LAD F-75", "unit_weight": 1.23},
        {"component": "VCD PROFILE LAD F-75", "unit_weight": 0.606},
    ],
    "LAD F-100": [
        {"component": "FRAME PROFILE LAD F-100", "unit_weight": 2.142},
        {"component": "INNERVANE PROFILE LAD F-100", "unit_weight": 1.728},
        {"component": "PCE PROFILE LAD F-100", "unit_weight": 1.386},
        {"component": "VCD PROFILE LAD F-100", "unit_weight": 0.696},
    ],
}

PROFILE_NAMES = list(PROFILE_MAP.values())

def get_profile_id_by_name(profile_name: str) -> str:
    """Get profile ID by profile name"""
    for profile_id, name in PROFILE_MAP.items():
        if name == profile_name:
            return profile_id
    return None

def get_profile_name_by_id(profile_id: str) -> str:
    """Get profile name by profile ID"""
    return PROFILE_MAP.get(profile_id, None)

def get_cutting_allowance(profile_name: str):
    if profile_name == ("FRAME PROFILE FOR LAD F-75" or "FRAME PROFILE LAD F-100"):
        return FRAME_CUTTING_ALLOWANCE
    else:
        return CUTTING_ALLOWANCE

def classify_bin(length: float) -> str:
    """Classify profiles into bins based on length"""
    if 1000 <= length < 1500:
        return "1000-1500"
    elif 1500 <= length < 3000:
        return "1500-3000"
    elif 3000 <= length <= 6000:
        return "3000-6000"
    else:
        return "out-of-range"

def get_product_names():
    return list(PRODUCTS.keys())

def get_product_components(product_name):
    return PRODUCTS.get(product_name, [])