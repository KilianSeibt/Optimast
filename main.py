from osm import *
from plot_radii import *
from Problem import *
import json

CACHE: dict[tuple[int, int], dict] = {}

def write_txt_file(small_towers: set[Tower] = None, large_towers: set[Tower] = None):

    with open("solution.txt", "w") as file:

        for tower in small_towers | large_towers:

            if tower.lat is None:
                lat, lon = utm_to_latlon((tower.x, tower.y))
                file.write(f'{str(lat)}, {str(lon)}, {tower.radius}\n')
            else:
                file.write(f'{str(tower.lat)}, {str(tower.lon)}, {tower.radius}\n')

def print_results(best: dict):
    print("\n" + "=" * 60)
    print("               FINALE ERGEBNIS-ZUSAMMENFASSUNG")
    print("-" * 60)
    print(f" BESTE RADIEN:                  S={best['t_1']}m, L={best['t_2']}m")
    print(f" Gebaute kleine Masten (Blau):  {len(best['small_towers'])}")
    print(f" Gebaute große Masten (Lila):  {len(best['large_towers'])}")
    print(f" FINALE MINIMALKOSTEN:          {best['costs']:.2f} GE")
    print("=" * 60)

def find_minimum(t_1: int, t_2: int, grid_density, MAX_ITERATIONS, step_size) -> tuple[list, dict]:

    p = Problem(t_1, t_2, grid_density)
    towers_small, towers_large, _ = p.solve()
    best_costs = len(towers_small) * p.costs['small'] + len(towers_large) * p.costs['large']

    best = {'costs': best_costs, 't_1': t_1, 't_2': t_2,
            'small_towers': towers_small, 'large_towers': towers_large, 'problem': p}

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

        problem = Problem(t1, t2, grid_density)
        try:
            towers_s, towers_l, _ = problem.solve()
            costs = len(towers_s) * problem.costs['small'] + len(towers_l) * problem.costs['large']

            val = {'costs': costs, 't_1': t1, 't_2': t2,
                   'small_towers': towers_s, 'large_towers': towers_l, 'problem': problem}
            CACHE[key] = val

            return val

        except Exception:
            return {'costs': float('inf'), 't_1': t1, 't_2': t2,
                   'small_towers': None, 'large_towers': None, 'problem': problem}


    # =========================================================
    for iteration in range(MAX_ITERATIONS):
        print(f"\n--- [Iteration {iteration + 1}/{MAX_ITERATIONS}] ---")

        # First look in every direction and see which direction is the steepest
        to_compare = []
        for d in directions:
            print(f'Checking {d}...')
            to_compare.append(local_search(best['t_1'], best['t_2'], d))

        best_direction = min(to_compare, key=lambda x: x['costs'])

        # Now compare the results to our current best and decide if it is worth going to the new point our or not
        if best_direction['costs'] < best['costs']:
            print(f'Found a next Minimum! {best_direction}')
            best = best_direction
            points_to_plot.append(best_direction)

            # Safety net to ensure that we stay in the range
            best['t_1'] = max(5_000, best['t_1'])
            best['t_2'] = min(100_000, best['t_2'])

        else:
            # If there is no good direction, we decrease the step size and look again
            step_size = round(step_size * 0.5)
            print(f'No better direction found! Next step size is {step_size}')
        if step_size < 20:
            # we pretty much found our Optimum, so lets stop here
            break

    return points_to_plot, best

def main():
    print("=" * 60)
    print("    STARTE META-OPTIMIERUNG (EPSILON & RADIUS)")
    print("=" * 60)
    
    grid_density = 5_000

    points = range(5_000, 100_000, 5_000)
    points_to_plot = []

    for point1 in points:
        for point2 in points:
            if point1<point2:
                try:
                    print(f'Checke point = ({point1},{point2})')
                    problem = Problem(point1, point2, grid_density)
                    towers_s, towers_l, _ = problem.solve()
                    costs = len(towers_s) * problem.costs['small'] + len(towers_l) * problem.costs['large']
                    points_to_plot.append({'t_1': point1, 't_2': point2, 'costs': costs})
                    points_to_plot.append({'t_1': point2, 't_2': point1, 'costs': costs})
                except Exception:
                    pass

    plot_radii(points_to_plot)
    """
    # Startwerte für die Radien
    starting_points = [(15,50), (15,55), (15,60),
                       (20,30), (20,35), (20,40), (20,45), (20,50), (20,55), (20,60),
                       (25,35), (25,40), (25,45), (25,50), (25,55), (25,60),
                       (30,40), (30,45), (30,50), (30,55), (30,60)
                       ]

    starting_points = [(t1*1000, t2*1000) for (t1,t2) in starting_points]
    
    # Hyperparameter für die Meta-Optimierung
    MAX_ITERATIONS = 20     # Wie oft sollen t_1 und t_2 angepasst werden?
    step_size = 3_000      # Um wie viele Meter sollen t_1/t_2 pro Schritt variieren?
    
    for starting_point in starting_points:
        print(f'STARTING POINT {starting_point}')
        points_to_plot, best = find_minimum(starting_point[0], starting_point[1], grid_density, MAX_ITERATIONS, step_size)

        write_txt_file(best['small_towers'], best['large_towers'])
        #plot_radii(points_to_plot)

        print_results(best)
    
        # OSM-Visualisierung für das absolut beste gefundene Set
        visualize_coverage_on_osm(best['problem'], best['small_towers'], best['large_towers'], best['t_1'], best['t_2'])
"""
if __name__ == "__main__":
    main()