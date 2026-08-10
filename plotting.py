import matplotlib.pyplot as plt
from geopandas import GeoDataFrame
from models import *

def plot_map(country_datas: list[CountryData],
             cities: set[City]|None = None,
             radius: tuple[int, int]|None = None,
             towers: tuple[set[Tower], set[Tower]]|None = None,
             grid: set[Point]|None = None,
             headline: str = 'To determine',
             unit: str = 'latlon') -> None:
    """
     Plots the map including cities, towers, grid, etc.
     Note that the coords of any point can be given in either utm or lat/lon format
    :param country_datas: List of CountryData objects to plot
    :param cities: Set of City objects to plot
    :param radius: Tuple of (radius_small, radius_large) for tower circles
    :param towers: Tuple of (small_towers, large_towers) containing sets of Tower objects
    :param grid: Set of grid points to plot
    :param headline: The headline of the map
    :param unit: Either 'latlon' or 'utm' for coordinate format
    :return: None
    """
    # Extract tuple parameters
    radius_small, radius_large = radius if radius else (None, None)
    tower_small_coords, tower_large_coords = towers if towers else (None, None)
    city_coords = cities

    fig, ax = plt.subplots(figsize=(8, 10))
    for country_data in country_datas:
        if unit == 'latlon':
            country_map = country_data.latlon_plot
        elif unit == 'utm':
            country_map = country_data.utm_plot
        else:
            raise ValueError
        country_map.plot(ax=ax, color="lightgray", edgecolor="black")

    def plot_points(points: set[Point], color: str = 'black', marker_size: int = 10) -> GeoDataFrame:
        # Check if the coords are in utm or lat/lon format
        # In lat/lon format the values are lower than 180. If this is not the case we first have to convert to lat/lon format
        shapely_points = []
        for point in points:
            if point.lat is None:
                lat, lon = utm_to_latlon((point.x, point.y), country_data.epsg)
                shapely_points.append(ShapelyPoint(lon, lat))
            else:
                shapely_points.append(ShapelyPoint(point.lon, point.lat))

        points_gdf = gpd.GeoDataFrame(geometry=shapely_points, crs="EPSG:4326")
        if unit == 'utm':
            crs = country_data.utm_plot.crs
            assert crs is not None
            points_gdf = points_gdf.to_crs(crs)
        points_gdf.plot(ax=ax, color=color, markersize=marker_size)

        return points_gdf

    def plot_circles(points: set[Point], color: str, r: int):
        points_gdf = plot_points(points, color)

        points_projected = points_gdf.to_crs(epsg=country_data.epsg)
        circles = points_projected.buffer(r)
        circles_gdf = gpd.GeoDataFrame(geometry=circles, crs=f'EPSG:{country_data.epsg}')
        circles_gdf = circles_gdf.to_crs(epsg=4326)
        circles_gdf.plot(ax=ax, facecolor='lightcoral', edgecolor=color, alpha=0.3)

    if city_coords:
        plot_points(city_coords)

    if tower_small_coords:
        plot_circles(tower_small_coords, 'blue', radius_small)

    if tower_large_coords:
        plot_circles(tower_large_coords, 'red', radius_large)

    if grid:
        plot_points(grid, 'red', 1)


    plt.title(headline)
    plt.show()