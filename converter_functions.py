import math
import pyproj

# ==========================================
# A. ANGLE CONVERTERS
# ==========================================

def dd_to_dms_string(dd: float) -> str:
    """
    Converts Decimal Degrees to a formatted DMS string.
    Example: 12.345 -> 12° 20' 42.00"
    """
    is_positive = dd >= 0
    dd = abs(dd)
    
    degrees = int(dd)
    minutes_float = (dd - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    
    # Handle rounding edge case (e.g. 59.999 seconds rounds up to 60)
    seconds = round(seconds, 3)
    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        degrees += 1
        minutes = 0
        
    sign = "" if is_positive else "-"
    return f"""{sign}{degrees}° {minutes}' {seconds:.3f}" """

def dd_to_units(dd: float):
    """
    Returns a dictionary with Radians and Gradians (Gons).
    """
    radians = math.radians(dd)
    gradians = dd * (400 / 360) # 400 gons = 360 degrees
    return {"radians": radians, "gradians": gradians}

def azimuth_to_bearing(azimuth: float) -> str:
    """
    Converts Azimuth (0-360) to Quadrant Bearing (e.g., N 45 E).
    """
    azimuth = azimuth % 360 # Normalize to 0-360
    
    if 0 <= azimuth <= 90:
        return f"N {azimuth}° E"
    elif 90 < azimuth <= 180:
        angle = 180 - azimuth
        return f"S {angle}° E"
    elif 180 < azimuth <= 270:
        angle = azimuth - 180
        return f"S {angle}° W"
    else: # 270 < azimuth <= 360
        angle = 360 - azimuth
        return f"N {angle}° W"

def bearing_to_azimuth(direction: str, angle: float) -> float:
    """
    Converts Bearing (e.g., 'NE', 45) to Azimuth.
    Input: direction (string like 'NE', 'SE', 'SW', 'NW'), angle (float).
    """
    direction = direction.upper().strip()
    
    if direction == "NE":
        return angle
    elif direction == "SE":
        return 180 - angle
    elif direction == "SW":
        return 180 + angle
    elif direction == "NW":
        return 360 - angle
    else:
        raise ValueError("Invalid Direction. Use NE, SE, SW, or NW.")

# ==========================================
# B. DISTANCE & UNIT CONVERTERS
# ==========================================

def convert_length(value: float, from_unit: str, to_unit: str = "meters") -> float:
    """
    Converts various legacy units to Meters (and vice versa).
    Supported 'from_unit': 'meters', 'chains', 'links', 'rods', 'us_feet', 'int_feet'
    """
    # Base conversion to Meters
    to_meters_factors = {
        "meters": 1.0,
        "chains": 20.1168,       # 1 Chain = 66 ft = 20.1168m
        "links": 0.201168,       # 1 Link = 1/100 chain
        "rods": 5.0292,          # 1 Rod = 16.5 ft = 5.0292m
        "int_feet": 0.3048,      # International Foot (1959)
        "us_feet": 1200 / 3937   # US Survey Foot (Legacy) approx 0.3048006
    }
    
    if from_unit not in to_meters_factors:
        raise ValueError(f"Unknown unit: {from_unit}")

    # Step 1: Convert input to Meters
    value_in_meters = value * to_meters_factors[from_unit]
    
    # Step 2: Convert Meters to target unit
    # (To convert meters -> chains, we divide by the factor)
    if to_unit in to_meters_factors:
        return value_in_meters / to_meters_factors[to_unit]
    else:
        return value_in_meters # Default return meters if target not specified

# ==========================================
# C. SCALE CONVERTER
# ==========================================

def map_to_ground(map_dist: float, scale_ratio: float, map_unit="cm", ground_unit="meters") -> float:
    """
    Converts Map Distance to Ground Distance.
    Example: 5cm on 1:2000 map -> 100 meters.
    """
    # 1. Calculate raw ground distance in the SAME unit as map (e.g. cm)
    raw_ground_dist = map_dist * scale_ratio 
    
    # 2. Convert to requested ground unit
    # Assuming map_unit is 'cm' for simplicity, converting to meters
    if map_unit == "cm" and ground_unit == "meters":
        return raw_ground_dist / 100
    elif map_unit == "mm" and ground_unit == "meters":
        return raw_ground_dist / 1000
    else:
        return raw_ground_dist # Return in original unit if no match

# ==========================================
# D. AREA CONVERTERS
# ==========================================

def convert_area(value: float, from_unit: str, to_unit: str) -> float:
    """
    Converts between Area units.
    Supported: 'sq_meters', 'hectares', 'acres', 'sq_feet'
    """
    # Base conversion to Square Meters
    to_sqm_factors = {
        "sq_meters": 1.0,
        "hectares": 10000.0,
        "acres": 4046.856422,  # 1 Acre = 4046.86 m2
        "sq_feet": 0.09290304  # 1 sq ft = 0.0929 m2
    }
    
    if from_unit not in to_sqm_factors or to_unit not in to_sqm_factors:
        raise ValueError("Invalid area unit")
        
    # Step 1: Convert to Square Meters
    value_in_sqm = value * to_sqm_factors[from_unit]
    
    # Step 2: Convert to target unit
    return value_in_sqm / to_sqm_factors[to_unit]


# ==========================================
# E. COORDINATE CONVERSION LOGIC
# ==========================================

# Cache for EPSG codes to speed up app load
_epsg_cache = {}

def get_epsg_codes() -> dict:
    """
    Retrieves available 2D CRS from PyProj. 
    Returns a sorted dictionary: {'Name (EPSG:123)': 'EPSG:123'}
    """

    global _epsg_cache 

    # If already cached, return it
    if _epsg_cache:
        return _epsg_cache

    # If empty, fill it
    crs_info_list = pyproj.database.query_crs_info(auth_name="EPSG", pj_types=None)
    
    temp_dict = {}
    for info in crs_info_list:
        if info.code and info.name:
            label = f"{info.name} (EPSG:{info.code})"
            temp_dict[label] = f"EPSG:{info.code}"
    
    # Sort and save to the global cache
    _epsg_cache = dict(sorted(temp_dict.items()))
    return _epsg_cache

def transform_coords(lon: float, lat: float, source_epsg: str, target_epsg: str):
    """
    Pure logic function to transform coordinates.
    Returns: (x, y) tuple or raises Exception.
    """
    if not source_epsg or not target_epsg:
        raise ValueError("Source or Target CRS not selected")

    source_crs = pyproj.CRS(source_epsg)
    target_crs = pyproj.CRS(target_epsg)
    
    # always_xy=True ensures we always pass (Lon, Lat) or (East, North) order
    transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)
    
    x, y = transformer.transform(lon, lat)
    return x, y

def get_wgs84_coords(x: float, y: float, current_epsg: str):
    """
    Helper to convert ANY projected coordinate to WGS84 (Lat/Lon)
    specifically for the Map display.
    """
    wgs84 = pyproj.CRS("EPSG:4326")
    current_crs = pyproj.CRS(current_epsg)
    
    transformer = pyproj.Transformer.from_crs(current_crs, wgs84, always_xy=True)
    lon, lat = transformer.transform(x, y)
    return lat, lon # Return Lat, Lon order for Folium/Leaflet




# ==========================================
# TEST BLOCK (Run this file to verify)
# ==========================================
if __name__ == "__main__":
    print("--- Testing Angle Converters ---")
    print(f"DMS String: {dd_to_dms_string(12.345)}")
    print(f"Units: {dd_to_units(180)}")
    print(f"Bearing: {azimuth_to_bearing(315)}")
    print(f"Azimuth: {bearing_to_azimuth('NW', 45)}")
    
    print("\n--- Testing Distance Converters ---")
    print(f"1 Chain to Meters: {convert_length(1, 'chains', 'meters')} m")
    print(f"100 US Feet to Int Feet: {convert_length(100, 'us_feet', 'int_feet')} ft")
    
    print("\n--- Testing Scale Converters ---")
    print(f"Map 5cm (1:2000) to Ground: {map_to_ground(5, 2000)} meters")
    
    print("\n--- Testing Area Converters ---")
    print(f"1 Hectare to Acres: {convert_area(1, 'hectares', 'acres')} acres")