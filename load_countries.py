import geopandas as gpd
from shapely.geometry.geo import box
from shapely.ops import unary_union
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

ger_utm_row = _world_europe_utm[
    _world_europe_utm["NAME"] == "Germany"
].iloc[0]

COUNTRY_DATA["Germany"] = {
    "latlon_plot": gpd.GeoSeries([ger_latlon_row.geometry],crs=_world_lat_lon.crs),

    "utm_plot": gpd.GeoSeries([ger_utm_row.geometry],crs=_world_europe_utm.crs),

    "latlon_prep": prep(ger_latlon_row.geometry),
    "utm_prep": prep(ger_utm_row.geometry),

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

fra = _world_lat_lon[_world_lat_lon["NAME"] == "France"]

parts = fra.explode(index_parts=False)

parts = parts[parts.intersects(box(-10, 40, 15, 55))]

parts_utm = parts.to_crs(32632)

fra_geom_latlon = unary_union(parts.geometry)
fra_geom_utm = unary_union(parts_utm.geometry)

COUNTRY_DATA["France"] = {
    "latlon_plot": gpd.GeoSeries([fra_geom_latlon], crs=_world_lat_lon.crs),

    "utm_plot": gpd.GeoSeries([fra_geom_utm], crs=_world_europe_utm.crs),

    "latlon_prep": prep(fra_geom_latlon),
    "utm_prep": prep(fra_geom_utm),

    "bounds": (
        -678_983,
        584_102,
        4_634_280,
        5_854_153,
    )
}