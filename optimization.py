from pathlib import Path
from models import City
from geo_utils import latlon_to_utm, calculate_distance_km, create_grid


def calculate_density(cities_small_radius: list[City], cities_large_radius: list[City]) -> tuple[float, str]:
    NO_UNCOVERED_VALUE = float("-inf")

    def density(cities: list[City], scale: float) -> float:
        if not cities:
            return NO_UNCOVERED_VALUE
        uncovered_exists = any(not city.covered for city in cities)
        if not uncovered_exists:
            return NO_UNCOVERED_VALUE
        score = 0
        for city in cities:
            if not city.covered:
                score += scale
        return score

    density_small = density(cities_small_radius, 2.4)
    density_large = density(cities_large_radius, 1)

    if density_small == NO_UNCOVERED_VALUE and density_large != NO_UNCOVERED_VALUE:
        return density_large, "large"
    if density_small == NO_UNCOVERED_VALUE and density_large == NO_UNCOVERED_VALUE:
        return NO_UNCOVERED_VALUE, "small"
    if density_large >= density_small:
        return density_large, "large"
    return density_small, "small"

class Meta:
    def __init__(self):
        self.cities = {}
        self.nr_of_cities = 0

    def create_cities(self):
        file_path = Path("input_files/cities_de_50k.txt")
        counter = 0
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                parts = line.strip().split(",")
                name = parts[0]
                lat = float(parts[1])
                lon = float(parts[2])
                x,  y = latlon_to_utm((lat, lon))
                city = City(name=name, lat=lat, lon=lon, covered=False, x=x, y=y)
                self.cities[name] = city
                counter += 1
        self.nr_of_cities = counter

    def get_cities_in_circle(self, center: tuple[float, float]) -> tuple[list[City], list[City]]:
        cities_in_small_radius = []
        cities_in_large_radius = []
        for city in self.cities.values():
            distance = calculate_distance_km(center, (city.x, city.y), 'utm')
            if distance < 20.0:
                cities_in_small_radius.append(city)
                cities_in_large_radius.append(city)
            elif distance < 50.0:
                cities_in_large_radius.append(city)
        return cities_in_small_radius, cities_in_large_radius

    def cover_cities(self, cities: list[City]) -> None:
        for city in cities:
            if not city.covered:
                city.covered = True
                self.nr_of_cities -= 1
                

def run_optimization(meta: Meta, grid_density: int) -> dict:
    print(f"\n--- Starte Optimierung für {grid_density//1000}km Raster ---")
    
    # Setze alle Städte für diesen Durchlauf zurück
    for city in meta.cities.values():
        city.covered = False
    meta.nr_of_cities = len(meta.cities)

    grid = create_grid(grid_density, squared=False)
    towers_small = []
    towers_large = []
    
    point_to_cities_small = {}
    point_to_cities_large = {}

    print("Berechne Entfernungen im Voraus...")
    for point in grid:
        small_r, large_r = meta.get_cities_in_circle(point)
        point_to_cities_small[point] = small_r
        point_to_cities_large[point] = large_r

    iterations = 1
    while meta.nr_of_cities > 0:
        grid_points_to_density = {}
        for point in grid:
            density = calculate_density(point_to_cities_small[point], point_to_cities_large[point])
            if density[0] != float('-inf'):
                grid_points_to_density[point] = density

        if not grid_points_to_density:
            print("Abbruch: Keine Städte mehr erreichbar!")
            break

        grid_points_to_density = sorted(grid_points_to_density.items(), key=lambda item: item[1][0], reverse=True)
        highest_density_point = grid_points_to_density[0][0]
        small_or_large = grid_points_to_density[0][1][1]

        if small_or_large == 'small':
            towers_small.append(highest_density_point)
            meta.cover_cities(point_to_cities_small[highest_density_point])
        else:
            towers_large.append(highest_density_point)
            meta.cover_cities(point_to_cities_large[highest_density_point])

        iterations += 1

    total_costs = len(towers_small) + 2.4 * len(towers_large)
    city_status_snapshot = {name: city.covered for name, city in meta.cities.items()}

    print(f"Ergebnis: {total_costs} Kosten, {iterations} Iterationen.")

    return {
        "towers_small": towers_small,
        "towers_large": towers_large,
        "costs": total_costs,
        "iterations": iterations,
        "city_status": city_status_snapshot
    }                