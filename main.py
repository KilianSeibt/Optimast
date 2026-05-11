from optimization import Meta, run_optimization
from visualization import create_multi_layer_map

def main():
    print("Starte Projekt...")
    meta = Meta()
    meta.create_cities()
    
    grid_densities_to_test = [1000]
    all_results = {}
    
    for density in grid_densities_to_test:
        all_results[density] = run_optimization(meta, density)
        
    create_multi_layer_map(meta_cities=meta.cities, results_dict=all_results)

if __name__ == '__main__':
    main()