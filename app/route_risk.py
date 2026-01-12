#!/usr/bin/env python3
"""
Route Risk Calculation Module for RiskRadar

Handles route-based risk calculations:
- Individual risk per waypoint
- Accumulated risk along route segments
- Aggregated risk summaries for routes

Author: RiskRadar Team
Date: 2025-01-12
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

from geo_utils import haversine_distance

logger = logging.getLogger(__name__)


@dataclass
class RoutePoint:
    """Represents a waypoint on a route with calculated risks."""
    order: int
    name: str
    lat: float
    lon: float
    fire_risk: float = 0.0
    quake_risk: float = 0.0
    flood_risk: float = 0.0  # Placeholder for future implementation
    combined_risk: float = 0.0
    distance_from_prev: float = 0.0  # km from previous waypoint
    accumulated_risk: float = 0.0  # Cumulative risk up to this point


@dataclass
class Route:
    """Represents a complete route with multiple waypoints."""
    route_id: str
    points: List[RoutePoint] = field(default_factory=list)
    total_distance: float = 0.0
    aggregated_fire_risk: float = 0.0
    aggregated_quake_risk: float = 0.0
    aggregated_combined_risk: float = 0.0
    dominant_risk_category: str = ""
    
    def add_point(self, point: RoutePoint):
        """Add a waypoint to the route."""
        self.points.append(point)
        self.points.sort(key=lambda p: p.order)
    
    def get_risk_label(self) -> str:
        """Get risk level label based on aggregated combined risk."""
        if self.aggregated_combined_risk >= 75:
            return "Very High"
        elif self.aggregated_combined_risk >= 50:
            return "High"
        elif self.aggregated_combined_risk >= 25:
            return "Medium"
        else:
            return "Low"
    
    def get_risk_color(self) -> str:
        """Get color for risk level."""
        if self.aggregated_combined_risk >= 75:
            return "#dc3545"  # Red
        elif self.aggregated_combined_risk >= 50:
            return "#fd7e14"  # Orange
        elif self.aggregated_combined_risk >= 25:
            return "#ffc107"  # Yellow
        else:
            return "#28a745"  # Green


def load_routes_from_csv(routes_path: Path) -> List[Route]:
    """
    Load route definitions from CSV file.
    
    Expected CSV format:
        route_id,order,name,lat,lon
        A,1,Hamburg,53.5511,9.9937
        A,2,Mumbai,19.0760,72.8777
    
    Args:
        routes_path: Path to routes CSV file
        
    Returns:
        List of Route objects
    """
    if not routes_path.exists():
        logger.warning(f"Routes file not found: {routes_path}")
        return []
    
    df = pd.read_csv(routes_path)
    required_cols = ['route_id', 'order', 'name', 'lat', 'lon']
    
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Routes CSV missing required column: {col}")
    
    routes_dict: Dict[str, Route] = {}
    
    for _, row in df.iterrows():
        route_id = str(row['route_id'])
        
        if route_id not in routes_dict:
            routes_dict[route_id] = Route(route_id=route_id)
        
        point = RoutePoint(
            order=int(row['order']),
            name=str(row['name']),
            lat=float(row['lat']),
            lon=float(row['lon'])
        )
        routes_dict[route_id].add_point(point)
    
    logger.info(f"Loaded {len(routes_dict)} routes from {routes_path}")
    return list(routes_dict.values())


def calculate_route_distances(route: Route) -> Route:
    """
    Calculate distances between waypoints in a route.
    
    Args:
        route: Route object with points
        
    Returns:
        Updated Route with distances calculated
    """
    total_distance = 0.0
    
    for i, point in enumerate(route.points):
        if i == 0:
            point.distance_from_prev = 0.0
        else:
            prev = route.points[i - 1]
            dist = haversine_distance(prev.lat, prev.lon, point.lat, point.lon)
            point.distance_from_prev = dist
            total_distance += dist
    
    route.total_distance = total_distance
    return route


def calculate_accumulated_risk(route: Route) -> Route:
    """
    Calculate accumulated risk along the route.
    
    Uses probability formula: P(at least one event) = 1 - ∏(1 - P_i)
    
    Args:
        route: Route with individual risks calculated
        
    Returns:
        Updated Route with accumulated risks
    """
    # Accumulated fire risk
    fire_probs = [p.fire_risk / 100 for p in route.points]
    route.aggregated_fire_risk = (1 - np.prod([1 - p for p in fire_probs])) * 100
    
    # Accumulated quake risk
    quake_probs = [p.quake_risk / 100 for p in route.points]
    route.aggregated_quake_risk = (1 - np.prod([1 - p for p in quake_probs])) * 100
    
    # Accumulated combined risk
    combined_probs = [p.combined_risk / 100 for p in route.points]
    route.aggregated_combined_risk = (1 - np.prod([1 - p for p in combined_probs])) * 100
    
    # Determine dominant risk category
    if route.aggregated_fire_risk > route.aggregated_quake_risk:
        route.dominant_risk_category = "Feuer"
    else:
        route.dominant_risk_category = "Erdbeben"
    
    # Calculate per-point accumulated risk
    cumulative = 0.0
    for point in route.points:
        prob = point.combined_risk / 100
        cumulative = 1 - (1 - cumulative) * (1 - prob)
        point.accumulated_risk = cumulative * 100
    
    return route


def assign_risks_to_route(
    route: Route,
    predictions_df: pd.DataFrame
) -> Route:
    """
    Assign risk scores to route waypoints from predictions DataFrame.
    
    Args:
        route: Route with waypoints
        predictions_df: DataFrame with site predictions
        
    Returns:
        Updated Route with risks assigned to waypoints
    """
    for point in route.points:
        # Try to find matching prediction by name
        match = predictions_df[predictions_df['site_name'].str.lower() == point.name.lower()]
        
        if not match.empty:
            row = match.iloc[0]
            point.fire_risk = row.get('fire_risk_score', 0.0)
            point.quake_risk = row.get('quake_risk_score', 0.0)
            point.combined_risk = row.get('combined_risk_score', 0.0)
            point.flood_risk = 0.0  # Placeholder
        else:
            # Find nearest location by coordinates
            min_dist = float('inf')
            best_match = None
            
            for _, row in predictions_df.iterrows():
                dist = haversine_distance(
                    point.lat, point.lon,
                    row['lat'], row['lon']
                )
                if dist < min_dist:
                    min_dist = dist
                    best_match = row
            
            if best_match is not None and min_dist < 100:  # Within 100km
                point.fire_risk = best_match.get('fire_risk_score', 0.0)
                point.quake_risk = best_match.get('quake_risk_score', 0.0)
                point.combined_risk = best_match.get('combined_risk_score', 0.0)
                point.flood_risk = 0.0
                logger.info(f"  Matched {point.name} to {best_match['site_name']} ({min_dist:.1f}km)")
            else:
                logger.warning(f"  No prediction found for waypoint: {point.name}")
    
    return route


def process_all_routes(
    routes: List[Route],
    predictions_df: pd.DataFrame
) -> List[Route]:
    """
    Process all routes: assign risks, calculate distances and accumulations.
    
    Args:
        routes: List of Route objects
        predictions_df: DataFrame with site predictions
        
    Returns:
        List of fully processed Route objects
    """
    processed = []
    
    for route in routes:
        logger.info(f"Processing route {route.route_id}...")
        route = assign_risks_to_route(route, predictions_df)
        route = calculate_route_distances(route)
        route = calculate_accumulated_risk(route)
        processed.append(route)
        
        logger.info(f"  Route {route.route_id}: {len(route.points)} waypoints, "
                   f"{route.total_distance:.0f}km, "
                   f"Combined Risk: {route.aggregated_combined_risk:.1f}%")
    
    return processed


def routes_to_dataframe(routes: List[Route]) -> pd.DataFrame:
    """
    Convert routes to a summary DataFrame.
    
    Args:
        routes: List of processed Route objects
        
    Returns:
        DataFrame with route summaries
    """
    records = []
    
    for route in routes:
        for point in route.points:
            records.append({
                'route_id': route.route_id,
                'order': point.order,
                'waypoint_name': point.name,
                'lat': point.lat,
                'lon': point.lon,
                'fire_risk': point.fire_risk,
                'quake_risk': point.quake_risk,
                'flood_risk': point.flood_risk,
                'combined_risk': point.combined_risk,
                'distance_from_prev_km': point.distance_from_prev,
                'accumulated_risk': point.accumulated_risk,
                'route_total_distance_km': route.total_distance,
                'route_aggregated_risk': route.aggregated_combined_risk,
                'route_risk_label': route.get_risk_label(),
                'route_dominant_category': route.dominant_risk_category
            })
    
    return pd.DataFrame(records)


if __name__ == "__main__":
    # Test with sample data
    logging.basicConfig(level=logging.INFO)
    
    # Create sample route
    test_route = Route(route_id="Test")
    test_route.add_point(RoutePoint(1, "Start", 52.52, 13.405))
    test_route.add_point(RoutePoint(2, "Middle", 48.8566, 2.3522))
    test_route.add_point(RoutePoint(3, "End", 41.9028, 12.4964))
    
    # Assign mock risks
    for i, point in enumerate(test_route.points):
        point.fire_risk = 20 + i * 15
        point.quake_risk = 10 + i * 20
        point.combined_risk = 25 + i * 15
    
    # Calculate
    test_route = calculate_route_distances(test_route)
    test_route = calculate_accumulated_risk(test_route)
    
    print(f"\nRoute: {test_route.route_id}")
    print(f"Total Distance: {test_route.total_distance:.0f} km")
    print(f"Aggregated Combined Risk: {test_route.aggregated_combined_risk:.1f}%")
    print(f"Risk Level: {test_route.get_risk_label()}")
    
    for p in test_route.points:
        print(f"  {p.order}. {p.name}: Fire={p.fire_risk:.0f}%, "
              f"Quake={p.quake_risk:.0f}%, Accumulated={p.accumulated_risk:.1f}%")
