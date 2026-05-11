import folium
from models import City
from geo_utils import utm_to_latlon


def create_multi_layer_map(meta_cities, results_dict: dict, out_file: str = "deutschland_vergleich.html"):
    print("\nBaue interaktive Multi-Layer-Karte zusammen... Bitte warten.")
    m = folium.Map(location=[51.165691, 10.451526], zoom_start=6)

    for grid_density, data in results_dict.items():
        grid_km = grid_density // 1000
        costs = data['costs']
        t_small = data['towers_small']
        t_large = data['towers_large']
        city_status = data['city_status']

        layer_name = f"{grid_km}km Raster | Kosten: {costs:.1f} | Masten: {len(t_small)}x Klein, {len(t_large)}x Groß"
        is_visible = (grid_km == 10) # 10km ist standardmäßig aktiv
        fg = folium.FeatureGroup(name=layer_name, show=is_visible)

        for city_name, city_obj in meta_cities.items():
            is_covered = city_status[city_name]
            color = "green" if is_covered else "red"
            folium.CircleMarker(
                location=[city_obj.lat, city_obj.lon],
                radius=4, color=color, weight=1, fill=True, fill_color=color, fill_opacity=0.9,
                tooltip=f"<b>{city_name}</b><br>Abgedeckt im {grid_km}km Raster: {is_covered}"
            ).add_to(fg)

        for tower_utm in t_small:
            lat, lon = utm_to_latlon(tower_utm)
            folium.Circle(location=[lat, lon], radius=20000, color="blue", fill=True, fill_color="blue", fill_opacity=0.2).add_to(fg)
            folium.CircleMarker(location=[lat, lon], radius=3, color="black", weight=1, fill=True, fill_color="black", fill_opacity=1.0, tooltip="Mast (20km)").add_to(fg)

        for tower_utm in t_large:
            lat, lon = utm_to_latlon(tower_utm)
            folium.Circle(location=[lat, lon], radius=50000, color="purple", fill=True, fill_color="purple", fill_opacity=0.2).add_to(fg)
            folium.CircleMarker(location=[lat, lon], radius=3, color="black", weight=1, fill=True, fill_color="black", fill_opacity=1.0, tooltip="Großer Mast (50km)").add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(out_file)
    print(f"Fertig! Öffne '{out_file}' im Browser.")