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


def generate_route_builder_html() -> str:
    """Generate HTML for the dynamic route builder section."""
    return '''
    <div class="route-builder-section">
        <h4>🛤️ Routen-Builder</h4>
        <p class="builder-hint" id="builder-hint">Klicken Sie auf Standorte auf der Karte, um eine Route zu erstellen</p>
        <div id="route-builder-list"></div>
        <div id="route-summary" style="display: none;">
            <div class="risk-total">
                <div class="risk-row">
                    <span>🔥 Feuer:</span>
                    <span id="total-fire">0%</span>
                </div>
                <div class="risk-row">
                    <span>🌍 Erdbeben:</span>
                    <span id="total-quake">0%</span>
                </div>
                <hr>
                <div class="risk-row total-row">
                    <strong>⚠️ Gesamtrisiko:</strong>
                    <strong id="total-risk">0%</strong>
                </div>
            </div>
        </div>
        <button id="clear-route-btn" onclick="clearRoute()" style="display: none;">Route löschen</button>
    </div>
    '''


def generate_sidebar_html(routes: List[Route]) -> str:
    """Generate complete sidebar HTML."""
    route_list = generate_route_list_html(routes)
    location_profile = generate_location_profile_html()
    route_builder = generate_route_builder_html()
    
    return f'''
    <div id="sidebar">
        <div class="sidebar-header">
            <h2>Logistik-Risikobewertung</h2>
            <h3>Dashboard</h3>
        </div>
        
        <div class="sidebar-section">
            <h4>Suche & Filter</h4>
            <input type="text" id="search-box" placeholder="Suchort, Lokation / Routen..." oninput="filterRoutes(this.value)">
        </div>
        
        <div class="sidebar-section">
            <h4>Aktuelle Routen-Risiken</h4>
            {route_list}
        </div>
        
        <div class="sidebar-section">
            {location_profile}
        </div>
        
        <div class="sidebar-section">
            {route_builder}
        </div>
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
        
        # Popup content with "Add to Route" button
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
            <button onclick="parent.addToRoute('{point.name}', {point.lat}, {point.lon}, {point.fire_risk}, {point.quake_risk}, {point.combined_risk})"
                    style="width: 100%; margin-top: 10px; padding: 8px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">
                ➕ Zur Route hinzufügen
            </button>
            <small style="display: block; margin-top: 5px; color: #666;">Route {route.route_id} - Waypoint {point.order}</small>
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
    max_fires: int = 1000,
    max_quakes: int = 500
) -> None:
    """Add historical fire and earthquake layers to the map.
    
    Shows all available data without time filtering.
    """
    
    # Historical Fires Layer
    fire_group = folium.FeatureGroup(name="🔥 Historische Feuer", show=False)
    
    if not firms_df.empty:
        try:
            # Use all available fire data (limited for performance)
            fires_to_show = firms_df.head(max_fires)
            logger.info(f"  Historical fires layer: {len(fires_to_show)} of {len(firms_df)} detections")
            
            # Add marker cluster for fires
            fire_cluster = plugins.MarkerCluster(name="Fire Detections")
            
            for _, row in fires_to_show.iterrows():
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=3,
                    color='red',
                    fill=True,
                    fillColor='red',
                    fillOpacity=0.6,
                    popup=f"Fire Detection<br>Date: {row.get('acq_date', 'N/A')}<br>"
                          f"Brightness: {row.get('brightness', 'N/A')}"
                ).add_to(fire_cluster)
            
            fire_cluster.add_to(fire_group)
        except Exception as e:
            logger.warning(f"Error adding fire layer: {e}")
    
    fire_group.add_to(map_obj)
    
    # Historical Earthquakes Layer
    quake_group = folium.FeatureGroup(name="🌍 Historische Erdbeben", show=False)
    
    if not usgs_df.empty:
        try:
            # Use all available earthquake data (limited for performance)
            quakes_to_show = usgs_df.head(max_quakes)
            logger.info(f"  Historical quakes layer: {len(quakes_to_show)} of {len(usgs_df)} earthquakes")
            
            for _, row in quakes_to_show.iterrows():
                mag = row.get('mag', 3.0)
                if pd.isna(mag):
                    mag = 3.0
                radius = max(3, float(mag) * 2)  # Scale by magnitude
                
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=radius,
                    color='blue',
                    fill=True,
                    fillColor='blue',
                    fillOpacity=0.5,
                    popup=f"Earthquake<br>Magnitude: {mag:.1f}<br>"
                          f"Date: {row.get('time', 'N/A')}<br>"
                          f"Location: {row.get('place', 'N/A')}"
                ).add_to(quake_group)
        except Exception as e:
            logger.warning(f"Error adding earthquake layer: {e}")
    
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

.route-builder-section {
    background: white;
    padding: 12px;
    border-radius: 4px;
}

.route-builder-section h4 {
    margin: 0 0 10px 0;
    font-size: 0.95em;
}

.builder-hint {
    color: #666;
    font-size: 0.85em;
    font-style: italic;
    margin: 0;
}

#route-builder-list {
    max-height: 150px;
    overflow-y: auto;
}

.route-waypoint-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 8px;
    margin: 4px 0;
    background: #e9ecef;
    border-radius: 4px;
    font-size: 0.85em;
}

.route-waypoint-item .waypoint-name {
    font-weight: 500;
}

.route-waypoint-item .waypoint-risk {
    color: #dc3545;
}

.route-waypoint-item .remove-btn {
    cursor: pointer;
    color: #999;
    font-size: 1.1em;
}

.route-waypoint-item .remove-btn:hover {
    color: #dc3545;
}

#route-summary {
    margin-top: 10px;
}

.risk-total {
    background: #f8f9fa;
    padding: 8px;
    border-radius: 4px;
}

.risk-row {
    display: flex;
    justify-content: space-between;
    margin: 4px 0;
    font-size: 0.9em;
}

.total-row {
    font-size: 1em;
    margin-top: 8px;
}

#clear-route-btn {
    width: 100%;
    margin-top: 10px;
    padding: 8px;
    background: #dc3545;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.85em;
}

#clear-route-btn:hover {
    background: #c82333;
}
</style>
'''


# ==================== JAVASCRIPT ====================

def generate_dashboard_js(predictions_df: pd.DataFrame, routes: List[Route]) -> str:
    """Generate JavaScript with embedded location data for search and route building."""
    
    # Build location data for search - now including risk values
    locations = []
    
    # Add prediction locations with their risk values
    for _, row in predictions_df.iterrows():
        locations.append({
            'name': row['site_name'],
            'lat': float(row['lat']),
            'lon': float(row['lon']),
            'fireRisk': float(row.get('fire_risk', 0)),
            'quakeRisk': float(row.get('quake_risk', 0)),
            'combinedRisk': float(row.get('combined_risk', 0)),
            'type': 'location'
        })
    
    # Add route waypoints with their risk values
    for route in routes:
        for point in route.points:
            # Check if already added
            if not any(loc['name'].lower() == point.name.lower() for loc in locations):
                locations.append({
                    'name': point.name,
                    'lat': float(point.lat),
                    'lon': float(point.lon),
                    'fireRisk': float(point.fire_risk),
                    'quakeRisk': float(point.quake_risk),
                    'combinedRisk': float(point.combined_risk),
                    'type': 'waypoint',
                    'route': route.route_id
                })
    
    locations_json = json.dumps(locations)
    
    return f'''
<script>
// Location data for search and route building
const locationData = {locations_json};

// Current route being built
let currentRoute = [];

// Get map object from iframe
function getMapObject() {{
    const iframe = document.querySelector('#map-container iframe');
    if (iframe && iframe.contentWindow) {{
        const win = iframe.contentWindow;
        for (let key in win) {{
            if (key.startsWith('map_') && win[key] && typeof win[key].flyTo === 'function') {{
                return win[key];
            }}
        }}
    }}
    return null;
}}

function selectRoute(routeId) {{
    console.log('Selected route:', routeId);
    const waypoint = locationData.find(loc => loc.route === routeId);
    if (waypoint) {{
        panToLocation(waypoint.lat, waypoint.lon, waypoint.name);
    }}
}}

function panToLocation(lat, lon, name) {{
    const map = getMapObject();
    if (map) {{
        map.flyTo([lat, lon], 5, {{ duration: 1.5 }});
        console.log('Panning to:', name, lat, lon);
    }}
}}

function filterRoutes(query) {{
    const items = document.querySelectorAll('.route-item');
    const lowerQuery = query.toLowerCase().trim();
    
    items.forEach(item => {{
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(lowerQuery) ? 'block' : 'none';
    }});
    
    if (lowerQuery.length >= 2) {{
        const match = locationData.find(loc => 
            loc.name.toLowerCase().includes(lowerQuery)
        );
        if (match) {{
            panToLocation(match.lat, match.lon, match.name);
            updateLocationProfile(match.name, match.fireRisk || 0, match.quakeRisk || 0, 0);
        }}
    }}
}}

// Handle Enter key in search box
document.addEventListener('DOMContentLoaded', function() {{
    const searchBox = document.getElementById('search-box');
    if (searchBox) {{
        searchBox.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') {{
                const query = this.value.toLowerCase().trim();
                const match = locationData.find(loc => 
                    loc.name.toLowerCase() === query ||
                    loc.name.toLowerCase().startsWith(query)
                );
                if (match) {{
                    panToLocation(match.lat, match.lon, match.name);
                }}
            }}
        }});
    }}
}});

function updateLocationProfile(name, fire, quake, flood) {{
    document.getElementById('profile-name').textContent = name;
    document.getElementById('profile-fire').textContent = fire.toFixed(0) + '%';
    document.getElementById('profile-quake').textContent = quake.toFixed(0) + '%';
    document.getElementById('profile-flood').textContent = flood.toFixed(0) + '%';
    
    document.getElementById('bar-fire').style.width = Math.min(fire, 100) + '%';
    document.getElementById('bar-quake').style.width = Math.min(quake, 100) + '%';
    document.getElementById('bar-flood').style.width = Math.min(flood, 100) + '%';
}}

// ==================== ROUTE BUILDER FUNCTIONS ====================

function addToRoute(name, lat, lon, fireRisk, quakeRisk, combinedRisk) {{
    // Check if already in route
    if (currentRoute.some(p => p.name === name)) {{
        console.log('Location already in route:', name);
        return;
    }}
    
    currentRoute.push({{ name, lat, lon, fireRisk, quakeRisk, combinedRisk }});
    renderRouteBuilder();
    console.log('Added to route:', name);
}}

function removeFromRoute(index) {{
    currentRoute.splice(index, 1);
    renderRouteBuilder();
}}

function clearRoute() {{
    currentRoute = [];
    renderRouteBuilder();
}}

function renderRouteBuilder() {{
    const listEl = document.getElementById('route-builder-list');
    const summaryEl = document.getElementById('route-summary');
    const hintEl = document.getElementById('builder-hint');
    const clearBtn = document.getElementById('clear-route-btn');
    
    if (currentRoute.length === 0) {{
        listEl.innerHTML = '';
        summaryEl.style.display = 'none';
        hintEl.style.display = 'block';
        clearBtn.style.display = 'none';
        return;
    }}
    
    hintEl.style.display = 'none';
    summaryEl.style.display = 'block';
    clearBtn.style.display = 'block';
    
    // Render waypoint items
    let html = '';
    currentRoute.forEach((point, index) => {{
        html += `
            <div class="route-waypoint-item">
                <span class="waypoint-name">${{index + 1}}. ${{point.name}}</span>
                <span class="waypoint-risk">⚠️ ${{point.combinedRisk.toFixed(0)}}%</span>
                <span class="remove-btn" onclick="removeFromRoute(${{index}})">✕</span>
            </div>
        `;
    }});
    listEl.innerHTML = html;
    
    // Calculate totals
    let totalFire = 0;
    let totalQuake = 0;
    let totalCombined = 0;
    
    currentRoute.forEach(point => {{
        totalFire += point.fireRisk;
        totalQuake += point.quakeRisk;
        totalCombined += point.combinedRisk;
    }});
    
    // Average the risks (or could use max/sum depending on preference)
    const avgFire = totalFire / currentRoute.length;
    const avgQuake = totalQuake / currentRoute.length;
    const avgCombined = totalCombined / currentRoute.length;
    
    document.getElementById('total-fire').textContent = avgFire.toFixed(0) + '%';
    document.getElementById('total-quake').textContent = avgQuake.toFixed(0) + '%';
    document.getElementById('total-risk').textContent = avgCombined.toFixed(0) + '%';
}}

// Expose addToRoute globally for map popups
window.addToRoute = addToRoute;
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
        
        # Add routes (polylines only, no waypoint markers)
        for route in self.routes:
            create_route_polylines(m, route)
        
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
        
        # Generate JavaScript with location data
        dashboard_js = generate_dashboard_js(self.predictions_df, self.routes)
        
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
    {dashboard_js}
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
            
            fire_risk = row.get('fire_risk_score', 0)
            quake_risk = row.get('quake_risk_score', 0)
            site_name = row['site_name']
            lat = row['lat']
            lon = row['lon']
            
            popup_html = f'''
            <div style="width: 250px; font-family: Arial, sans-serif;">
                <h4 style="margin: 0 0 10px 0;">{site_name}</h4>
                <hr>
                <div style="margin: 5px 0;">
                    <strong>🔥 Fire Risk:</strong> {fire_risk:.1f}%
                    <div style="background: #ffcccc; height: 8px; border-radius: 4px;">
                        <div style="background: #dc3545; height: 8px; width: {min(fire_risk, 100)}%; border-radius: 4px;"></div>
                    </div>
                </div>
                <div style="margin: 5px 0;">
                    <strong>🌍 Quake Risk:</strong> {quake_risk:.1f}%
                    <div style="background: #cce5ff; height: 8px; border-radius: 4px;">
                        <div style="background: #0d6efd; height: 8px; width: {min(quake_risk, 100)}%; border-radius: 4px;"></div>
                    </div>
                </div>
                <hr>
                <div style="margin: 5px 0;">
                    <strong>⚠️ Combined:</strong> {risk:.1f}%
                </div>
                <button onclick="parent.addToRoute('{site_name}', {lat}, {lon}, {fire_risk}, {quake_risk}, {risk})"
                        style="width: 100%; margin-top: 10px; padding: 8px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">
                    ➕ Zur Route hinzufügen
                </button>
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
