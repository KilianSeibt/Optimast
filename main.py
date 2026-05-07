from pathlib import Path
import math
import geopandas as gpd
import matplotlib.pyplot as plt
from geopandas import GeoDataFrame
from shapely.geometry import Point
from dataclasses import dataclass
from load_germany import GER_lat_lon_plot, GER_lat_lon_prep, GER_xy_plot, GER_xy_prep

@dataclass
class City:
    # Every city has the following attributes:
    # name, coords in lat/lon format, coords in utm format, covered
    name: str
    lat: float
    lon: float
    x: float
    y: float
    covered: bool

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

def plot_map(city_coords: list[tuple | City] = None, tower_small_coords: list = None, tower_large_coords: list = None, grid: list[tuple] = None, headline: str = 'Städte in Deutschland') -> None:
    """
     Plots the map of Germany including cities, towers, grid, etc.
     Note that the coords of any point can be given in either utm or lat/lon format
    :param headline: The headline of the map
    :param city_coords: List of tuples containing the coords the cities or a list of datatype city.
    The coords can be given in either utm or lat/lon format
    :param tower_small_coords: List of tuples containing the coords of the small towers
    :param tower_large_coords: List of tuples containing the coords of the large towers
    :param grid: List of tuples containing coords of the grid points
    :return:
    """
    fig, ax = plt.subplots(figsize=(8, 10))
    GER_lat_lon_plot.plot(ax=ax, color="lightgray", edgecolor="black")

    def plot_points(points: list[tuple | City], color: str = 'black', marker_size: int = 10) -> GeoDataFrame:
        # Check if the points are of type tuple or City and convert if necessary
        if isinstance(points[0], City):
            points = [(city.lat, city.lon) for city in points]

        # Check if the coords are in utm or lat/lon format
        # In lat/lon format the values are lower than 180. If this is not the case we first have to convert to lat/lon format
        if points[0][0] > 180:
            points = [utm_to_latlon(point) for point in points]

        points = [Point(lon, lat) for lat, lon in points]
        points_gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
        points_gdf.plot(ax=ax, color=color, markersize=marker_size)

        return points_gdf

    def plot_circles(points: list, color: str, radius: int):
        points_gdf = plot_points(points, color)

        points_projected = points_gdf.to_crs(epsg=3035)
        circles = points_projected.buffer(radius*1000)
        circles_gdf = gpd.GeoDataFrame(geometry=circles, crs='EPSG:3035')
        circles_gdf = circles_gdf.to_crs(epsg=4326)

        circles_gdf.plot(ax=ax, facecolor=f'lightcoral', edgecolor=color, alpha=0.3)

    if city_coords:
        _ = plot_points(city_coords)

    if tower_small_coords:
        plot_circles(tower_small_coords, 'blue', 20)

    if tower_large_coords:
        plot_circles(tower_large_coords, 'red', 50)

    if grid:
        plot_points(grid, 'red', 1)


    plt.title(headline)
    plt.show()

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

def calculate_density(cities_small_radius: list[City], cities_large_radius: list[City]) -> tuple[float, str]:
    """if not cities_large_radius:
            return -100, 'large'
        if not cities_small_radius:
            density_small = -100

        all_covered = True

        for city in cities_large_radius:
            if city in cities_small_radius:
                if city.covered:
                    density_large -= 1.0
                    density_small -= 1.0
                else:
                    all_covered = False
                    density_large += 1.0
                    density_small += 1.0
            else:
                if city.covered:
                    density_large -= 1.0
                else:
                    all_covered = False
                    density_large += 1.0

        if all_covered:
            return -100, 'large'
        density_small *= 2.4
        if density_small < density_large:
            return density_large, 'large'
        else:
            return density_small, 'small'"""


    NO_UNCOVERED_VALUE = float("-inf")

    def density(cities: list[City], scale: float) -> float:
        if not cities:
            return NO_UNCOVERED_VALUE

        uncovered_exists = any(not city.covered for city in cities)

        if not uncovered_exists:
            return NO_UNCOVERED_VALUE

        score = 0

        for city in cities:
            if city.covered:
                #score -= scale
                pass
            else:
                score += scale

        return score

    density_small = density(cities_small_radius, 2.4)
    density_large = density(cities_large_radius, 1)

    # Falls nur large noch uncovered Städte enthält
    if density_small == NO_UNCOVERED_VALUE and density_large != NO_UNCOVERED_VALUE:
        return density_large, "large"

    # Falls gar nichts mehr offen ist
    if density_small == NO_UNCOVERED_VALUE and density_large == NO_UNCOVERED_VALUE:
        return NO_UNCOVERED_VALUE, "small"

    # Normale Entscheidung
    if density_large >= density_small:
        return density_large, "large"

    return density_small, "small"

class Meta:

    def __init__(self):
        self.cities = {}
        self.nr_of_cities = 0
        self.grid_points_to_cities_small = {}
        self.grid_points_to_cities_large = {}

    def create_cities(self):

        file_path = Path("input_files/cities_de_50k.txt")
        counter = 0
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
                city = City(name=name, lat=lat, lon=lon, covered=False, x=x, y=y)
                self.cities[parts[0]] = city
                counter += 1
        self.nr_of_cities = counter


    def get_cities_in_circle(self, center: tuple[float, float]) -> tuple[list[City], list[City]]:
        flag = False
        if center == (805000, 5815000):
            flag = True
        cities_in_small_radius = []
        cities_in_large_radius = []
        for city in self.cities.values():
            distance = calculate_distance_km(center, (city.x, city.y), 'utm')
            if distance < 20.0:
                if flag:
                    print(f'{city} is in small radius! Distance is {distance}')
                cities_in_small_radius.append(city)
                cities_in_large_radius.append(city)
            elif distance < 50.0:
                if flag:
                    print(f'{city} is in large radius! Distance is {distance}')
                cities_in_large_radius.append(city)

        return cities_in_small_radius, cities_in_large_radius

    def cover_cities(self, cities: list[City]) -> None:
        for city in cities:
            if not city.covered:
                city.covered = True
                self.nr_of_cities -= 1
        print(f'{self.nr_of_cities} left!')


def main():
    meta = Meta()
    meta.create_cities()
    # Print all the cities and calculate some example distances just for fun:)
    print(f"cities = {meta.cities}")
    #print(f"Distance lat/lon Erlangen - Nuremberg: {calculate_distance_km(meta.cities['Erlangen'], meta.cities['Nürnberg'], 'lat_lon')}")
    #print(f"Distance lat/lon Munich - Berlin: {calculate_distance_km(meta.cities['Munich'], meta.cities['Berlin'], 'lat_lon')}")

    #print(f"Distance utm Erlangen - Nuremberg: {calculate_distance_km(meta.cities['Erlangen'], meta.cities['Nürnberg'], 'utm')}")
    #print(f"Distance utm Munich - Berlin: {calculate_distance_km(meta.cities['Munich'], meta.cities['Berlin'], 'utm')}")

    grid_density = 10_000
    grid = create_grid(grid_density, squared=False)
    grid_points_to_density = {}
    towers_small = []
    towers_large = []

    for point in grid:
        cities_in_small_radius, cities_in_large_radius = meta.get_cities_in_circle(point)
        #print(f'Point = {point}, SMALL = {cities_in_small_radius}, LARGE = {cities_in_large_radius}')
        meta.grid_points_to_cities_small[point] = cities_in_small_radius
        meta.grid_points_to_cities_large[point] = cities_in_large_radius

    number_of_iterations = 1

    while meta.nr_of_cities > 0:
        print(f'Iteration {number_of_iterations}:')
        for point in grid:

            density = calculate_density(meta.grid_points_to_cities_small[point], meta.grid_points_to_cities_large[point])
            if density[0] != float('-inf'):
                grid_points_to_density[point] = calculate_density(meta.grid_points_to_cities_small[point], meta.grid_points_to_cities_large[point])

        grid_points_to_density = sorted(grid_points_to_density.items(), key=lambda  item: item[1][0], reverse=True)

        print(f'grid points to density = {grid_points_to_density}')
        highest_density_point = grid_points_to_density[0][0]
        print(f'highest density point = {highest_density_point}')
        small_or_large = grid_points_to_density[0][1][1]

        if small_or_large == 'small':
            towers_small.append(highest_density_point)
            meta.cover_cities(meta.grid_points_to_cities_small[highest_density_point])
        else:
            towers_large.append(highest_density_point)
            meta.cover_cities(meta.grid_points_to_cities_large[highest_density_point])

        grid_points_to_density = {}
        #plot_map(city_coords=list(meta.cities.values()), tower_small_coords=towers_small,
                # tower_large_coords=towers_large, grid=grid)

        number_of_iterations += 1


    print(f'number of iterations = {number_of_iterations}')

    for city in meta.cities.values():
        print(f'{city.name}: Covered = {city.covered}')
    #plot_map(city_coords=list(coords.values()))
    total_costs = len(towers_small) + 2.4*len(towers_large)
    headline = f'grid_density = {grid_density}\n{number_of_iterations} iterations, {len(towers_small)} small towers, {len(towers_large)} large towers, costs = {total_costs}'
    plot_map(city_coords=list(meta.cities.values()), tower_small_coords = towers_small, tower_large_coords = towers_large, headline=headline, grid=grid)

    #plot_map(city_coords=list(coords.values()))
    #test

if __name__ == '__main__':
    main()