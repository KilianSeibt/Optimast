from abc import abstractmethod
from dataclasses import dataclass
import math
import geopandas as gpd
from shapely.geometry import Point as ShapelyPoint
from pathlib import Path
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

class Problem:

    def __init__(self, R_small, R_large, grid_density):

        self.cities: set[City] = set()
        self.nr_of_cities: int = 0
        self.grid: set[Point] = set()
        self.grids_to_cities: dict[str, dict] = {'small': {}, 'large': {}}
        self.cities_to_grids: dict[str, dict] = {'small': {}, 'large': {}}
        self.radius: dict = {'small': R_small, 'large': R_large}
        self.costs: dict = {'small': cost_function(R_small), 'large': cost_function(R_large)}

        self.load_cities()
        self.create_grid(grid_density, pattern='square')
        self.get_points_in_circles()

    def load_cities(self):

        file_path = Path("input_files/cities_de_50k.txt")
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                # Separate each line at the commas
                parts: list = line.strip().split(",")

                # Latitude is the second entry in parts, longitude is the third entry in parts
                name = parts[0]
                lat = float(parts[1])
                lon = float(parts[2])
                # Calculate the utm coords right away so we have them ready for later
                x,  y = latlon_to_utm((lat, lon))
                city = City(name=name, lat=lat, lon=lon, x=x, y=y)
                self.cities.add(city)
                self.nr_of_cities += 1

    def add_to_dicts(self, grid_point: Point, city: City, small_or_large: str):

        if grid_point in self.grids_to_cities[small_or_large]:
            self.grids_to_cities[small_or_large][grid_point].add(city)
        else:
            self.grids_to_cities[small_or_large][grid_point] = {city}

        if city in self.cities_to_grids[small_or_large]:
            self.cities_to_grids[small_or_large][city].add(grid_point)
        else:
            self.cities_to_grids[small_or_large][city] = {grid_point}


    def get_points_in_circles(self) -> None:

        for grid_point in self.grid.copy():
            for city in self.cities:
                distance = calculate_distance_m(city, grid_point, 'utm')

                if distance < self.radius['small']:
                    self.add_to_dicts(grid_point, city, 'small')
                    self.add_to_dicts(grid_point, city, 'large')

                elif distance < self.radius['large']:
                    self.add_to_dicts(grid_point, city, 'large')
            if not grid_point in self.grids_to_cities['large']:
                self.grids_to_cities['large'][grid_point] = set()
            if not grid_point in self.grids_to_cities['small']:
                self.grids_to_cities['small'][grid_point] = set()

    def create_grid(self, step_size: int, pattern: str = 'square') -> None:

        x_min, x_max = (285_000, 915_000)
        y_min, y_max = (5215_000, 6115_000)
        x, y = (x_min, y_min)
        shift = 0.5 * step_size
        even = True
        while y <= y_max:
            while x <= x_max:
                if is_in_Germany((x, y), 'xy'):
                    self.grid.add(Point(x=x, y=y))
                x += step_size
            if pattern == 'hexagon':
                if even:
                    x = x_min + shift
                    even = False
                else:
                    even = True
                    x = x_min
            elif pattern == 'square':
                x = x_min
            else:
                raise ValueError
            y += step_size

class Solver:

    @abstractmethod
    def solve(self, problem: Problem):
        pass

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