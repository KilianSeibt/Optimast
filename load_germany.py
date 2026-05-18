import geopandas as gpd
from shapely.prepared import prep

# --- load only once ---
_world_lat_lon = gpd.read_file("input_files/ne_110m_admin_0_countries.shp")

# --- LAT/LON ---
GER_lat_lon_ROW = _world_lat_lon[_world_lat_lon["NAME"] == "Germany"].iloc[0]

GER_lat_lon_plot = gpd.GeoSeries([GER_lat_lon_ROW.geometry], crs=_world_lat_lon.crs)
GER_lat_lon_prep = prep(GER_lat_lon_ROW.geometry)

# --- XY (UTM) ---
_world_xy = _world_lat_lon.to_crs(epsg=32632)

GER_xy_ROW = _world_xy[_world_xy["NAME"] == "Germany"].iloc[0]

GER_xy_plot = GER_xy_ROW.geometry
GER_xy_prep = prep(GER_xy_plot)