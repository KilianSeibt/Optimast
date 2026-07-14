from dataclasses import dataclass
import math
import geopandas as gpd
from shapely.geometry import Point as ShapelyPoint
from pathlib import Path
from enum import StrEnum

from shapely.geometry.geo import box
from shapely.ops import unary_union
from shapely.prepared import prep, PreparedGeometry

"""
This file provides some basic data structures and functions for example, points, towers, cities, calcuate distance,
calculate cost function, check if a point is in a country, load cities.
No big logic happening here^^
"""

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

class Country(StrEnum):
    ALBANIA = "Albania"
    AUSTRIA = "Austria"
    BELARUS = "Belarus"
    BELGIUM = "Belgium"
    BOSNIA = "Bosnia and Herz."
    BULGARIA = "Bulgaria"
    CROATIA = "Croatia"
    CYPRUS = "Cyprus"
    CZECHIA = "Czechia"
    DENMARK = "Denmark"
    ESTONIA = "Estonia"
    FINLAND = "Finland"
    FRANCE = "France"
    GERMANY = "Germany"
    GREECE = "Greece"
    HUNGARY = "Hungary"
    ICELAND = "Iceland"
    IRELAND = "Ireland"
    ITALY = "Italy"
    LATVIA = "Latvia"
    LITHUANIA = "Lithuania"
    LUXEMBOURG = "Luxembourg"
    MOLDOVA = "Moldova"
    MONTENEGRO = "Montenegro"
    NETHERLANDS = "Netherlands"
    NORTH_MACEDONIA = "North Macedonia"
    NORWAY = "Norway"
    POLAND = "Poland"
    PORTUGAL = "Portugal"
    ROMANIA = "Romania"
    SERBIA = "Serbia"
    SLOVAKIA = "Slovakia"
    SLOVENIA = "Slovenia"
    SPAIN = "Spain"
    SWEDEN = "Sweden"
    SWITZERLAND = "Switzerland"
    TURKIYE = "Turkey"
    UKRAINE = "Ukraine"
    UNITED_KINGDOM = "United Kingdom"

@dataclass(frozen=True)
class CountryData:
    name: str
    latlon_plot: gpd.GeoSeries
    utm_plot: gpd.GeoSeries
    latlon_prep: PreparedGeometry
    utm_prep: PreparedGeometry
    epsg: int
    bounds: tuple[int, int, int, int]

# We load the world map from the geopandas library.
_world_lat_lon = gpd.read_file("input_files/ne_110m_admin_0_countries.shp")

def create_country_data(country: Country, epsg: int = 3035) -> CountryData:

    _world_europe_utm = _world_lat_lon.to_crs(epsg=epsg)
    country_latlon = _world_lat_lon[_world_lat_lon["NAME"] == country]

    parts = country_latlon.explode(index_parts=False)
    EUROPE_BOX = box(-25, 34, 45, 72)
    parts = parts[parts.intersects(EUROPE_BOX)]

    country_geometry = unary_union(parts.geometry)
    country_utm = gpd.GeoSeries([country_geometry],crs=_world_lat_lon.crs).to_crs(epsg=epsg)
    xmin, ymin, xmax, ymax = country_utm.iloc[0].bounds
    buffer = 10_000
    return CountryData(
        name = country.capitalize(),
        latlon_plot = gpd.GeoSeries([country_geometry],crs=_world_lat_lon.crs),

        utm_plot = country_utm,

        latlon_prep = prep(country_geometry),
        utm_prep = prep(country_utm.iloc[0]),
        epsg = 3035,
        bounds = (int(xmin)-buffer, int(xmax)+buffer, int(ymin)-buffer, int(ymax)+buffer)
    )


def latlon_to_utm(point: tuple[float, float], country: str) -> tuple[float, float]:
    """
    Converts a point from lat/lon to UTM.

    :param country:
    :param point: (x, y) in meters (UTM)
    :return: (lat, lon)
        """
    if country == 'Paraguay':
        epsg = 32721
    else:
        epsg = 3035

    lat, lon = point
    gdf = gpd.GeoDataFrame(
        geometry=[ShapelyPoint(lon, lat)],
        crs="EPSG:4326"
    )
    gdf_utm = gdf.to_crs(epsg=epsg)
    p = gdf_utm.geometry.iloc[0]
    return p.x, p.y

def utm_to_latlon(point: tuple[float, float], epsg: int) -> tuple[float, float]:

    x, y = point

    gdf = gpd.GeoDataFrame(
        geometry=[ShapelyPoint(x, y)],
        crs=f"EPSG:{epsg}"
    )

    gdf_latlon = gdf.to_crs(epsg=4326)

    lon, lat = gdf_latlon.geometry.iloc[0].x, gdf_latlon.geometry.iloc[0].y

    return lat, lon

def calculate_distance_m(start: tuple[float, float] | Point,
                          destination: tuple[float, float] | Point,
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

def is_in_country(point: tuple[float, float], country_data: CountryData, unit: str) -> bool:

    if unit == 'lon_lat':

        lat, lon = point
        return country_data.latlon_prep.contains(
            ShapelyPoint(lon, lat)
        )
    elif unit == 'utm':
        x, y = point

        return country_data.utm_prep.contains(
            ShapelyPoint(x, y)
        )
    else:
        raise ValueError(
            "unit must be 'lon_lat' or 'xy'"
        )

def load_cities(country: Country) -> tuple[set[City], int]:

    cities: set[City] = set()
    nr_of_cities = 0
    file_path = Path(f"input_files/cities_europe_50k.txt")
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            # Separate each line at the commas
            line =  line.strip().split(",")
            name, lat, lon, cntry = line[0].strip(), float(line[1]), float(line[2]), line[3].strip()

            if cntry == country:

                # Calculate the utm coords right away so we have them ready for later
                x, y = latlon_to_utm((lat, lon), country)
                city = City(name=name, lat=lat, lon=lon, x=x, y=y)
                cities.add(city)
                nr_of_cities += 1
    if nr_of_cities == 0:
        print("No cities found for the given country!")
        print(f"Please check the country name and try again. The country name is: {country}")
    return cities, nr_of_cities