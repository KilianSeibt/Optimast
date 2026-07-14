import folium
from folium.plugins import FastMarkerCluster
from models import *

"""
This file does the plotting of the Open-Street-Map-coverage on a map.
No big logic happening here^^ Just some visualization stuff
"""

def visualize_coverage_on_osm(country_datas: list[CountryData], cities: set[City], radius: tuple[int, int], towers: tuple[set[Tower], set[Tower]]):
    """
    Visualisiert Städte hocheffizient via Clustering und zeichnet die Masten
    direkt aus den Berechnungsergebnissen auf einer interaktiven OSM-Karte.
    """

    # 1. OSM-Karte zentriert auf die Mitte Deutschlands erstellen
    m = folium.Map(location=[51.165691, 10.451526], zoom_start=6)

    # 2. Ebene für die Funkmasten anlegen
    fg_towers = folium.FeatureGroup(name="Funkmasten (Abdeckung)", show=True)

    city_coords = [[city.lat, city.lon] for city in cities]

    # FastMarkerCluster sorgt dafür, dass die Karte blitzschnell lädt
    fast_cluster = FastMarkerCluster(data=city_coords, name="Städte (Dynamisch gruppiert)")
    fast_cluster.add_to(m)

    def draw_circles(circles: set[Tower], rad: int):
        for circle in circles:
            lat, lon = circle.lat, circle.lon
            if lat is None or lon is None:
                lat, lon = utm_to_latlon((circle.x, circle.y), epsg=country_datas[0].epsg)

            # Funkradius (schön dezent transparent)
            folium.Circle(
                location=[lat, lon],
                radius=rad,
                color="#2980B9",
                weight=1,
                fill=True,
                fill_color="#2980B9",
                fill_opacity=0.15,
                tooltip=f"<b>Kleiner Mast</b><br>Radius: {rad / 1000} km"
            ).add_to(fg_towers)

            # Exakter Standortpunkt
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                color="black",
                fill=True,
                fill_color="#2980B9",
                fill_opacity=1.0
            ).add_to(fg_towers)

    draw_circles(towers[0], radius[0])
    draw_circles(towers[1], radius[1])

    # Ebenen-Steuerung hinzufügen
    fg_towers.add_to(m)
    folium.LayerControl().add_to(m)

    # Speichern
    file_name = f"osm_coverage_Europe_{radius[0]}_{radius[1]}.html"
    m.save(file_name)