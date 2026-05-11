from dataclasses import dataclass

@dataclass
class City:
    # Every city has the following attributes:
    # name, coords in lat/lon format, coords in utm format, covered
    name: str
    lat: float
    lon: float
    x: float
    y: float
    covered: bool
    