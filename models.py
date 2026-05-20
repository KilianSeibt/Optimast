from abc import abstractmethod
from dataclasses import dataclass
import math
import geopandas as gpd
from shapely.geometry import Point as ShapelyPoint
from load_germany import  GER_lat_lon_prep, GER_xy_prep


@dataclass(slots=True, frozen=True)
class Point:
    lat: float = None
    lon: float = None
    x: float = None
    y: float = None

@dataclass(slots=True, frozen=True)
class Tower(Point):
    radius: int = None


@dataclass(slots=True, frozen=True)
class City(Point):
    name: str = None

def latlon_to_utm(point: tuple[float, float]) -> tuple[float, float]:
    """
    Converts a point from lat/lon (EPSG:4326) to UTM (EPSG:32632).

    :param point: (x, y) in meters (UTM)
    :return: (lat, lon)
        """
    lat, lon = point
    gdf = gpd.GeoDataFrame(
        geometry=[ShapelyPoint(lon, lat)],
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
        geometry=[ShapelyPoint(x, y)],
        crs="EPSG:32632"
    )

    gdf_latlon = gdf.to_crs(epsg=4326)

    lon, lat = gdf_latlon.geometry.iloc[0].x, gdf_latlon.geometry.iloc[0].y

    return lat, lon

def calculate_distance_m(start: tuple[float, float] | Point = None,
                          destination: tuple[float, float] | Point = None,
                          unit: str = 'lat_lon'
                          ) -> float:
    """
    Calculates the distance between the two points in km.
    The coords of the two points can either be given in utm or in lat/lon format
    :param start: Start[latitude, longitude] | Point
    :param destination: Destination[latitude, longitude] | Point
    :param unit: Either 'utm' or 'lat_lon' depending on the format if the coords
    :return: Distance in m
    """

    if unit == 'lat_lon':
        # Radius of the earth in m
        R = 6_371_000.0

        if isinstance(start, tuple) and isinstance(destination, tuple):
            lat1, lon1 = start
            lat2, lon2 = destination
        elif isinstance(start, Point) and isinstance(destination, Point):
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
        elif isinstance(start, Point) and isinstance(destination, Point):
            x1 = start.x
            y1 = start.y
            x2 = destination.x
            y2 = destination.y
        else:
            raise ValueError("Wrong data type!")

        dx = x1 - x2
        dy = y1 - y2
        return math.sqrt(dx**2 + dy**2)

    else:
        raise ValueError

def cost_function(radius: float) -> float:

    # Radius is given in m, so we have to convert to km
    radius /= 1000.0

    if radius < 5:
        raise ValueError
    elif radius < 20:
        return (0.00003898883009994121 * radius**3
                - 0.0005848324514991181  * radius**2
                + 0.000818342151675485   * radius
                + 0.9056554967666078)
    elif radius < 35:
        return (-0.00004679600235155791 * radius**3
                + 0.004562257495590829    * radius**2
                - 0.10212345679012345     * radius
                + 1.591934156378601)
    elif radius < 50:
        return (0.00005930629041740153 * radius**3
                - 0.006578483245149912   * radius**2
                + 0.2878024691358025     * radius
                - 2.957201646090535)
    elif radius <= 100:
        return (-0.00001544973544973545 * radius**3
                + 0.004634920634920635    * radius**2
                - 0.27286772486772487     * radius
                + 6.387301587301588)
    else:
        raise ValueError

def is_in_Germany(point: tuple[float, float], unit: str) -> bool:
    if unit == 'lon_lat':
        lat, lon = point
        return GER_lat_lon_prep.contains(ShapelyPoint(lon, lat))
    elif unit == 'xy':
        x, y = point
        return GER_xy_prep.contains(ShapelyPoint(x, y))
    else:
        raise ValueError