import folium
from folium.plugins import FastMarkerCluster
# WICHTIG: Wir holen uns die Funktion direkt aus eurer plotting.py!
from plotting import utm_to_latlon

def visualize_coverage_on_osm(problem_instance, small_towers, large_towers, output_html="abdeckung_karte.html"):
    """
    Visualisiert Städte hocheffizient via Clustering und zeichnet die Masten 
    direkt aus den Berechnungsergebnissen auf einer interaktiven OSM-Karte.
    """
    print("\n[OSM] Generiere optimierte interaktive OSM-Abdeckungskarte...")
    
    # 1. OSM-Karte zentriert auf die Mitte Deutschlands erstellen
    m = folium.Map(location=[51.165691, 10.451526], zoom_start=6)
    
    # 2. Ebene für die Funkmasten anlegen
    fg_towers = folium.FeatureGroup(name="Funkmasten (Abdeckung)", show=True)
    
    # 3. STÄDTE SAMMELN UND OPTIMIERT CLUSTERN (Verhindert Browser-Lag)
    city_coords = []
    cities = problem_instance.cities
    print(f"[OSM] Bereite {len(cities)} Städte für das hocheffiziente Rendering vor...")
    
    for city in cities:
        lat, lon = city.lat, city.lon
        if lat is None or lon is None:
            lat, lon = utm_to_latlon((city.x, city.y))
        if lat is not None and lon is not None:
            city_coords.append([lat, lon])
            
    # FastMarkerCluster sorgt dafür, dass die Karte blitzschnell lädt
    fast_cluster = FastMarkerCluster(data=city_coords, name="Städte (Dynamisch gruppiert)")
    fast_cluster.add_to(m)

    # 4. MASTEN PLOTTEN (Direkt aus den Programmvariablen)
    print(f"[OSM] Plotte Masten (Klein: {len(small_towers)}, Groß: {len(large_towers)})...")
    
    # Kleine Masten zeichnen
    for tower in small_towers:
        lat, lon = tower.lat, tower.lon
        if lat is None or lon is None:
            lat, lon = utm_to_latlon((tower.x, tower.y))
            
        radius = tower.radius if (hasattr(tower, 'radius') and tower.radius is not None) else problem_instance.radius['small']
        
        # Funkradius (schön dezent transparent)
        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color="#2980B9",
            weight=1,
            fill=True,
            fill_color="#2980B9",
            fill_opacity=0.15,
            tooltip=f"<b>Kleiner Mast</b><br>Radius: {radius/1000} km"
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

    # Große Masten zeichnen
    for tower in large_towers:
        lat, lon = tower.lat, tower.lon
        if lat is None or lon is None:
            lat, lon = utm_to_latlon((tower.x, tower.y))
            
        radius = tower.radius if (hasattr(tower, 'radius') and tower.radius is not None) else problem_instance.radius['large']
        
        # Funkradius
        folium.Circle(
            location=[lat, lon],
            radius=radius,
            color="#8E44AD",
            weight=1,
            fill=True,
            fill_color="#8E44AD",
            fill_opacity=0.15,
            tooltip=f"<b>Großer Mast</b><br>Radius: {radius/1000} km"
        ).add_to(fg_towers)
        
        # Exakter Standortpunkt
        folium.CircleMarker(
            location=[lat, lon],
            radius=4,
            color="black",
            fill=True,
            fill_color="#8E44AD",
            fill_opacity=1.0
        ).add_to(fg_towers)

    # Ebenen-Steuerung hinzufügen
    fg_towers.add_to(m)
    folium.LayerControl().add_to(m)
    
    # Speichern
    m.save(output_html)
    print(f"[OSM] Erfolg! Die optimierte Karte wurde als '{output_html}' gespeichert.")