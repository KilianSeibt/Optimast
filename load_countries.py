import geopandas as gpd
from shapely.prepared import prep

# ---------------------------------------------------------
# LOAD WORLD SHAPEFILE ONLY ONCE
# ---------------------------------------------------------

_world_lat_lon = gpd.read_file(
    "input_files/ne_110m_admin_0_countries.shp"
)

# ---------------------------------------------------------
# PROJECTED CRS
# ---------------------------------------------------------

# Europe (Germany + France)
_world_europe_utm = _world_lat_lon.to_crs(epsg=32632)

# USA
_world_usa_utm = _world_lat_lon.to_crs(epsg=5070)

# ---------------------------------------------------------
# COUNTRY CONFIGURATION
# ---------------------------------------------------------

COUNTRY_DATA = {}

# =========================================================
# GERMANY
# =========================================================

ger_latlon_row = _world_lat_lon[
    _world_lat_lon["NAME"] == "Germany"
].iloc[0]

ger_xy_row = _world_europe_utm[
    _world_europe_utm["NAME"] == "Germany"
].iloc[0]

COUNTRY_DATA["Germany"] = {
    "latlon_prep": prep(ger_latlon_row.geometry),
    "xy_prep": prep(ger_xy_row.geometry),

    # UTM-like bounds
    "bounds": (
        285_000,
        915_000,
        5_215_000,
        6_115_000
    )
}

# =========================================================
# FRANCE
# =========================================================

fra_latlon_row = _world_lat_lon[
    _world_lat_lon["NAME"] == "France"
].iloc[0]

fra_xy_row = _world_europe_utm[
    _world_europe_utm["NAME"] == "France"
].iloc[0]

COUNTRY_DATA["France"] = {
    "latlon_prep": prep(fra_latlon_row.geometry),
    "xy_prep": prep(fra_xy_row.geometry),

    "bounds": (
        -200_000,
        1_200_000,
        4_600_000,
        5_700_000
    )
}

# =========================================================
# USA
# =========================================================

usa_latlon_row = _world_lat_lon[
    _world_lat_lon["NAME"] == "United States of America"
].iloc[0]

usa_xy_row = _world_usa_utm[
    _world_usa_utm["NAME"] == "United States of America"
].iloc[0]

COUNTRY_DATA["USA"] = {
    "latlon_prep": prep(usa_latlon_row.geometry),
    "xy_prep": prep(usa_xy_row.geometry),

    "bounds": (
        -2_600_000,
        2_600_000,
        1_300_000,
        3_200_000
    )
}