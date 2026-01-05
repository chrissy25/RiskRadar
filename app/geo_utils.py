"""
Geospatial utilities for distance calculations and GeoJSON parsing.
"""
import math
import logging
from typing import List, Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
    
    Returns:
        Distance in kilometers
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def extract_coordinates_from_geometry(geometry: Dict[str, Any]) -> List[Tuple[float, float]]:
    """
    Extract all coordinate pairs (lat, lon) from a GeoJSON geometry.
    
    Supports: Point, MultiPoint, LineString, MultiLineString, Polygon, MultiPolygon
    
    Args:
        geometry: GeoJSON geometry object
    
    Returns:
        List of (lat, lon) tuples
    """
    coords = []
    geom_type = geometry.get("type", "")
    coordinates = geometry.get("coordinates", [])
    
    if not coordinates:
        return coords
    
    try:
        if geom_type == "Point":
            # coordinates = [lon, lat]
            lon, lat = coordinates[0], coordinates[1]
            coords.append((lat, lon))
            
        elif geom_type == "MultiPoint":
            # coordinates = [[lon, lat], [lon, lat], ...]
            for point in coordinates:
                lon, lat = point[0], point[1]
                coords.append((lat, lon))
                
        elif geom_type == "LineString":
            # coordinates = [[lon, lat], [lon, lat], ...]
            for point in coordinates:
                lon, lat = point[0], point[1]
                coords.append((lat, lon))
                
        elif geom_type == "MultiLineString":
            # coordinates = [[[lon, lat], ...], [[lon, lat], ...], ...]
            for line in coordinates:
                for point in line:
                    lon, lat = point[0], point[1]
                    coords.append((lat, lon))
                    
        elif geom_type == "Polygon":
            # coordinates = [[[lon, lat], ...], ...] (outer + holes)
            for ring in coordinates:
                for point in ring:
                    lon, lat = point[0], point[1]
                    coords.append((lat, lon))
                    
        elif geom_type == "MultiPolygon":
            # coordinates = [[[[lon, lat], ...], ...], ...]
            for polygon in coordinates:
                for ring in polygon:
                    for point in ring:
                        lon, lat = point[0], point[1]
                        coords.append((lat, lon))
        else:
            logger.warning(f"Unknown geometry type: {geom_type}")
            
    except (IndexError, TypeError, KeyError) as e:
        logger.error(f"Error extracting coordinates from {geom_type}: {e}")
    
    return coords


def min_distance_to_event(
    site_lat: float,
    site_lon: float,
    event_geometry: Dict[str, Any]
) -> float:
    """
    Calculate minimum distance from a site to any point in an event geometry.
    
    Args:
        site_lat, site_lon: Site coordinates
        event_geometry: GeoJSON geometry object
    
    Returns:
        Minimum distance in kilometers (or inf if no valid coordinates)
    """
    coords = extract_coordinates_from_geometry(event_geometry)
    
    if not coords:
        return float('inf')
    
    min_dist = float('inf')
    for event_lat, event_lon in coords:
        dist = haversine_distance(site_lat, site_lon, event_lat, event_lon)
        min_dist = min(min_dist, dist)
    
    return min_dist


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate that coordinates are within valid ranges.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        True if valid, False otherwise
    """
    return -90 <= lat <= 90 and -180 <= lon <= 180


def get_centroid(geometry: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """
    Get approximate centroid of a geometry (simple mean of coordinates).
    
    Args:
        geometry: GeoJSON geometry object
    
    Returns:
        (lat, lon) tuple or None if no valid coordinates
    """
    coords = extract_coordinates_from_geometry(geometry)
    
    if not coords:
        return None
    
    avg_lat = sum(lat for lat, lon in coords) / len(coords)
    avg_lon = sum(lon for lat, lon in coords) / len(coords)
    
    return (avg_lat, avg_lon)
