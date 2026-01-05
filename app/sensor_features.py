#!/usr/bin/env python3
"""
Sensor-basierte Feature-Extraktion für RiskRadar V4

Features basieren auf Past Data (< target_date):
- FIRMS Historical Fire Activity
- USGS Historical Seismic Activity  
- Weather: Open-Meteo (Historical für Training, Forecast für Prediction)
- Temporal/Geographic Features

WICHTIG: Kein EONET mehr für Features!
UPGRADE: Open-Meteo statt OpenWeather → Kostenlose historische Daten!

Author: RiskRadar Team
Date: 2025-12-23
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
import requests
from typing import Dict, Optional
from geo_utils import haversine_distance

# Import Open-Meteo Client
from openmeteo_client import get_historical_weather_features, get_forecast_weather_features

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

RADIUS_KM = 50  # Radius für historische Daten (direkte Umgebung)
FIRMS_CONFIDENCE_THR = 70  # Minimum confidence für FIRMS
FIRMS_MIN_FRP = 30.0  # Minimum FRP in MW (filtert landwirtschaftliche/industrielle/kleine Feuer)
FIRMS_DAYLIGHT_ONLY = True  # Nur Tageslicht-Detektionen


# ==================== FIRMS HISTORICAL FEATURES ====================

def extract_firms_historical_features(
    site: Dict[str, float],
    target_date: pd.Timestamp,
    firms_df: pd.DataFrame,
    lookback_days_short: int = 7,
    lookback_days_long: int = 30
) -> Dict[str, float]:
    """
    Extract historical fire features from FIRMS (BEFORE target_date!).
    
    Args:
        site: Dict with 'lat', 'lon'
        target_date: Timestamp (features must be < target_date)
        firms_df: FIRMS DataFrame
        lookback_days_short: Short period (default 7 days)
        lookback_days_long: Long period (default 30 days)
        
    Returns:
        Dict with features:
        - fires_7d_count: Number of detections last 7 days
        - fires_30d_count: Number of detections last 30 days
        - fire_max_brightness_7d: Highest brightness
        - fire_avg_brightness_7d: Average
        - fire_max_frp_7d: Highest FRP
        - fires_persistent: Number of days with fire (last 7 days)
        - days_since_last_fire: Days since last fire (max 999)
    """
    lat, lon = site['lat'], site['lon']
    
    # Time window (PAST only!)
    past_start_short = target_date - timedelta(days=lookback_days_short)
    past_start_long = target_date - timedelta(days=lookback_days_long)
    past_end = target_date  # EXKLUSIV: alles < target_date
    
    # Datums-Konvertierung
    if not pd.api.types.is_datetime64_any_dtype(firms_df['acq_date']):
        firms_df = firms_df.copy()
        firms_df['acq_date'] = pd.to_datetime(firms_df['acq_date'])
    
    # Filter: Past + Confidence + FRP + (optional) Daylight + Radius
    filters_short = [
        (firms_df['acq_date'] >= past_start_short),
        (firms_df['acq_date'] < past_end),
        (firms_df['confidence'] >= FIRMS_CONFIDENCE_THR),
        (firms_df['frp'] >= FIRMS_MIN_FRP)
    ]
    
    filters_long = [
        (firms_df['acq_date'] >= past_start_long),
        (firms_df['acq_date'] < past_end),
        (firms_df['confidence'] >= FIRMS_CONFIDENCE_THR),
        (firms_df['frp'] >= FIRMS_MIN_FRP)
    ]
    
    # Daylight filter (nur wenn Spalte existiert)
    if 'daynight' in firms_df.columns:
        filters_short.append(firms_df['daynight'] == 'D')
        filters_long.append(firms_df['daynight'] == 'D')
    
    # Kombiniere Filter
    from functools import reduce
    import operator
    past_fires_short = firms_df[reduce(operator.and_, filters_short)]
    past_fires_long = firms_df[reduce(operator.and_, filters_long)]
    
    # Räumlicher Filter
    if len(past_fires_short) > 0:
        past_fires_short = past_fires_short[
            past_fires_short.apply(
                lambda row: haversine_distance(lat, lon, row['latitude'], row['longitude']) < RADIUS_KM,
                axis=1
            )
        ]
    
    if len(past_fires_long) > 0:
        past_fires_long = past_fires_long[
            past_fires_long.apply(
                lambda row: haversine_distance(lat, lon, row['latitude'], row['longitude']) < RADIUS_KM,
                axis=1
            )
        ]
    
    # Features berechnen
    features = {}
    
    # Count Features
    features['fires_7d_count'] = len(past_fires_short)
    features['fires_30d_count'] = len(past_fires_long)
    
    # Brightness Features (7 Tage)
    if len(past_fires_short) > 0:
        features['fire_max_brightness_7d'] = past_fires_short['brightness'].max()
        features['fire_avg_brightness_7d'] = past_fires_short['brightness'].mean()
        features['fire_max_frp_7d'] = past_fires_short['frp'].max()
        features['fire_avg_frp_7d'] = past_fires_short['frp'].mean()
        
        # Persistent fires: Anzahl unterschiedliche Tage mit Feuer
        unique_days = past_fires_short['acq_date'].dt.date.nunique()
        features['fires_persistent_days'] = unique_days
        
        # Days since last fire
        most_recent = past_fires_short['acq_date'].max()
        days_diff = (target_date - most_recent).days
        features['days_since_last_fire'] = min(days_diff, 999)
    else:
        # Keine Feuer
        features['fire_max_brightness_7d'] = 0.0
        features['fire_avg_brightness_7d'] = 0.0
        features['fire_max_frp_7d'] = 0.0
        features['fire_avg_frp_7d'] = 0.0
        features['fires_persistent_days'] = 0
        features['days_since_last_fire'] = 999
    
    return features


# ==================== USGS HISTORICAL FEATURES ====================

def extract_usgs_historical_features(
    site: Dict[str, float],
    target_date: pd.Timestamp,
    usgs_df: pd.DataFrame,
    lookback_days_short: int = 7,
    lookback_days_long: int = 30,
    min_magnitude: float = 2.5
) -> Dict[str, float]:
    """
    Extract historical earthquake features from USGS (BEFORE target_date!).
    
    Args:
        site: Dict with 'lat', 'lon'
        target_date: Timestamp (features must be < target_date)
        usgs_df: USGS DataFrame with [time, mag, latitude, longitude]
        lookback_days_short: Short period (default 7 days)
        lookback_days_long: Long period (default 30 days)
        min_magnitude: Minimum magnitude for filter
        
    Returns:
        Dict with features:
        - quakes_7d_count
        - quakes_30d_count
        - quake_max_mag_30d
        - quake_avg_mag_30d
        - quakes_5plus_count: Number of M≥5.0
        - seismic_trend: Ratio recent/total
        - days_since_last_quake
    """
    lat, lon = site['lat'], site['lon']
    
    # Time window (PAST only!)
    past_start_short = target_date - timedelta(days=lookback_days_short)
    past_start_long = target_date - timedelta(days=lookback_days_long)
    past_end = target_date
    
    # Datums-Konvertierung
    if not pd.api.types.is_datetime64_any_dtype(usgs_df['time']):
        usgs_df = usgs_df.copy()
        usgs_df['time'] = pd.to_datetime(usgs_df['time'])
    
    # Filter: Past + Magnitude + Radius
    past_quakes_short = usgs_df[
        (usgs_df['time'] >= past_start_short) &
        (usgs_df['time'] < past_end) &
        (usgs_df['mag'] >= min_magnitude)
    ]
    
    past_quakes_long = usgs_df[
        (usgs_df['time'] >= past_start_long) &
        (usgs_df['time'] < past_end) &
        (usgs_df['mag'] >= min_magnitude)
    ]
    
    # Räumlicher Filter
    if len(past_quakes_short) > 0:
        past_quakes_short = past_quakes_short[
            past_quakes_short.apply(
                lambda row: haversine_distance(lat, lon, row['latitude'], row['longitude']) < RADIUS_KM,
                axis=1
            )
        ]
    
    if len(past_quakes_long) > 0:
        past_quakes_long = past_quakes_long[
            past_quakes_long.apply(
                lambda row: haversine_distance(lat, lon, row['latitude'], row['longitude']) < RADIUS_KM,
                axis=1
            )
        ]
    
    # Features berechnen
    features = {}
    
    # Count Features
    features['quakes_7d_count'] = len(past_quakes_short)
    features['quakes_30d_count'] = len(past_quakes_long)
    
    # Magnitude Features (30 Tage)
    if len(past_quakes_long) > 0:
        features['quake_max_mag_30d'] = past_quakes_long['mag'].max()
        features['quake_avg_mag_30d'] = past_quakes_long['mag'].mean()
        features['quakes_5plus_count'] = len(past_quakes_long[past_quakes_long['mag'] >= 5.0])
        
        # Seismic Trend: Ratio recent/total (normalisiert)
        if features['quakes_30d_count'] > 0:
            features['seismic_trend'] = (features['quakes_7d_count'] / features['quakes_30d_count']) * 4.3
        else:
            features['seismic_trend'] = 0.0
        
        # Days since last quake
        most_recent = past_quakes_long['time'].max()
        days_diff = (target_date - most_recent).days
        features['days_since_last_quake'] = min(days_diff, 999)
    else:
        # Keine Erdbeben
        features['quake_max_mag_30d'] = 0.0
        features['quake_avg_mag_30d'] = 0.0
        features['quakes_5plus_count'] = 0
        features['seismic_trend'] = 0.0
        features['days_since_last_quake'] = 999
    
    return features


# ==================== WEATHER FEATURES ====================

def extract_weather_features(
    site: Dict[str, float],
    target_date: pd.Timestamp,
    api_key: str = None,  # No longer needed with Open-Meteo!
    use_forecast: bool = True
) -> Dict[str, float]:
    """
    Extract weather features with Open-Meteo (free!).
    
    UPGRADE V4.3:
    - Training: Historical weather (7 days BEFORE target_date)
    - Prediction: Forecast weather (3 days FROM target_date)
    - Open-Meteo: Free, no API key needed!
    
    Args:
        site: Dict with 'lat', 'lon'
        target_date: Timestamp
        api_key: No longer used (compatibility)
        use_forecast: True = Forecast (Prediction), False = Historical (Training)
        
    Returns:
        Dict with 7 features:
        - temp_mean, temp_max, humidity_mean, humidity_min
        - wind_max, rain_total, dry_days
    """
    lat, lon = site['lat'], site['lon']
    
    try:
        if use_forecast:
            # PREDICTION MODE: Forecast for next 3 days
            logger.debug(f"Getting forecast weather for {lat}, {lon}")
            features = get_forecast_weather_features(lat, lon, days=3)
        else:
            # TRAINING MODE: Historical weather (7 Tage VOR target_date)
            target_str = target_date.strftime('%Y-%m-%d')
            logger.debug(f"Getting historical weather for {lat}, {lon} on {target_str}")
            features = get_historical_weather_features(lat, lon, target_str, lookback_days=7)
        
        return features
        
    except Exception as e:
        logger.warning(f"Weather API failed for {site.get('name', 'unknown')}: {e}")
        # Fallback: Gemäßigte Defaults
        return {
            'temp_mean': 15.0,
            'temp_max': 20.0,
            'humidity_mean': 60.0,
            'humidity_min': 40.0,
            'wind_max': 15.0,
            'rain_total': 0.0,
            'dry_days': 2.0
        }


# ==================== TEMPORAL/GEOGRAPHIC FEATURES ====================

def extract_temporal_geo_features(
    site: Dict[str, float],
    target_date: pd.Timestamp
) -> Dict[str, float]:
    """
    Extract temporal and geo features.
    
    Args:
        site: Dict with 'lat', 'lon'
        target_date: Timestamp
        
    Returns:
        Dict with 4 features:
        - latitude, longitude, month, season
    """
    # Calculate season (Northern hemisphere logic)
    month = target_date.month
    if month in [12, 1, 2]:
        season = 0  # Winter
    elif month in [3, 4, 5]:
        season = 1  # Spring
    elif month in [6, 7, 8]:
        season = 2  # Summer
    else:
        season = 3  # Fall
    
    return {
        'latitude': site['lat'],
        'longitude': site['lon'],
        'month': month,
        'season': season
    }


# ==================== MASTER FEATURE EXTRACTOR ====================

def extract_all_features(
    site: Dict[str, float],
    target_date: pd.Timestamp,
    firms_df: pd.DataFrame,
    usgs_df: pd.DataFrame,
    weather_api_key: Optional[str] = None,
    model_type: str = 'fire',
    use_historical_weather: bool = True  # NEW: True for Training, False for Prediction
) -> Dict[str, float]:
    """
    Master function: Extract all features for a sample.
    
    Args:
        site: Dict with 'name', 'lat', 'lon'
        target_date: Timestamp (features are < target_date!)
        firms_df: FIRMS DataFrame
        usgs_df: USGS DataFrame
        weather_api_key: No longer needed with Open-Meteo (compatibility)
        model_type: 'fire' or 'quake' (determines which features are important)
        use_historical_weather: True = Historical (Training), False = Forecast (Prediction)
        
    Returns:
        Dict with all features
    """
    features = {}
    
    # 1. FIRMS Historical (always for FireRisk, optional for QuakeRisk)
    if model_type == 'fire':
        features.update(extract_firms_historical_features(site, target_date, firms_df))
    
    # 2. USGS Historical (always for QuakeRisk, optional for FireRisk)
    if model_type == 'quake':
        features.update(extract_usgs_historical_features(site, target_date, usgs_df))
    
    # 3. Weather (mainly relevant for FireRisk)
    # UPGRADE: Open-Meteo mit Historical Support!
    if model_type == 'fire':
        use_forecast = not use_historical_weather  # Invert: historical=True → forecast=False
        features.update(extract_weather_features(site, target_date, api_key=None, use_forecast=use_forecast))
    
    # 4. Temporal/Geo (immer)
    features.update(extract_temporal_geo_features(site, target_date))
    
    return features


# ==================== TESTING ====================

if __name__ == "__main__":
    logger.info("Testing sensor_features.py...")
    
    # Dummy Data
    firms_data = pd.DataFrame({
        'latitude': [34.05] * 5,
        'longitude': [-118.24] * 5,
        'acq_date': pd.to_datetime([
            '2025-12-16', '2025-12-17', '2025-12-18', '2025-12-20', '2025-12-22'
        ]),
        'confidence': [85, 92, 78, 88, 91],
        'brightness': [325.7, 341.2, 298.5, 310.3, 350.1],
        'frp': [12.5, 18.3, 8.7, 15.2, 22.1]
    })
    
    usgs_data = pd.DataFrame({
        'latitude': [61.22, 61.25, 61.20],
        'longitude': [-149.90, -149.85, -149.95],
        'time': pd.to_datetime([
            '2025-12-10 10:30:00',
            '2025-12-15 14:20:00',
            '2025-12-20 08:15:00'
        ]),
        'mag': [3.2, 4.5, 2.8]
    })
    
    # Test Site
    la_site = {'name': 'Los Angeles', 'lat': 34.0522, 'lon': -118.2437}
    target = pd.Timestamp('2025-12-23 00:00:00')
    
    # Test FIRMS Features
    fire_features = extract_firms_historical_features(la_site, target, firms_data)
    logger.info(f"\nFIRMS Features: {fire_features}")
    
    # Test USGS Features
    anc_site = {'name': 'Anchorage', 'lat': 61.2181, 'lon': -149.9003}
    quake_features = extract_usgs_historical_features(anc_site, target, usgs_data)
    logger.info(f"\nUSGS Features: {quake_features}")
    
    # Test Temporal/Geo
    temporal_features = extract_temporal_geo_features(la_site, target)
    logger.info(f"\nTemporal/Geo Features: {temporal_features}")
    
    logger.info("\n✓ sensor_features.py tests passed!")
