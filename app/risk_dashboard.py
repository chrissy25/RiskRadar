#!/usr/bin/env python3
"""
Risk Dashboard Generator for RiskRadar

Creates an interactive HTML dashboard with:
- Left sidebar with route list, location profile, and charts
- Main map with route polylines and location markers
- Historical data toggle layers
- Aggregated risk popups

Author: RiskRadar Team
Date: 2025-01-12
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
import logging
import json
from datetime import datetime, timedelta

import folium
from folium import plugins

from route_risk import Route, RoutePoint, load_routes_from_csv, process_all_routes

logger = logging.getLogger(__name__)


# ==================== SIDEBAR HTML GENERATION ====================

def generate_route_list_html(routes: List[Route]) -> str:
    """Generate HTML for the route list in sidebar."""
    items = []
    
    for route in routes:
        # Determine border color based on risk
        color = route.get_risk_color()
        risk_label = route.get_risk_label()
        
        # Risk category icons
        fire_icon = "🔥" if route.aggregated_fire_risk > 25 else ""
        quake_icon = "🌍" if route.aggregated_quake_risk > 25 else ""
        flood_icon = "💧"  # Placeholder
        
        # Route summary
        start = route.points[0].name if route.points else "?"
        end = route.points[-1].name if route.points else "?"
        
        item_html = f'''
        <div class="route-item" style="border-left: 4px solid {color};" onclick="selectRoute('{route.route_id}')">
            <div class="route-header">
                <strong>Route {route.route_id}: {start} - {end}</strong>
                <span class="route-icons">{fire_icon}{quake_icon}{flood_icon}</span>
            </div>
            <div class="route-risk">
                Risk: {risk_label} ({route.aggregated_combined_risk:.0f}%) - {route.dominant_risk_category}
            </div>
        </div>
        '''
        items.append(item_html)
    
    return '\n'.join(items)


def generate_location_profile_html(location_name: str = "Select Location",
                                  fire_risk: float = 0,
                                  quake_risk: float = 0,
                                  flood_risk: float = 0) -> str:
    """Generate HTML for location risk profile with bar charts."""
    return f'''
    <div class="profile-section">
        <h4>Standort-Risikoprofil</h4>
        <div class="profile-location">
            <strong>Standort:</strong> <span id="profile-name">{location_name}</span>
        </div>
        <div class="profile-stats">
            <div>Feuer: <span id="profile-fire">{fire_risk:.0f}%</span></div>
            <div>Erdbeben: <span id="profile-quake">{quake_risk:.0f}%</span></div>
            <div>Hochwasser: <span id="profile-flood">{flood_risk:.0f}%</span></div>
        </div>
        <div class="bar-chart">
            <div class="bar-container">
                <div class="bar bar-fire" id="bar-fire" style="width: {fire_risk}%;"></div>
            </div>
            <div class="bar-container">
                <div class="bar bar-quake" id="bar-quake" style="width: {quake_risk}%;"></div>
            </div>
            <div class="bar-container">
                <div class="bar bar-flood" id="bar-flood" style="width: {flood_risk}%;"></div>
            </div>
            <div class="bar-labels">
                <span>Feuer</span>
                <span>Erdbeben</span>
                <span>Hochwasser</span>
            </div>
        </div>
    </div>
    '''


def generate_forecast_chart_html() -> str:
    """Generate HTML for the forecast/analysis chart placeholder."""
    return '''
    <div class="forecast-section">
        <h4>Prognose & Analyse</h4>
        <div class="chart-legend">
            <span class="legend-fire">■ Feuer</span>
            <span class="legend-analysis">■ Analyse</span>
        </div>
        <canvas id="forecast-chart" width="250" height="120"></canvas>
    </div>
    '''


def generate_sidebar_html(routes: List[Route]) -> str:
    """Generate complete sidebar HTML."""
    route_list = generate_route_list_html(routes)
    location_profile = generate_location_profile_html()
    forecast_chart = generate_forecast_chart_html()
    
    return f'''
    <div id="sidebar">
        <div class="sidebar-header">
            <h2>Logistik-Risikobewertung</h2>
            <h3>Dashboard</h3>
        </div>
        
        <div class="sidebar-section">
            <h4>Suche & Filter</h4>
            <input type="text" id="search-box" placeholder="Suchort, Lokation / Routen..." 
                   onkeyup="filterRoutes(this.value)">
        </div>
        
        <div class="sidebar-section">
            <h4>Aktuelle Routen-Risiken</h4>
            <div id="route-list">
                {route_list}
            </div>
        </div>
        
        {location_profile}
        {forecast_chart}
    </div>
    '''


# ==================== MAP GENERATION ====================

def create_route_polylines(map_obj: folium.Map, route: Route) -> None:
    """Add route polylines to the map."""
    if len(route.points) < 2:
        return
    
    # Create feature group for route
    route_group = folium.FeatureGroup(name=f"Route {route.route_id}")
    
    # Draw lines between consecutive points
    for i in range(len(route.points) - 1):
        p1 = route.points[i]
        p2 = route.points[i + 1]
        
        # Line color based on segment risk (average of two endpoints)
        avg_risk = (p1.combined_risk + p2.combined_risk) / 2
        if avg_risk >= 75:
            line_color = "#dc3545"
        elif avg_risk >= 50:
            line_color = "#fd7e14"
        elif avg_risk >= 25:
            line_color = "#ffc107"
        else:
            line_color = "#28a745"
        
        # Draw polyline
        folium.PolyLine(
            locations=[[p1.lat, p1.lon], [p2.lat, p2.lon]],
            color=line_color,
            weight=4,
            opacity=0.8,
            popup=f"Segment {p1.name} → {p2.name}<br>"
                  f"Distance: {p2.distance_from_prev:.0f} km<br>"
                  f"Avg Risk: {avg_risk:.1f}%"
        ).add_to(route_group)
    
    route_group.add_to(map_obj)


def create_waypoint_markers(map_obj: folium.Map, route: Route) -> None:
    """Add numbered waypoint markers to the map."""
    for point in route.points:
        # Marker color
        if point.combined_risk >= 75:
            color = "red"
        elif point.combined_risk >= 50:
            color = "orange"
        elif point.combined_risk >= 25:
            color = "beige"
        else:
            color = "green"
        
        # Popup content
        popup_html = f'''
        <div style="width: 250px; font-family: Arial, sans-serif;">
            <h4 style="margin: 0 0 10px 0;">{point.name}</h4>
            <hr>
            <div style="margin: 5px 0;">
                <strong>🔥 Fire Risk:</strong> {point.fire_risk:.1f}%
                <div style="background: #ffcccc; height: 8px; border-radius: 4px;">
                    <div style="background: #dc3545; height: 8px; width: {point.fire_risk}%; border-radius: 4px;"></div>
                </div>
            </div>
            <div style="margin: 5px 0;">
                <strong>🌍 Quake Risk:</strong> {point.quake_risk:.1f}%
                <div style="background: #cce5ff; height: 8px; border-radius: 4px;">
                    <div style="background: #0d6efd; height: 8px; width: {point.quake_risk}%; border-radius: 4px;"></div>
                </div>
            </div>
            <hr>
            <div style="margin: 5px 0;">
                <strong>⚠️ Combined:</strong> {point.combined_risk:.1f}%<br>
                <strong>📈 Accumulated:</strong> {point.accumulated_risk:.1f}%
            </div>
            <small>Route {route.route_id} - Waypoint {point.order}</small>
        </div>
        '''
        
        # Add marker with number
        folium.Marker(
            location=[point.lat, point.lon],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{point.order}. {point.name}: {point.combined_risk:.0f}%",
            icon=folium.Icon(color=color, icon="info-sign")
        ).add_to(map_obj)


def add_historical_layer(
    map_obj: folium.Map,
    firms_df: pd.DataFrame,
    usgs_df: pd.DataFrame,
    days_back: int = 30
) -> None:
    """Add historical fire and earthquake layers to the map."""
    
    # Historical Fires Layer
    fire_group = folium.FeatureGroup(name="🔥 Historische Feuer", show=False)
    
    if not firms_df.empty:
        # Filter to recent data
        cutoff_date = pd.Timestamp.now(tz='UTC') - timedelta(days=days_back)
        recent_fires = firms_df[firms_df['acq_date'] > cutoff_date].head(500)
        
        # Add marker cluster for fires
        fire_cluster = plugins.MarkerCluster(name="Fire Detections")
        
        for _, row in recent_fires.iterrows():
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=3,
                color='red',
                fill=True,
                fillColor='red',
                fillOpacity=0.6,
                popup=f"Fire Detection<br>Date: {row['acq_date']}<br>"
                      f"Brightness: {row.get('brightness', 'N/A')}"
            ).add_to(fire_cluster)
        
        fire_cluster.add_to(fire_group)
    
    fire_group.add_to(map_obj)
    
    # Historical Earthquakes Layer
    quake_group = folium.FeatureGroup(name="🌍 Historische Erdbeben", show=False)
    
    if not usgs_df.empty:
        cutoff_date = pd.Timestamp.now(tz='UTC') - timedelta(days=days_back)
        recent_quakes = usgs_df[usgs_df['time'] > cutoff_date].head(200)
        
        for _, row in recent_quakes.iterrows():
            mag = row.get('mag', 3.0)
            radius = max(3, mag * 2)  # Scale by magnitude
            
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=radius,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.5,
                popup=f"Earthquake<br>Magnitude: {mag}<br>Date: {row['time']}"
            ).add_to(quake_group)
    
    quake_group.add_to(map_obj)


def add_legend_html(map_obj: folium.Map) -> None:
    """Add legend to the map."""
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 180px;
                background: white; border: 2px solid #ccc; z-index: 9999;
                padding: 10px; font-size: 13px; border-radius: 5px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0;">Risk Level</h4>
        <p style="margin: 3px 0;"><span style="color: #dc3545;">●</span> Very High (≥75%)</p>
        <p style="margin: 3px 0;"><span style="color: #fd7e14;">●</span> High (50-75%)</p>
        <p style="margin: 3px 0;"><span style="color: #ffc107;">●</span> Medium (25-50%)</p>
        <p style="margin: 3px 0;"><span style="color: #28a745;">●</span> Low (<25%)</p>
        <hr style="margin: 8px 0;">
        <small>🔥 Fire | 🌍 Quake | ⚠️ Combined</small>
    </div>
    '''
    map_obj.get_root().html.add_child(folium.Element(legend_html))


# ==================== CSS STYLES ====================

DASHBOARD_CSS = '''
<style>
* {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0;
    font-family: 'Segoe UI', Arial, sans-serif;
    display: flex;
}

#sidebar {
    width: 320px;
    height: 100vh;
    background: #f8f9fa;
    border-right: 1px solid #dee2e6;
    overflow-y: auto;
    position: fixed;
    left: 0;
    top: 0;
    z-index: 10000;
    padding: 15px;
}

#map-container {
    margin-left: 320px;
    width: calc(100% - 320px);
    height: 100vh;
}

.sidebar-header h2 {
    margin: 0;
    font-size: 1.3em;
    color: #333;
}

.sidebar-header h3 {
    margin: 5px 0 15px 0;
    font-size: 1em;
    color: #666;
    font-weight: normal;
}

.sidebar-section {
    margin-bottom: 20px;
}

.sidebar-section h4 {
    margin: 0 0 10px 0;
    font-size: 0.95em;
    color: #333;
    border-bottom: 1px solid #dee2e6;
    padding-bottom: 5px;
}

#search-box {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 0.9em;
}

.route-item {
    background: white;
    padding: 10px;
    margin-bottom: 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background 0.2s;
}

.route-item:hover {
    background: #e9ecef;
}

.route-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.route-icons {
    font-size: 1.1em;
}

.route-risk {
    font-size: 0.85em;
    color: #666;
    margin-top: 5px;
}

.profile-section, .forecast-section {
    background: white;
    padding: 12px;
    border-radius: 4px;
    margin-bottom: 15px;
}

.profile-section h4, .forecast-section h4 {
    margin: 0 0 10px 0;
    font-size: 0.95em;
}

.profile-stats {
    font-size: 0.85em;
    margin: 10px 0;
}

.bar-chart {
    margin-top: 15px;
}

.bar-container {
    height: 20px;
    background: #e9ecef;
    border-radius: 4px;
    margin-bottom: 5px;
    overflow: hidden;
}

.bar {
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s;
}

.bar-fire { background: #dc3545; }
.bar-quake { background: #fd7e14; }
.bar-flood { background: #28a745; }

.bar-labels {
    display: flex;
    justify-content: space-between;
    font-size: 0.75em;
    color: #666;
    margin-top: 5px;
}

.chart-legend {
    font-size: 0.8em;
    margin-bottom: 10px;
}

.legend-fire { color: #dc3545; margin-right: 15px; }
.legend-analysis { color: #28a745; }

#forecast-chart {
    width: 100%;
    background: #f8f9fa;
    border-radius: 4px;
}
</style>
'''


# ==================== JAVASCRIPT ====================

DASHBOARD_JS = '''
<script>
function selectRoute(routeId) {
    console.log('Selected route:', routeId);
    // TODO: Highlight route on map, update profile
}

function filterRoutes(query) {
    const items = document.querySelectorAll('.route-item');
    const lowerQuery = query.toLowerCase();
    
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(lowerQuery) ? 'block' : 'none';
    });
}

function updateLocationProfile(name, fire, quake, flood) {
    document.getElementById('profile-name').textContent = name;
    document.getElementById('profile-fire').textContent = fire.toFixed(0) + '%';
    document.getElementById('profile-quake').textContent = quake.toFixed(0) + '%';
    document.getElementById('profile-flood').textContent = flood.toFixed(0) + '%';
    
    document.getElementById('bar-fire').style.width = fire + '%';
    document.getElementById('bar-quake').style.width = quake + '%';
    document.getElementById('bar-flood').style.width = flood + '%';
}
</script>
'''


# ==================== MAIN DASHBOARD BUILDER ====================

class RiskDashboard:
    """Main dashboard generator class."""
    
    def __init__(
        self,
        predictions_df: pd.DataFrame,
        routes: List[Route],
        firms_df: pd.DataFrame = None,
        usgs_df: pd.DataFrame = None
    ):
        self.predictions_df = predictions_df
        self.routes = routes
        self.firms_df = firms_df if firms_df is not None else pd.DataFrame()
        self.usgs_df = usgs_df if usgs_df is not None else pd.DataFrame()
    
    def build(self, output_path: Path) -> None:
        """Generate complete HTML dashboard."""
        logger.info("Building Risk Dashboard...")
        
        # Create base map
        center_lat = self.predictions_df['lat'].mean() if not self.predictions_df.empty else 20
        center_lon = self.predictions_df['lon'].mean() if not self.predictions_df.empty else 0
        
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=2,
            tiles='OpenStreetMap'
        )
        
        # Add routes
        for route in self.routes:
            create_route_polylines(m, route)
            create_waypoint_markers(m, route)
        
        # Add prediction markers for non-route locations
        self._add_prediction_markers(m)
        
        # Add historical layers
        add_historical_layer(m, self.firms_df, self.usgs_df)
        
        # Add legend
        add_legend_html(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add fullscreen
        plugins.Fullscreen().add_to(m)
        
        # Generate sidebar
        sidebar_html = generate_sidebar_html(self.routes)
        
        # Combine into full HTML
        map_html = m._repr_html_()
        
        full_html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RiskRadar - Logistik-Risikobewertung Dashboard</title>
    {DASHBOARD_CSS}
</head>
<body>
    {sidebar_html}
    <div id="map-container">
        {map_html}
    </div>
    {DASHBOARD_JS}
</body>
</html>
        '''
        
        # Save
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        logger.info(f"Dashboard saved to: {output_path}")
    
    def _add_prediction_markers(self, map_obj: folium.Map) -> None:
        """Add markers for all prediction locations."""
        prediction_group = folium.FeatureGroup(name="📍 Standorte")
        
        for _, row in self.predictions_df.iterrows():
            risk = row.get('combined_risk_score', 0)
            
            if risk >= 75:
                color = 'red'
            elif risk >= 50:
                color = 'orange'
            elif risk >= 25:
                color = 'beige'
            else:
                color = 'green'
            
            popup_html = f'''
            <div style="width: 250px;">
                <h4>{row['site_name']}</h4>
                <p>🔥 Fire: {row.get('fire_risk_score', 0):.1f}%</p>
                <p>🌍 Quake: {row.get('quake_risk_score', 0):.1f}%</p>
                <p>⚠️ Combined: {risk:.1f}%</p>
            </div>
            '''
            
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{row['site_name']}: {risk:.0f}%"
            ).add_to(prediction_group)
        
        prediction_group.add_to(map_obj)


def generate_dashboard(
    predictions_df: pd.DataFrame,
    routes_path: Path,
    output_path: Path,
    firms_df: pd.DataFrame = None,
    usgs_df: pd.DataFrame = None
) -> None:
    """
    Convenience function to generate dashboard.
    
    Args:
        predictions_df: DataFrame with location predictions
        routes_path: Path to routes CSV
        output_path: Output HTML path
        firms_df: Optional FIRMS data for historical layer
        usgs_df: Optional USGS data for historical layer
    """
    # Load and process routes
    routes = load_routes_from_csv(routes_path)
    routes = process_all_routes(routes, predictions_df)
    
    # Create dashboard
    dashboard = RiskDashboard(
        predictions_df=predictions_df,
        routes=routes,
        firms_df=firms_df,
        usgs_df=usgs_df
    )
    
    dashboard.build(output_path)


if __name__ == "__main__":
    # Test with mock data
    logging.basicConfig(level=logging.INFO)
    
    # Create mock predictions
    mock_predictions = pd.DataFrame({
        'site_name': ['Hamburg', 'Mumbai', 'Manila', 'Los Angeles', 'Miami'],
        'lat': [53.5511, 19.0760, 14.5995, 34.0522, 25.7617],
        'lon': [9.9937, 72.8777, 120.9842, -118.2437, -80.1918],
        'fire_risk_score': [10, 35, 45, 60, 30],
        'quake_risk_score': [20, 55, 65, 70, 15],
        'combined_risk_score': [28, 70, 81, 88, 40]
    })
    
    routes_path = Path('../data/routes.csv')
    output_path = Path('../outputs/risk_dashboard.html')
    
    if routes_path.exists():
        generate_dashboard(mock_predictions, routes_path, output_path)
        print(f"Dashboard generated: {output_path}")
    else:
        print(f"Routes file not found: {routes_path}")
