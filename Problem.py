from pulp import *
from models import *

"""
This file creates and solves the LP (See below).
"""

class Problem:

    # A problem has a country_data, a grid, cities and a penalty. The tower sizes are given as parameters in Problem.solve()
    country_data: CountryData
    grid: set[Point]
    cities: set[City]
    nr_of_cities: int
    penalty: float

    def __init__(self, grid_density: int, country: str, eps_x: int = 0, eps_y: int = 0,
                 penalty: float = 0):

        self.country_data: CountryData = create_country_data(country)
        self.cities, self.nr_of_cities = load_cities(country=country)
        self.create_grid(grid_density, eps_x, eps_y)

        self.penalty = penalty

    def create_grid(self, grid_density: int, eps_x: int, eps_y: int, pattern: str = 'square') -> None:

        """
        Creates a grid of candidate points. The pattern is either 'square' or 'hexagon'.
        For a high density, we don't think that it makes much of difference though.
        eps_x and eps_y are the shift of the grid in x and y direction.
        We do this to make sure we dont overlook some edge case where one tower can barely reach two cities only if a grid point is at a certain position. (make it more robust)
        For high grid density, we don't really need that anymore though.
        """

        step_size = grid_density

        x_min, x_max, y_min, y_max = self.country_data.bounds

        start_x = x_min + eps_x
        start_y = y_min + eps_y

        x = start_x
        y = start_y

        shift = 0.5 * step_size
        even = True

        grid: set[Point] = set()

        while y <= y_max:
            while x <= x_max:
                # if is_in_country((x, y), country, 'utm'):
                grid.add(Point(x=x, y=y))

                x += step_size

            # -----------------------------------
            # reset x for next row
            # -----------------------------------

            if pattern == 'hexagon':
                if even:
                    x = start_x + shift
                    even = False

                else:
                    x = start_x
                    even = True

            elif pattern == 'square':
                x = start_x

            else:
                raise ValueError(
                    "pattern must be square or hexagon"
                )
            y += step_size
        self.grid = grid

    def get_points_in_circles(self, radius_small: int, radius_large: int) -> tuple[dict, dict]:

        grids_to_cities: dict[str, dict] = {'small': {}, 'large': {}}
        cities_to_grids: dict[str, dict] = {'small': {}, 'large': {}}

        def add_to_dicts(small_or_large: str):

            if grid_point in grids_to_cities[small_or_large]:
                grids_to_cities[small_or_large][grid_point].add(city)
            else:
                grids_to_cities[small_or_large][grid_point] = {city}

            if city in cities_to_grids[small_or_large]:
                cities_to_grids[small_or_large][city].add(grid_point)
            else:
                cities_to_grids[small_or_large][city] = {grid_point}

        for grid_point in self.grid.copy():
            for city in self.cities:
                distance = calculate_distance_m(city, grid_point, 'utm')
                if distance < radius_large:
                    add_to_dicts('large')
                    if distance < radius_small:
                        add_to_dicts('small')

            if not grid_point in grids_to_cities['large']:
                grids_to_cities['large'][grid_point] = set()
            if not grid_point in grids_to_cities['small']:
                grids_to_cities['small'][grid_point] = set()

        return grids_to_cities, cities_to_grids

    def solve(self, radius_small: int, radius_large: int) -> tuple[set[Tower], set[Tower], float]:
        """
        For given tower sizes we solve the LP using PuLP.
        We return the set of small towers, the set of large towers and the total costs.
        """

        radius = {'small': radius_small, 'large': radius_large}
        grids_to_cities, cities_to_grids = self.get_points_in_circles(radius_small, radius_large)
        costs: dict[str, float] = {'small': cost_function(radius_small), 'large': cost_function(radius_large)}

        pulp_problem = LpProblem("TowerPlacement", LpMinimize)

        x = {}
        covered_cities = {}
        constant_cost = len(self.cities)

        for g in self.grid:
            for t in ["small", "large"]:
                x[g, t] = LpVariable(f"x_{g.x}_{g.y}_{t}", cat="Binary")
                covered_cities[g, t] = len(grids_to_cities[t][g])

        pulp_problem += lpSum(
            costs[t] * x[g, t] + covered_cities[g, t] * x[g, t] * self.penalty
            for g in self.grid
            for t in ['small', 'large']
        )

        for city in self.cities:
            # Sicherheitsnetz: Holt sich eine leere Liste [], falls die Stadt durch das Epsilon unerreichbar wurde
            grids_small = cities_to_grids['small'].get(city, [])
            grids_large = cities_to_grids['large'].get(city, [])

            if not grids_small and not grids_large:
                print(
                    f"Warnung: Die Stadt {city.name} kann vom aktuellen Raster (mit Epsilon-Verschiebung) nicht abgedeckt werden!")
                continue  # Überspringt diese Stadt, damit das Programm nicht crasht

            pulp_problem += lpSum(
                x[g, t]
                for t in ['small', 'large']
                for g in cities_to_grids[t].get(city, [])
            ) >= 1

        # Suppress solver output (CBC only)
        pulp_problem.solve(PULP_CBC_CMD(msg=False))
        for city in self.cities:
            coverage = sum(
                value(x[g, t])
                for t in ["small", "large"]
                for g in cities_to_grids[t].get(city, [])
            )

            if coverage < 0.5:
                print(city.name, coverage)

        tower_coords: dict = {'small': set(), 'large': set()}
        interference_cost = -constant_cost * self.penalty

        for t in ['small', 'large']:
            for g in self.grid:
                if value(x[g, t]) > 0.5:
                    tower_coords[t].add(Tower(x=g.x, y=g.y, radius=radius[t]))
                    interference_cost += (value(x[g, t]) * covered_cities[g, t]) * self.penalty

        total_costs = (len(tower_coords['small']) * costs['small']
                       + len(tower_coords['large']) * costs['large']
                       + interference_cost)

        return tower_coords['small'], tower_coords['large'], total_costs