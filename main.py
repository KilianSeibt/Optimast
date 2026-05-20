from osm import *
from plot_radii import *
from Problem import *
import random


def write_txt_file(small_towers: set[Tower] = None, large_towers: set[Tower] = None):

    with open("solution.txt", "w") as file:

        for tower in small_towers | large_towers:

            if tower.lat is None:
                lat, lon = utm_to_latlon((tower.x, tower.y))
                file.write(f'{str(lat)}, {str(lon)}, {tower.radius}\n')
            else:
                file.write(f'{str(tower.lat)}, {str(tower.lon)}, {tower.radius}\n')

def print_results(radius_small: int, radius_large: int, epsilon: tuple[int, int], small_towers: set[Tower], large_towers: set[Tower], costs: float):
    print("\n" + "=" * 60)
    print("               FINALE ERGEBNIS-ZUSAMMENFASSUNG")
    print("-" * 60)
    print(f" BESTE RADIEN:                  S={radius_small}m, L={radius_large}m")
    print(f" BESTES EPSILON (X, Y):         ({epsilon[0]}m, {epsilon[1]}m)")
    print(f" Gebaute kleine Masten (Blau):  {len(small_towers)}")
    print(f" Gebaute große Masten (Lila):  {len(large_towers)}")
    print(f" FINALE MINIMALKOSTEN:          {costs:.2f} GE")
    print("=" * 60)

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
            towers_small, towers_large = problem.solve()
            
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

    print_results(best_t_1, best_t_2, best_epsilon, best_small_towers, best_large_towers, best_overall_costs)
    
    # OSM-Visualisierung für das absolut beste gefundene Set
    visualize_coverage_on_osm(best_problem, best_small_towers, best_large_towers)

if __name__ == "__main__":
    main()