import matplotlib.pyplot as plt
from geopandas import GeoDataFrame
from load_germany import GER_lat_lon_plot
from models import *

def plot_map(city_coords: set[City] = None, tower_small_coords: set[Tower] = None, tower_large_coords: set[Tower] = None,
             radius_small: int = 0, radius_large: int = 0,
             grid: set[Point] = None, headline: str = 'Städte in Deutschland') -> None:
    """
     Plots the map of Germany including cities, towers, grid, etc.
     Note that the coords of any point can be given in either utm or lat/lon format
    :param radius_small:
    :param radius_large:
    :param headline: The headline of the map
    :param city_coords: List of tuples containing the coords of the cities or a list of datatype city.
    The coords can be given in either utm or lat/lon format
    :param tower_small_coords: List of tuples containing the coords of the small towers
    :param tower_large_coords: List of tuples containing the coords of the large towers
    :param grid: List of tuples containing coords of the grid points
    :return:
    """
    fig, ax = plt.subplots(figsize=(8, 10))
    GER_lat_lon_plot.plot(ax=ax, color="lightgray", edgecolor="black")

    def plot_points(points: set[Point], color: str = 'black', marker_size: int = 10) -> GeoDataFrame:
        # Check if the coords are in utm or lat/lon format
        # In lat/lon format the values are lower than 180. If this is not the case we first have to convert to lat/lon format
        shapely_points = []
        for point in points:
            if point.lat is None:
                lat, lon = utm_to_latlon((point.x, point.y))
                shapely_points.append(ShapelyPoint(lon, lat))
            else:
                shapely_points.append(ShapelyPoint(point.lon, point.lat))

        points_gdf = gpd.GeoDataFrame(geometry=shapely_points, crs="EPSG:4326")
        points_gdf.plot(ax=ax, color=color, markersize=marker_size)

        return points_gdf

    def plot_circles(points: set[Point], color: str, radius: int):
        points_gdf = plot_points(points, color)

        points_projected = points_gdf.to_crs(epsg=3035)
        circles = points_projected.buffer(radius)
        circles_gdf = gpd.GeoDataFrame(geometry=circles, crs='EPSG:3035')
        circles_gdf = circles_gdf.to_crs(epsg=4326)

        circles_gdf.plot(ax=ax, facecolor=f'lightcoral', edgecolor=color, alpha=0.3)

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