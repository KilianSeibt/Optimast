import matplotlib.pyplot as plt

def plot_radii(results):
    
    
    t_1_values = [res['t_1'] for res in results]
    t_2_values = [res['t_2'] for res in results]
    costs = [res['cost'] for res in results]

    # Center plot on last result (minimal cost)
    center_t1 = results[-1]['t_1']
    center_t2 = results[-1]['t_2']

    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(t_1_values, t_2_values, c=costs, cmap='coolwarm_r', s=100)
    plt.colorbar(scatter, label='Kosten')
    plt.xlabel('Radius t_1 (small)')
    plt.ylabel('Radius t_2 (large)')
    plt.title('Kosten in Abhängigkeit von den Radien t_1 und t_2')
    plt.grid()

    # Set plot limits to center on the last point
    xlim = plt.xlim()
    ylim = plt.ylim()
    x_range = max(abs(center_t1 - xlim[0]), abs(center_t1 - xlim[1]))
    y_range = max(abs(center_t2 - ylim[0]), abs(center_t2 - ylim[1]))
    plt.xlim(center_t1 - x_range, center_t1 + x_range)
    plt.ylim(center_t2 - y_range, center_t2 + y_range)

    plt.show()