from pulp import *
from pathlib import Path
from models import *
import traceback


class Problem:

    # Füge epsilon_x und epsilon_y mit Standardwert 0 hinzu
    def __init__(self, R_small, R_large, grid_density, epsilon_x=0, epsilon_y=0, penalty=0):

        self.cities: set[City] = set()
        self.nr_of_cities: int = 0
        self.grid: set[Point] = set()
        self.grids_to_cities: dict[str, dict] = {'small': {}, 'large': {}}
        self.cities_to_grids: dict[str, dict] = {'small': {}, 'large': {}}
        self.radius: dict = {'small': R_small, 'large': R_large}
        self.costs: dict = {'small': cost_function(R_small), 'large': cost_function(R_large)}

        self.grid_density = grid_density
        self.epsilon_x = epsilon_x
        self.epsilon_y = epsilon_y

        self.penalty = penalty

        self.load_cities()
        self.create_grid(step_size=self.grid_density)

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

        # --- NEU: Epsilon auf den Startwert addieren ---
        start_x = x_min + self.epsilon_x
        start_y = y_min + self.epsilon_y

        x, y = (start_x, start_y)
        shift = 0.5 * step_size
        even = True

        while y <= y_max:
            while x <= x_max:
                if is_in_Germany((x, y), 'xy'):
                    self.grid.add(Point(x=x, y=y))
                x += step_size

            # X muss für die neue Zeile auf den EPSILON-Startwert zurückgesetzt werden!
            if pattern == 'hexagon':
                if even:
                    x = start_x + shift
                    even = False
                else:
                    even = True
                    x = start_x
            elif pattern == 'square':
                x = start_x
            else:
                raise ValueError

            y += step_size

    def solve(self) -> tuple[set[Tower], set[Tower], float]:

        pulp_problem = LpProblem("TowerPlacement", LpMinimize)

        x = {}
        covered_cities = {}
        constant_cost = len(self.cities)

        for g in self.grid:
            for t in ["small", "large"]:
                x[g, t] = LpVariable(f"x_{g.x}_{g.y}_{t}", cat="Binary")
                covered_cities[g, t] = len(self.grids_to_cities[t][g])

        pulp_problem += lpSum(
            self.costs[t] * x[g, t] + covered_cities[g, t] * x[g, t] * self.penalty
            for g in self.grid
            for t in ['small', 'large']
        )

        for city in self.cities:
            # Sicherheitsnetz: Holt sich eine leere Liste [], falls die Stadt durch das Epsilon unerreichbar wurde
            grids_small = self.cities_to_grids['small'].get(city, [])
            grids_large = self.cities_to_grids['large'].get(city, [])

            if not grids_small and not grids_large:
                print(
                    f"Warnung: Die Stadt {city.name} kann vom aktuellen Raster (mit Epsilon-Verschiebung) nicht abgedeckt werden!")
                continue  # Überspringt diese Stadt, damit das Programm nicht crasht

            pulp_problem += lpSum(
                x[g, t]
                for t in ['small', 'large']
                for g in self.cities_to_grids[t].get(city, [])
            ) >= 1

        solver = PULP_CBC_CMD(
            msg=False,
            logPath="cbc.log"
        )

        try:
            status = pulp_problem.solve(solver)

            status_str = LpStatus[status]

            if status_str != "Optimal":
                pulp_problem.writeLP("failed_model.lp")
                raise RuntimeError(f"Solver status: {status_str}")

        except Exception:
            pulp_problem.writeLP("crash_model.lp")
            traceback.print_exc()
            raise

        tower_coords: dict = {'small': set(), 'large': set()}
        interference_cost = -constant_cost * self.penalty

        for t in ['small', 'large']:
            for g in self.grid:
                if value(x[g, t]) > 0.5:
                    tower_coords[t].add(Tower(x=g.x, y=g.y, radius=self.radius[t]))
                    interference_cost += (value(x[g, t]) * covered_cities[g, t]) * self.penalty

        return tower_coords['small'], tower_coords['large'], interference_cost