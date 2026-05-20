import folium
from folium.plugins import FastMarkerCluster
import geopandas as gpd
from shapely.geometry import Point as ShapelyPoint

def utm_to_latlon(point: tuple[float, float]) -> tuple[float, float]:
    """
    Converts a point from UTM (EPSG:32632) to lat/lon (EPSG:4326).
    """
    x, y = point

    gdf = gpd.GeoDataFrame(
        geometry=[ShapelyPoint(x, y)],
        crs="EPSG:32632"
    )

    gdf_latlon = gdf.to_crs(epsg=4326)

    lon, lat = gdf_latlon.geometry.iloc[0].x, gdf_latlon.geometry.iloc[0].y

    return lat, lon

def visualize_coverage_on_osm(problem_instance, test_results, output_html="abdeckung_karte.html", metadata=None):
    """
    Visualisiert Städte hocheffizient via Clustering, zeichnet die Masten 
    verschiedener Testdurchläufe als umschaltbare Ebenen.
    """
    print("\n[OSM] Generiere optimierte interaktive OSM-Abdeckungskarte...")
    
    # 1. OSM-Karte zentriert auf die Mitte Deutschlands erstellen
    m = folium.Map(location=[51.165691, 10.451526], zoom_start=6)
    
    # 2. STÄDTE SAMMELN UND OPTIMIERT CLUSTERN
    city_coords = []
    cities = problem_instance.cities
    print(f"[OSM] Bereite {len(cities)} Städte für das hocheffiziente Rendering vor...")
    
    for city in cities:
        lat, lon = city.lat, city.lon
        if lat is None or lon is None:
            lat, lon = utm_to_latlon((city.x, city.y))
        if lat is not None and lon is not None:
            city_coords.append([lat, lon])
            
    # Custom JavaScript Callback für kleine Punkte
    circle_callback = """
    function (row) {
        var marker = L.circleMarker([row[0], row[1]], {
            radius: 3,
            color: '#2C3E50',
            weight: 1,
            fillColor: '#34495E',
            fillOpacity: 1.0
        });
        return marker;
    }
    """
            
    fast_cluster = FastMarkerCluster(
        data=city_coords, 
        name="Städte (Dynamisch gruppiert)",
        callback=circle_callback
    )
    fast_cluster.add_to(m)

    # 3. MASTEN PLOTTEN (Als umschaltbare Ebenen)
    print(f"[OSM] Erstelle {len(test_results)} umschaltbare Ebenen für die besten Tests...")
    
    for i, test in enumerate(test_results):
        layer_name = test['name']
        small_towers = test['small_towers']
        large_towers = test['large_towers']
        
        # Nur das allerbeste Ergebnis (Index 0) ist beim Start sichtbar, sonst überlagert sich alles
        fg_towers = folium.FeatureGroup(name=layer_name, show=(i == 0))
        
        # Kleine Masten zeichnen
        for tower in small_towers:
            lat, lon = tower.lat, tower.lon
            if lat is None or lon is None:
                lat, lon = utm_to_latlon((tower.x, tower.y))
                
            radius = tower.radius if (hasattr(tower, 'radius') and tower.radius is not None) else problem_instance.radius['small']
            
            folium.Circle(
                location=[lat, lon], radius=radius, color="#2980B9", weight=1,
                fill=True, fill_color="#2980B9", fill_opacity=0.15,
                tooltip=f"<b>Kleiner Mast</b><br>Radius: {radius/1000} km"
            ).add_to(fg_towers)
            
            folium.CircleMarker(
                location=[lat, lon], radius=3, color="black",
                fill=True, fill_color="#2980B9", fill_opacity=1.0
            ).add_to(fg_towers)

        # Große Masten zeichnen
        for tower in large_towers:
            lat, lon = tower.lat, tower.lon
            if lat is None or lon is None:
                lat, lon = utm_to_latlon((tower.x, tower.y))
                
            radius = tower.radius if (hasattr(tower, 'radius') and tower.radius is not None) else problem_instance.radius['large']
            
            folium.Circle(
                location=[lat, lon], radius=radius, color="#8E44AD", weight=1,
                fill=True, fill_color="#8E44AD", fill_opacity=0.15,
                tooltip=f"<b>Großer Mast</b><br>Radius: {radius/1000} km"
            ).add_to(fg_towers)
            
            folium.CircleMarker(
                location=[lat, lon], radius=4, color="black",
                fill=True, fill_color="#8E44AD", fill_opacity=1.0
            ).add_to(fg_towers)

        # Ebene zur Karte hinzufügen
        fg_towers.add_to(m)

    # Das Ebenen-Menü (LayerControl) - ausgeklappt lassen für bessere Sichtbarkeit!
    folium.LayerControl(collapsed=False).add_to(m)
    
    # --- DAS SCHWEBENDE INFO-DASHBOARD ---
    if metadata:
        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 320px; height: auto; 
                    background-color: rgba(255, 255, 255, 0.95); border: 2px solid #2C3E50; z-index: 9999; font-family: Arial, sans-serif; font-size: 14px;
                    padding: 15px; border-radius: 8px; box-shadow: 4px 4px 10px rgba(0,0,0,0.3);">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #2C3E50; text-align: center;"><b>Bester Testlauf (Details)</b></h4>
            <b>Modus:</b> {metadata.get('mode', 'N/A')}<br>
            <b>Grid-Dichte:</b> {metadata.get('grid_density', 0):,} m<br>
            <b>Epsilon (X, Y):</b> ({metadata.get('epsilon')[0]} m, {metadata.get('epsilon')[1]} m)<br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px solid #ccc;">
            <b>Radius S (Blau):</b> {metadata.get('t_1', 0):,} m<br>
            <b>Radius L (Lila):</b> {metadata.get('t_2', 0):,} m<br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px solid #ccc;">
            <b style="color: #c0392b; font-size: 16px;">Gesamtkosten: {metadata.get('costs', 0):.2f} GE</b>
            <hr style="margin: 8px 0; border: 0; border-top: 1px solid #ccc;">
            <i style="font-size: 12px; color: #7f8c8d;">Tipp: Oben rechts im Menü kannst du verschiedene Durchläufe vergleichen!</i>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
    
    # Speichern
    m.save(output_html)
    print(f"[OSM] Erfolg! Die optimierte Karte wurde als '{output_html}' gespeichert.")