from plotting import *
from models import *
from pulp import *

def calculate_density(cities_small_radius: set[City], cities_large_radius: set[City],
                      costs_small: float, costs_large: float, uncovered_cities: set[City]) -> tuple[float, str]:

    NO_UNCOVERED_VALUE = float("-inf")

    def density(cities: set[City], scale: float) -> float:

        intersection = cities & uncovered_cities
        the_rest = cities - uncovered_cities

        if not intersection:
            return NO_UNCOVERED_VALUE

        score = len(intersection)
        score -= len(the_rest)

        return score / scale

    density_small = density(cities_small_radius, costs_small)
    density_large = density(cities_large_radius, costs_large)

    if density_small == NO_UNCOVERED_VALUE and density_large != NO_UNCOVERED_VALUE:
        return density_large, "large"

    if density_small == NO_UNCOVERED_VALUE and density_large == NO_UNCOVERED_VALUE:
        return NO_UNCOVERED_VALUE, "small"

    return (density_large, 'large') if density_large >= density_small else (density_small, 'small')


def heuristic_approach(problem: Problem) -> tuple[set[Tower], set[Tower]]:

    grid_points_to_density = {}

    tower_coords: dict = {'small': set(), 'large': set()}

    uncovered_cities: set = problem.cities.copy()

    for point in problem.grid:
        density = calculate_density(problem.grids_to_cities['small'][point],
                                    problem.grids_to_cities['large'][point],
                                    problem.costs['small'], problem.costs['large'], uncovered_cities)
        if density != float('-inf'):
            grid_points_to_density[point] = density

    while uncovered_cities:

        best = max(grid_points_to_density.items(), key=lambda x: x[1][0])

        best_point: Point = best[0]
        small_or_large = best[1][1]
        radius = problem.radius[small_or_large]
        tower = Tower(x=best_point.x, y=best_point.y, radius=radius)

        tower_coords[small_or_large].add(tower)

        for city in problem.grids_to_cities[small_or_large][best_point]:
            uncovered_cities.discard(city)
            for grid_point in problem.cities_to_grids['large'][city]:
                density = calculate_density(problem.grids_to_cities['small'][grid_point],
                                            problem.grids_to_cities['large'][grid_point],
                                            problem.costs['small'], problem.costs['large'], uncovered_cities)
                if density == float("-inf"):
                    grid_points_to_density.pop(grid_point)
                else:
                    grid_points_to_density[grid_point] = density

    return tower_coords['small'], tower_coords['large']


def MILP_approach(problem: Problem) -> tuple[set[Tower], set[Tower]]:

    pulp_problem = LpProblem("TowerPlacement", LpMinimize)

    x = {}

    for g in problem.grid:
        for t in ["small", "large"]:
            x[g, t] = LpVariable(f"x_{g.x}_{g.y}_{t}", cat="Binary")

    pulp_problem += lpSum(
        problem.costs[t] * x[g, t]
        for g in problem.grid
        for t in ['small', 'large']
    )

    for city in problem.cities:
        pulp_problem += lpSum(
            x[g, t]
            for t in ['small', 'large']
            for g in problem.cities_to_grids[t][city]
        ) >= 1

    pulp_problem.solve()

    tower_coords: dict = {'small': set(), 'large': set()}

    for t in ['small', 'large']:
        for g in problem.grid:
            if value(x[g, t]) > 0.5:
                tower_coords[t].add(Tower(x=g.x, y=g.y, radius=problem.radius[t]))

    return tower_coords['small'], tower_coords['large']

def write_txt_file(small_towers: set[Tower] = None, large_towers: set[Tower] = None):

    with open("solution.txt", "w") as file:

        for tower in small_towers | large_towers:

            if tower.lat is None:
                lat, lon = utm_to_latlon((tower.x, tower.y))
                file.write(f'{str(lat)}, {str(lon)}, {tower.radius}\n')
            else:
                file.write(f'{str(tower.lat)}, {str(tower.lon)}, {tower.radius}\n')


def main():

    grid_density = 1_000
    tower_size_S, tower_size_L = 17_500, 47_500
    #tower_size_S, tower_size_L = 20_000, 50_000
    problem = Problem(tower_size_S, tower_size_L, grid_density)

    towers_small_coords, towers_large_coords = MILP_approach(problem)

    total_costs = len(towers_small_coords) * problem.costs['small'] + len(towers_large_coords) * problem.costs['large']
    write_txt_file(towers_small_coords, towers_large_coords)
    headline = (f'grid_density = {grid_density}, tower sizes: ({tower_size_S, tower_size_L}'
                f'\n{len(towers_small_coords)} small towers, '
                f'{len(towers_large_coords)} large towers, costs = {total_costs}')

    plot_map(city_coords=problem.cities,
             tower_small_coords=towers_small_coords, tower_large_coords=towers_large_coords,
             radius_small=tower_size_S, radius_large=tower_size_L, headline=headline)


if __name__ == '__main__':
    main()