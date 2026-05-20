from models import *
from pulp import *
from osm import *
from plot_radii import *
import time
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
        grids_small = problem.cities_to_grids['small'].get(city, [])
        grids_large = problem.cities_to_grids['large'].get(city, [])
        
        if not grids_small and not grids_large:
            continue 
            
        pulp_problem += lpSum(
            x[g, t]
            for t in ['small', 'large']
            for g in problem.cities_to_grids[t].get(city, [])
        ) >= 1

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
    
    # =========================================================================
    OPTIMIZATION_MODE = "stochastic"  # "grid", "stochastic", oder "epsilon_search"
    # =========================================================================

    grid_density = 2_000
    N_EPSILONS = 10 
    
    best_overall_costs = float('inf')
    best_t_1, best_t_2 = 0, 0
    best_epsilon = (0, 0)
    best_small_towers, best_large_towers = set(), set()
    best_problem = None
    points_to_plot = []

    # --- NEU: Tracking aller Ergebnisse für die Karte ---
    all_test_results = []
    
    def track_result(t_s, t_l, cost, r_s, r_l, ex, ey):
        all_test_results.append({
            'name': f"🎯 {cost:.0f} GE | S={r_s}m, L={r_l}m | Eps=({ex},{ey})",
            'small_towers': t_s,
            'large_towers': t_l,
            'cost': cost
        })

    start_total_time = time.time()

    # -------------------------------------------------------------------------
    # METHODE 1: GRID SEARCH
    # -------------------------------------------------------------------------
    if OPTIMIZATION_MODE == "grid":
        print("Modus: GRID SEARCH (Rastersuche) gestartet...")
        tower_sizes = []
        for i in range(20_200, 20_300, 100):
            for j in range(49_600, 49_800, 50):
                if i < j:
                    tower_sizes.append((i,j))
        
        total_runs = len(tower_sizes) * N_EPSILONS
        print(f"Teste {len(tower_sizes)} Radien-Kombinationen mit je {N_EPSILONS} Epsilon(s). Gesamt: {total_runs} Durchläufe.")
        
        run_count = 1
        for (t_1, t_2) in tower_sizes:
            for e in range(N_EPSILONS):
                #eps_x = random.randint(0, grid_density)
                #eps_y = random.randint(0, grid_density)
                eps_x = 0
                eps_y = 0
                
                print(f"[{run_count}/{total_runs}] Teste S={t_1}, L={t_2}, Eps=({eps_x}, {eps_y})... ", end="", flush=True)
                
                problem = Problem(t_1, t_2, grid_density, eps_x, eps_y)
                towers_small, towers_large = MILP_approach(problem)
                costs = len(towers_small) * problem.costs['small'] + len(towers_large) * problem.costs['large']
                
                print(f"Kosten: {costs:.2f} GE")
                points_to_plot.append({'t_1': t_1, 't_2': t_2, 'cost': costs})
                track_result(towers_small, towers_large, costs, t_1, t_2, eps_x, eps_y)
                
                if costs < best_overall_costs:
                    best_overall_costs = costs
                    best_t_1, best_t_2 = t_1, t_2
                    best_epsilon = (eps_x, eps_y)
                    best_small_towers, best_large_towers = towers_small, towers_large
                    best_problem = problem
                    
                run_count += 1

    # -------------------------------------------------------------------------
    # METHODE 2: STOCHASTIC HILL CLIMBING
    # -------------------------------------------------------------------------
    elif OPTIMIZATION_MODE == "stochastic":
        print("Modus: STOCHASTIC HILL CLIMBING gestartet...")
        MAX_ITERATIONS = 1
        STEP_SIZE = 10
        t_1, t_2 = 20_230, 49_570 
        
        for iteration in range(MAX_ITERATIONS):
            print(f"\n--- [Iteration {iteration+1}/{MAX_ITERATIONS}] Teste Radien: S={t_1}m, L={t_2}m ---")
            
            current_iter_best_costs = float('inf')
            current_iter_best_eps = (0, 0)
            current_iter_small, current_iter_large = set(), set()
            current_iter_problem = None
            
            for i in range(N_EPSILONS):
                #eps_x = random.randint(0, grid_density)
                #eps_y = random.randint(0, grid_density)
                eps_x = 0
                eps_y = 0
                
                print(f"  -> Teste Epsilon {i+1}/{N_EPSILONS}: Offset X:{eps_x}m, Y:{eps_y}m... ", end="", flush=True)
                
                problem = Problem(t_1, t_2, grid_density, eps_x, eps_y)
                towers_small, towers_large = MILP_approach(problem)
                costs = len(towers_small) * problem.costs['small'] + len(towers_large) * problem.costs['large']
                print(f"Kosten: {costs:.2f} GE")
                
                track_result(towers_small, towers_large, costs, t_1, t_2, eps_x, eps_y)
                
                if costs < current_iter_best_costs:
                    current_iter_best_costs = costs
                    current_iter_best_eps = (eps_x, eps_y)
                    current_iter_small, current_iter_large = towers_small, towers_large
                    current_iter_problem = problem

            points_to_plot.append({'t_1': t_1, 't_2': t_2, 'cost': current_iter_best_costs})

            if current_iter_best_costs < best_overall_costs:
                print(f"  [!] NEUES GLOBALES MINIMUM GEFUNDEN: {current_iter_best_costs:.2f} GE")
                best_overall_costs = current_iter_best_costs
                best_t_1, best_t_2 = t_1, t_2
                best_epsilon = current_iter_best_eps
                best_small_towers, best_large_towers = current_iter_small, current_iter_large
                best_problem = current_iter_problem
                
                t_1 += random.choice([-STEP_SIZE, STEP_SIZE])
                t_2 += random.choice([-STEP_SIZE, STEP_SIZE])
                if t_1 > t_2:
                    t_1, t_2 = t_2, t_1
            else:
                print(f"  [x] Keine Verbesserung. Bleibe beim Bisherigen besten.")
                t_1 = best_t_1 + random.choice([-STEP_SIZE, STEP_SIZE])
                t_2 = best_t_2 + random.choice([-STEP_SIZE, STEP_SIZE])
                
            t_1 = max(5_000, t_1)
            t_2 = max(20_000, t_2)

    # -------------------------------------------------------------------------
    # METHODE 3: DIRECTED EPSILON SEARCH
    # -------------------------------------------------------------------------
    elif OPTIMIZATION_MODE == "epsilon_search":
        print("Modus: DIRECTED EPSILON SEARCH (Mustersuche) gestartet...")
        
        best_t_1, best_t_2 = 20_230, 49_570 
        print(f"Fixe Radien: S={best_t_1}m, L={best_t_2}m. Suche besten Grid-Offset...")
        
        eps_x, eps_y = 0, 0
        step_size = grid_density // 4 
        min_step_size = 100            
        
        iteration = 1
        
        # Startpunkt
        problem = Problem(best_t_1, best_t_2, grid_density, eps_x, eps_y)
        towers_small, towers_large = MILP_approach(problem)
        best_overall_costs = len(towers_small) * problem.costs['small'] + len(towers_large) * problem.costs['large']
        best_epsilon = (eps_x, eps_y)
        best_small_towers, best_large_towers = towers_small, towers_large
        best_problem = problem
        print(f"[Start] Offset ({eps_x}, {eps_y}) -> Kosten: {best_overall_costs:.2f} GE")
        track_result(towers_small, towers_large, best_overall_costs, best_t_1, best_t_2, eps_x, eps_y)
        
        while step_size >= min_step_size:
            print(f"\n--- Such-Schrittweite: {step_size}m (Zentrum: {eps_x}, {eps_y}) ---")
            
            neighbors = [
                ((eps_x + step_size) % grid_density, eps_y),
                ((eps_x - step_size) % grid_density, eps_y),
                (eps_x, (eps_y + step_size) % grid_density),
                (eps_x, (eps_y - step_size) % grid_density)
            ]
            
            improved_in_this_step = False
            
            for nx, ny in neighbors:
                problem = Problem(best_t_1, best_t_2, grid_density, nx, ny)
                t_s, t_l = MILP_approach(problem)
                cost = len(t_s) * problem.costs['small'] + len(t_l) * problem.costs['large']
                
                print(f"  Teste Offset ({nx}, {ny}) -> Kosten: {cost:.2f} GE")
                track_result(t_s, t_l, cost, best_t_1, best_t_2, nx, ny)
                
                if cost < best_overall_costs:
                    best_overall_costs = cost
                    best_epsilon = (nx, ny)
                    best_small_towers, best_large_towers = t_s, t_l
                    best_problem = problem
                    
                    eps_x, eps_y = nx, ny
                    improved_in_this_step = True
                    print(f"  [!] Neuer bester Offset gefunden! Gehe in diese Richtung.")
                    break 
                    
            if not improved_in_this_step:
                print(f"  [x] Keine Richtung war besser. Halbiere Schrittweite...")
                step_size //= 2
            
            iteration += 1

    # -------------------------------------------------------------------------
    # AUSWERTUNG UND OUTPUT FÜR ALLE METHODEN
    # -------------------------------------------------------------------------
    if best_problem is not None:
        write_txt_file(best_small_towers, best_large_towers)
        
        try:
            if OPTIMIZATION_MODE != "epsilon_search":
                plot_radii(points_to_plot)
        except NameError:
            pass 
            
        print("\n" + "=" * 60)
        print("               FINALE ERGEBNIS-ZUSAMMENFASSUNG")
        print("=" * 60)
        print(f" Gewählte Methode:              {OPTIMIZATION_MODE.upper()}")
        print(f" Gesamte Programmlaufzeit:     {time.time() - start_total_time:.2f} Sekunden")
        print("-" * 60)
        print(f" BESTE RADIEN:                  S={best_t_1}m, L={best_t_2}m")
        print(f" BESTES EPSILON (X, Y):         ({best_epsilon[0]}m, {best_epsilon[1]}m)")
        print(f" FINALE MINIMALKOSTEN:          {best_overall_costs:.2f} GE")
        print("=" * 60)
        
        # Bereinigung der Ergebnisse: Duplikate entfernen und auf die Top 10 beschränken
        unique_results = []
        seen_names = set()
        for res in sorted(all_test_results, key=lambda x: x['cost']):
            if res['name'] not in seen_names:
                seen_names.add(res['name'])
                unique_results.append(res)
                
        # Maximal 10 Layer, damit die Karte nicht abstürzt!
        if len(unique_results) > 10:
            print("\nHinweis: Es werden nur die 10 besten Durchläufe als Karte gespeichert, um Browser-Abstürze zu vermeiden.")
            unique_results = unique_results[:10]

        map_metadata = {
            'mode': OPTIMIZATION_MODE.upper(),
            'grid_density': grid_density,
            'epsilon': best_epsilon,
            't_1': best_t_1,
            't_2': best_t_2,
            'costs': best_overall_costs
        }
        
        visualize_coverage_on_osm(best_problem, unique_results, metadata=map_metadata)
        print("=" * 60)
    else:
        print("Es wurde kein gültiges Ergebnis gefunden. Überprüfe die Startparameter.")

if __name__ == "__main__":
    main()