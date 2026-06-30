from osm import *
from Problem import *
from logger import *

CACHE: dict[tuple[int, int], dict] = {}

def write_txt_file(small_towers: set[Tower] = None, large_towers: set[Tower] = None):

    with open("solution.txt", "w") as file:

        for tower in small_towers | large_towers:

            if tower.lat is None:
                lat, lon = utm_to_latlon((tower.x, tower.y))
                file.write(f'{str(lat)}, {str(lon)}, {tower.radius}\n')
            else:
                file.write(f'{str(tower.lat)}, {str(tower.lon)}, {tower.radius}\n')

def log_results(local_minima: set[tuple], best: dict):
    logging.info("\n" + "=" * 60)
    logging.info("               FINAL SUMMARY")
    logging.info("-" * 60)
    logging.info(f"We have found the following local minima:")
    for minimum in local_minima:
        logging.info(f"📍 Tower Sizes: ({minimum[0]}, {minimum[1]}), costs: {minimum[2]:.2f} GE")
    logging.info("-" * 60)
    logging.info(f"The Best Minimum found so far is:")
    logging.info(f" Tower Sizes:              S={best['size_small']}m, L={best['size_large']}m")
    logging.info(f" Nr of small towers:      {len(best['positions_small'])}")
    logging.info(f" Nr of large towers:      {len(best['positions_large'])}")
    logging.info(f" Costs:                   {best['costs']:.2f} GE")
    logging.info("=" * 60)

def find_minimum(problem: Problem, starting_point: tuple[int, int],
                 max_iter: int = 30, step_size: int = 3_000) -> tuple[list, dict]:

    CACHE.clear()

    t_1, t_2 = starting_point
    towers_small, towers_large, costs = problem.solve(t_1, t_2)

    best = {'costs': costs, 'size_small': t_1, 'size_large': t_2,
            'positions_small': towers_small, 'positions_large': towers_large}

    points_to_plot = [best]
    directions = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']

    def local_search(t1: int, t2: int, direction: str) -> dict | None:
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
        key = (t1, t2)
        if key in CACHE:
            return CACHE[key]

        try:
            towers_s, towers_l, cost = problem.solve(t1, t2)

            val = {'costs': cost, 'size_small': t1, 'size_large': t2,
                    'positions_small': towers_s, 'positions_large': towers_l}
            CACHE[key] = val

            return val

        except Exception:
            return {'costs': float('inf'), 'size_small': t1, 'size_large': t2,
                    'positions_small': None, 'positions_large': None}


    # =========================================================
    for iteration in range(max_iter):
        logging.info(f"\n--- [Iteration {iteration + 1}/{max_iter}] ---")

        # First look in every direction and see which direction is the steepest
        to_compare = []
        for d in directions:
            logging.info(f'Checking {d}...')
            to_compare.append(local_search(best['size_small'], best['size_large'], d))

        best_direction = min(to_compare, key=lambda x: x['costs'])

        # Now compare the results to our current best and decide if it is worth going to the new point our or not
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
            # we pretty much found our Optimum, so lets stop here
            break

    return points_to_plot, best

def main():
    print('Program started. Results are saved in the log file results_gradient_search.log.')
    logging.info("=" * 60)
    logging.info("    GRADIENT SEARCH - MINIMIZING THE COST OF BUILDING TOWERS")
    logging.info("=" * 60)
    country = 'Germany'
    logging.info(f'COUNTRY: {country}')
    grid_density = 2_000
    logging.info(f'GRID DENSITY: {grid_density}')


    # Startwerte für die Radien
    starting_points = [(t1*1000,t2*1000) for t1 in range(15, 80, 5) for t2 in range(t1+5, 90, 5)]


    # Hyperparameter für die Meta-Optimierung
    MAX_ITERATIONS = 40
    step_size = 2_000

    problem = Problem(grid_density, country=country)

    best = {'costs': float('inf'), 'size_small': 0, 'size_large': 0,
            'positions_small': set(), 'positions_large': set()}
    local_minima: set[tuple] = set()

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

        #write_txt_file(best['small_towers'], best['large_towers'])
        #plot_radii(points_to_plot)

    log_results(local_minima, best)
    # OSM-Visualisierung für das absolut beste gefundene Set
    visualize_coverage_on_osm(country, (best['size_small'], best['size_large']), (best['positions_small'], best['positions_large']))
    print('Finished!')

if __name__ == "__main__":
    main()