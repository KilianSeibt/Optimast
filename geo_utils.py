import math
import geopandas as gpd
from models import City
from shapely.geometry import Point
from load_germany import GER_lat_lon_plot, GER_lat_lon_prep, GER_xy_plot, GER_xy_prep


def latlon_to_utm(point: tuple[float, float]) -> tuple[float, float]:
    lat, lon = point
    gdf = gpd.GeoDataFrame(
        geometry=[Point(lon, lat)],
        crs="EPSG:4326"
    )
    gdf_utm = gdf.to_crs(epsg=32632)
    p = gdf_utm.geometry.iloc[0]
    return p.x, p.y

def utm_to_latlon(point: tuple[float, float]) -> tuple[float, float]:
    """
    Converts a point from UTM (EPSG:32632) to lat/lon (EPSG:4326).

    :param point: (x, y) in meters (UTM)
    :return: (lat, lon)
    """
    x, y = point

    gdf = gpd.GeoDataFrame(
        geometry=[Point(x, y)],
        crs="EPSG:32632"
    )

    gdf_latlon = gdf.to_crs(epsg=4326)

    lon, lat = gdf_latlon.geometry.iloc[0].x, gdf_latlon.geometry.iloc[0].y

    return lat, lon

def is_in_Germany(point: tuple[float, float], unit: str) -> bool:
    if unit == 'lon_lat':
        lat, lon = point
        return GER_lat_lon_prep.contains(Point(lon, lat))
    elif unit == 'xy':
        x, y = point
        return GER_xy_prep.contains(Point(x, y))
    else:
        raise ValueError

def create_grid(step_size: int, squared: bool = True) -> list[tuple[float, float]]:

    grid = []
    x_min, x_max = (285_000, 915_000)
    y_min, y_max = (5215_000, 6115_000)
    x, y = (x_min, y_min)
    shift = 0.5 * step_size
    even = True
    while y <= y_max:
        while x <= x_max:
            if is_in_Germany((x,y), 'xy'):
                grid.append((x,y))
            x += step_size
        if  not squared:
            if even:
                x = x_min + shift
                even = False
            else:
                even = True
                x = x_min
        else:
            x = x_min
        y += step_size

    return grid


def calculate_distance_km(start: tuple[float, float] | City = None,
                          destination: tuple[float, float] | City = None,
                          unit: str = 'lat_lon'
                          ) -> float:
    """
    Calculates the distance between the two points in km.
    The coords of the two points can either be given in utm or in lat/lon format
    :param start: Start[latitude, longitude] | City
    :param destination: Destination[latitude, longitude] | City
    :param unit: Either 'utm' or 'lat_lon' depending on the format if the coords
    :return: Distance in km
    """

    if unit == 'lat_lon':
        # Radius of the earth in km
        R = 6371.0

        if isinstance(start, tuple) and isinstance(destination, tuple):
            lat1, lon1 = start
            lat2, lon2 = destination
        elif isinstance(start, City) and isinstance(destination, City):
            lat1 = start.lat
            lon1 = start.lon
            lat2 = destination.lat
            lon2 = destination.lon
        else:
            raise ValueError("Wrong data type!")

        # Change to radians
        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        # Differences
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Haversine-Formular
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c

        return distance
    elif unit == 'utm':

        if isinstance(start, tuple) and isinstance(destination, tuple):
            x1, y1 = start
            x2, y2 = destination
        elif isinstance(start, City) and isinstance(destination, City):
            x1 = start.x
            y1 = start.y
            x2 = destination.x
            y2 = destination.y
        else:
            raise ValueError("Wrong data type!")

        dx = x1 - x2
        dy = y1 - y2
        return math.sqrt(dx**2 + dy**2) / 1000

    else:
        raise ValueError