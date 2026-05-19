from models import *
from pulp import *
from osm import *
from plot_radii import *
import time
import timeit
import random


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

        points_to_update = set()
        for city in problem.grids_to_cities[small_or_large][best_point]:
            uncovered_cities.discard(city)
            points_to_update |= problem.cities_to_grids['large'][city]
        for grid_point in points_to_update:
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
        # Sicherheitsnetz: Holt sich eine leere Liste [], falls die Stadt durch das Epsilon unerreichbar wurde
        grids_small = problem.cities_to_grids['small'].get(city, [])
        grids_large = problem.cities_to_grids['large'].get(city, [])
        
        if not grids_small and not grids_large:
            print(f"Warnung: Die Stadt {city.name} kann vom aktuellen Raster (mit Epsilon-Verschiebung) nicht abgedeckt werden!")
            continue # Überspringt diese Stadt, damit das Programm nicht crasht
            
        pulp_problem += lpSum(
            x[g, t]
            for t in ['small', 'large']
            for g in problem.cities_to_grids[t].get(city, [])
        ) >= 1

    # Suppress solver output (CBC only)
    pulp_problem.solve(PULP_CBC_CMD(msg=False))

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
    print("=" * 60)
    print("    STARTE META-OPTIMIERUNG (EPSILON & RADIUS)")
    print("=" * 60)
    
    grid_density = 5_000
    
    # Startwerte für die Radien
    t_1 = 50_000  # small
    t_2 = 60_000  # large
    
    # Hyperparameter für die Meta-Optimierung
    MAX_ITERATIONS = 15     # Wie oft sollen t_1 und t_2 angepasst werden?
    N_EPSILONS = 5         # Wie viele Epsilons pro Iteration testen?
    STEP_SIZE = 1_500      # Um wie viele Meter sollen t_1/t_2 pro Schritt variieren?
    
    best_overall_costs = float('inf')
    best_t_1, best_t_2 = t_1, t_2
    best_epsilon = (0, 0)
    best_small_towers, best_large_towers = set(), set()
    best_problem = None
    
    start_total_time = time.time()

    points_to_plot = []
    
    # =========================================================
    # ÄUSSERE SCHLEIFE: Passe die Tower-Größen an (t_1, t_2)
    # =========================================================
    for iteration in range(MAX_ITERATIONS):
        print(f"\n--- [Iteration {iteration+1}/{MAX_ITERATIONS}] Teste Radien: S={t_1}m, L={t_2}m ---")
        
        current_iter_best_costs = float('inf')
        current_iter_best_eps = (0, 0)
        current_iter_small, current_iter_large = set(), set()
        current_iter_problem = None
        
        # =========================================================
        # INNERE SCHLEIFE: Teste N verschiedene Epsilons
        # =========================================================
        for i in range(N_EPSILONS):
            # 1. Zufälliges Epsilon würfeln (zwischen 0 und grid_density)
            eps_x = random.randint(0, grid_density)
            eps_y = random.randint(0, grid_density)
            
            print(f"  -> Teste Epsilon {i+1}/{N_EPSILONS}: Offset X:{eps_x}m, Y:{eps_y}m... ", end="", flush=True)
            
            # 2. Problem erstellen und MILP lösen
            problem = Problem(t_1, t_2, grid_density, eps_x, eps_y)
            towers_small, towers_large = MILP_approach(problem)
            
            # 3. Kosten berechnen
            costs = len(towers_small) * problem.costs['small'] + len(towers_large) * problem.costs['large']
            print(f"Kosten: {costs:.2f} GE")
            
            # 4. Minimalstes Problem (m_i) dieser Iteration speichern
            if costs < current_iter_best_costs:
                current_iter_best_costs = costs
                points_to_plot.append({'t_1': t_1, 't_2': t_2, 'cost': current_iter_best_costs})
                current_iter_best_eps = (eps_x, eps_y)
                current_iter_small, current_iter_large = towers_small, towers_large
                current_iter_problem = problem

        # =========================================================
        # UPDATE-REGEL (Stochastic Hill Climbing / Pseudo-Gradient)
        # =========================================================
        if current_iter_best_costs < best_overall_costs:
            print(f"  [!] NEUES GLOBALES MINIMUM GEFUNDEN: {current_iter_best_costs:.2f} GE")
            best_overall_costs = current_iter_best_costs
            best_t_1, best_t_2 = t_1, t_2
            best_epsilon = current_iter_best_eps
            best_small_towers, best_large_towers = current_iter_small, current_iter_large
            best_problem = current_iter_problem
            
            # Wir sind auf einem guten Weg! Verändere die Radien leicht für die nächste Runde.
            # Zufälliger Schritt (+ oder - STEP_SIZE)
            t_1 += random.choice([-STEP_SIZE, STEP_SIZE])
            t_2 += random.choice([-STEP_SIZE, STEP_SIZE])
        else:
            print(f"  [x] Keine Verbesserung. Bleibe beim Bisherigen besten.")
            # Wir haben uns verschlechtert! Gehe zurück zu den besten Werten und probiere 
            # eine andere zufällige Richtung aus.
            t_1 = best_t_1 + random.choice([-STEP_SIZE, STEP_SIZE])
            t_2 = best_t_2 + random.choice([-STEP_SIZE, STEP_SIZE])
            
        # Sicherheits-Check: Radien dürfen nicht zu klein werden
        t_1 = max(5_000, t_1)
        t_2 = min(20_000, t_2)

    # =========================================================
    # ENDE DER OPTIMIERUNG - ERGEBNISSE AUSGEBEN
    # =========================================================
    write_txt_file(best_small_towers, best_large_towers)
    plot_radii(points_to_plot)
    
    print("\n" + "=" * 60)
    print("               FINALE ERGEBNIS-ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f" Gesamte Programmlaufzeit:     {time.time() - start_total_time:.2f} Sekunden")
    print("-" * 60)
    print(f" BESTE RADIEN:                  S={best_t_1}m, L={best_t_2}m")
    print(f" BESTES EPSILON (X, Y):         ({best_epsilon[0]}m, {best_epsilon[1]}m)")
    print(f" Gebaute kleine Masten (Blau):  {len(best_small_towers)}")
    print(f" Gebaute große Masten (Lila):  {len(best_large_towers)}")
    print(f" FINALE MINIMALKOSTEN:          {best_overall_costs:.2f} GE")
    print("=" * 60)
    
    # OSM-Visualisierung für das absolut beste gefundene Set
    visualize_coverage_on_osm(best_problem, best_small_towers, best_large_towers)
    print("=" * 60)

if __name__ == "__main__":
    main()