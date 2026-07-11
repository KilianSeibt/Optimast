from osm import *
from Problem import *
from logger import *
from typing import TypedDict
from plotting import *


class SearchResult(TypedDict):
    costs: float|int
    size_small: int
    size_large: int
    positions_small: set[Tower]
    positions_large: set[Tower]


# We create a cache so we don't solve the LP for the same tower sizes again and again
CACHE: dict[tuple[int, int], SearchResult] = {}

def write_txt_file(small_towers: set[Tower], large_towers: set[Tower]):

    with open("solution.txt", "w") as file:

        for tower in small_towers | large_towers:

            if tower.lat is None:
                lat, lon = utm_to_latlon((tower.x, tower.y), epsg=3035)
                file.write(f'{str(lat)}, {str(lon)}, {tower.radius}\n')
            else:
                file.write(f'{str(tower.lat)}, {str(tower.lon)}, {tower.radius}\n')

def log_start(country: str, grid_density: int):
    print('Program started. Results are saved in the log file results_gradient_search.log.')
    logging.info("=" * 60)
    logging.info("    COMPASS SEARCH - MINIMIZING THE COST OF BUILDING TOWERS")
    logging.info("=" * 60)

    logging.info(f'COUNTRY: {country}')

    logging.info(f'GRID DENSITY: {grid_density}')

def log_results(local_minima: set[tuple], sizes: tuple[int, int], positions: tuple[set, set], costs: float):
    logging.info("\n" + "=" * 60)
    logging.info("               FINAL SUMMARY")
    logging.info("-" * 60)
    logging.info(f"We have found the following local minima:")
    for minimum in local_minima:
        logging.info(f"📍 Tower Sizes: ({minimum[0]}, {minimum[1]}), costs: {minimum[2]:.2f} GE")
    logging.info("-" * 60)
    logging.info(f"The Best Minimum found so far is:")
    logging.info(f" Tower Sizes:              S={sizes[0]}m, L={sizes[1]}m")
    logging.info(f" Nr of small towers:      {len(positions[0])}")
    logging.info(f" Nr of large towers:      {len(positions[1])}")
    logging.info(f" Costs:                   {costs:.2f} GE")
    logging.info("=" * 60)

def find_minimum(problem: Problem, starting_point: tuple[int, int],
                 max_iter: int = 30, step_size: int = 3_000) -> tuple[list[SearchResult], SearchResult]:
    """
    Returns a local minimum
    This is the gradient search algorithm.
    We start with a starting point, and then we look into every direction and see which direction is the steepest.
    If we find a direction that is better than the current best, we go in that direction.
    If we don't find a better direction, we decrease the step size and look again.
    (In this implementation we divide the step size by 2, but we also tried a slower decrease, e.g. multiply by 0.66 etc.)
    max_iter is kind of a safety net: In case we somehow get into an endless loop, we stop after max_iter iterations.
    When we were running the code, we never reached max_iter iterations, because we always found a local minimum before (which means our step size is <= 1).
    param step_size is the step size at the beginning.
    """

    t_1, t_2 = starting_point
    towers_small, towers_large, costs = problem.solve(t_1, t_2)

    best: SearchResult = {'costs': costs, 'size_small': t_1, 'size_large': t_2,
                          'positions_small': towers_small, 'positions_large': towers_large}

    points_to_plot: list[SearchResult] = [best]
    directions = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']

    def local_search(t1: int, t2: int, direction: str) -> SearchResult:
        """
        From the point (t1, t2) we look into the specified direction
        and then solve the LP at the new point and return the solution.
        """
        if direction == 'north':
            t1 += step_size
        elif direction == 'northeast':
            t1 += step_size
            t2 += step_size
        elif direction == 'east':
            t2 += step_size
        elif direction == 'southeast':
            t1 -= step_size
            t2 += step_size
        elif direction == 'south':
            t1 -= step_size
        elif direction == 'southwest':
            t1 -= step_size
            t2 -= step_size
        elif direction == 'west':
            t2 -= step_size
        elif direction == 'northwest':
            t1 += step_size
            t2 -= step_size
        else:
            raise ValueError
        # Now, (t1, t2) is our point where we want to calculate the function value (solve the LP with tower sizes (t1,t2))
        # We first check if we have already calculated the value at this point. If yes, we just return it immediately.
        key = (t1, t2)
        if key in CACHE:
            return CACHE[key]

        # In case we have not calculated this value before, we solve the LP, add the result to the cache, and return the result.
        # We built a try/except block around the pulp solver because in rare edge cases, the pulp solver throws an error while solving the LP.
        # These cases are very rare, and they seem to be an issue with pulp.
        # It was possible to check these points manually, so we are sure that they are no minima:)
        # noinspection PyBroadException
        try:
            towers_s, towers_l, cost = problem.solve(t1, t2)

            val: SearchResult = {'costs': cost, 'size_small': t1, 'size_large': t2,
                                 'positions_small': towers_s, 'positions_large': towers_l}
            CACHE[key] = val

            return val

        except Exception:
            return {'costs': float('inf'), 'size_small': t1, 'size_large': t2,
                    'positions_small': set(), 'positions_large': set()}

    # =========================================================
    for iteration in range(max_iter):
        logging.info(f"\n--- [Iteration {iteration + 1}/{max_iter}] ---")

        # First look in every direction and see which direction is the steepest
        to_compare = []
        for d in directions:
            logging.info(f'Checking {d}...')
            to_compare.append(local_search(best['size_small'], best['size_large'], d))

        best_direction = min(to_compare, key=lambda x: x['costs'])

        # Now compare the results to our current best and decide if it is worth going to the new point or not
        if best_direction['costs'] < best['costs']:
            logging.info(f'Found a next Minimum! {best_direction}')
            best = best_direction
            points_to_plot.append(best_direction)

            # Safety net to ensure that we stay in the range
            best['size_small'] = max(5_000, best['size_small'])
            best['size_large'] = min(100_000, best['size_large'])

        else:
            # If there is no good direction, we decrease the step size and look again
            step_size = round(step_size * 0.5)
            logging.info(f'No better direction found! Next step size is {step_size}')
        if step_size <= 1:
            # we pretty much found our minimum, so lets stop here
            break

    return points_to_plot, best

def calculate_costs(country: str, grid_density: int, point: tuple[int, int]) -> tuple[set, set, float]:

    problem = Problem(grid_density, country=country)
    towers_small, towers_large, costs = problem.solve(point[0], point[1])
    return towers_small, towers_large, costs

def main():
    grid_density = 20_000

    for country in countries:
        log_start(country, grid_density)
        try:
            problem = Problem(grid_density, country=country)
            plot_map(country_data=problem.country_data, grid=problem.grid, headline=country)
        except Exception as e:
            print(f'Country: {country} could not be plotted.')
            print(f"Error: {e}")

    """# Starting points for the gradient search
    starting_points = [(13_700, 44_500)]

    MAX_ITERATIONS = 40
    step_size = 100

    problem = Problem(grid_density, country=country)

    best: SearchResult = {'costs': float('inf'), 'size_small': 0, 'size_large': 0,
                          'positions_small': set(), 'positions_large': set()}
    local_minima: set[tuple] = set()

    # For every starting point, we do compass search and find a local minimum.
    # We log and safe all the minima and keep track of the best minimum found so far
    for starting_point in starting_points:
        logging.info(f'---------------\nSTARTING POINT {starting_point}')
        _, local_minimum = find_minimum(problem, starting_point, max_iter=MAX_ITERATIONS, step_size=step_size)
        entry = (local_minimum['size_small'], local_minimum['size_large'], local_minimum['costs'])
        logging.info('---------------\nLOCAL MINIMUM FOUND AT '
                     f'({entry[0]}, {entry[1]}) '
                     f'WITH COSTS {entry[2]:.2f} GE\n')
        local_minima.add(entry)
        if local_minimum['costs'] < best['costs']:
            best = local_minimum
    # At the end we log our results, write the solution.txt file and plot the coverage with osm.
    log_results(local_minima, (best['size_small'], best['size_large']), (best['positions_small'], best['positions_large']), best['costs'])
    #write_txt_file(best['positions_small'], best['positions_large'])
    visualize_coverage_on_osm(country, (best['size_small'], best['size_large']),
                              (best['positions_small'], best['positions_large']))
"""
if __name__ == "__main__":
    main()
