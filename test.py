import unittest

import pandas as pd
import folium

class Test(unittest.TestCase):
    def test_1(self):

        # 1. Daten laden (z. B. die Simplemaps World Cities Datei) print("Lese Daten ein...") # WICHTIG: Ersetze 'worldcities.csv' mit dem echten Dateinamen deiner Liste!
        df = pd.read_csv('input_files/worldcities.csv')

        # 2. Daten filtern: Nur Paraguay UND mehr als 10.000 Einwohner # Wir stellen sicher, dass die Population als Zahl gelesen wird df['population'] = pd.to_numeric(df['population'], errors='coerce')
        country = 'Paraguay'

        df = df[(df['country'] == country) & (df['population'] > 30_000)].dropna(subset=['lat', 'lng', 'population'])


        # 3. OpenStreetMap Karte initialisieren
        # Die Koordinaten (-23.4, -58.4) zentrieren die Karte ungefähr auf Paraguay

        m = folium.Map(location=[-23.4425, -58.4438], zoom_start=6)

        # 4. Städte in die Karte eintragen
        print("Generiere Marker auf der Karte...")
        for idx, row in df.iterrows():
             folium.CircleMarker(
                 location=[row['lat'], row['lng']],
                 radius=5, # Etwas größer, da es weniger Städte sind als in den USA
                 popup=f"<b>{row['city']}</b><br>Einwohner: {int(row['population']):,}",
                 color='#2ca02c', # Ein schönes Grün zur Abwechslung
                 fill=True,
                 fill_color='#2ca02c',
                 fill_opacity=0.8
             ).add_to(m)

        with open('input_files/cities_paraguay.txt', 'w') as file:
            for idx, row in df.iterrows():
                file.write(f"{row['city']}, {row['lat']}, {row['lng']}\n")

        # 5. Karte abspeichern
        output_file = f'{country}_cities_map.html'
        m.save(output_file)
