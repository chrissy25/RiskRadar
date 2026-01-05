"""
USGS Earthquake API Client

Provides access to real-time earthquake data from the United States Geological Survey.
Earthquake activity can be a precursor to or co-occur with other natural disasters.

API Documentation: https://earthquake.usgs.gov/fdsnws/event/1/
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)


class USGSClient:
    """
    Client for USGS Earthquake Catalog API.
    
    Provides real-time and historical earthquake data from USGS monitoring stations worldwide.
    No API key required - public data service.
    """
    
    def __init__(self):
        """Initialize USGS client."""
        self.base_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        
        # Rate limiting: Be respectful of public API
        self.last_request_time = None
        self.min_request_interval = 1.0  # seconds between requests
        
    def _rate_limit(self):
        """Enforce rate limiting between API requests."""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def get_earthquakes(
        self,
        lat: float,
        lon: float,
        radius_km: int = 200,
        days: int = 30,
        min_magnitude: float = 2.5
    ) -> Dict:
        """
        Get earthquakes within radius of a location.
        
        Args:
            lat: Latitude of center point
            lon: Longitude of center point
            radius_km: Search radius in kilometers (max 20,000)
            days: Number of days to look back
            min_magnitude: Minimum magnitude to include (0-10)
        
        Returns:
            Dictionary with earthquake data:
            {
                'count': int,
                'earthquakes': List[Dict],
                'max_magnitude': float,
                'avg_magnitude': float,
                'recent_count_7d': int,
                'magnitude_5plus': int,
                'depth_avg': float
            }
        """
        self._rate_limit()
        
        # Calculate date range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Convert radius to degrees (approximate: 1 degree ≈ 111 km)
        max_radius_deg = radius_km / 111.0
        
        params = {
            'format': 'geojson',
            'latitude': lat,
            'longitude': lon,
            'maxradiuskm': radius_km,
            'starttime': start_time.strftime('%Y-%m-%d'),
            'endtime': end_time.strftime('%Y-%m-%d'),
            'minmagnitude': min_magnitude,
            'orderby': 'time-asc'
        }
        
        try:
            logger.debug(f"Fetching USGS earthquakes for ({lat}, {lon}) radius {radius_km}km")
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            count = len(features)
            
            if count == 0:
                return {
                    'count': 0,
                    'earthquakes': [],
                    'max_magnitude': 0.0,
                    'avg_magnitude': 0.0,
                    'recent_count_7d': 0,
                    'magnitude_5plus': 0,
                    'depth_avg': 0.0
                }
            
            # Extract earthquake properties
            earthquakes = []
            magnitudes = []
            depths = []
            recent_count = 0
            magnitude_5plus = 0
            
            recent_cutoff = (datetime.utcnow() - timedelta(days=7)).timestamp() * 1000
            
            for feature in features:
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                mag = props.get('mag', 0.0)
                depth = geom.get('coordinates', [0, 0, 0])[2]  # Depth is 3rd coordinate
                time_ms = props.get('time', 0)
                
                earthquakes.append({
                    'magnitude': mag,
                    'depth_km': depth,
                    'time': datetime.fromtimestamp(time_ms / 1000).isoformat(),
                    'place': props.get('place', 'Unknown'),
                    'type': props.get('type', 'earthquake')
                })
                
                magnitudes.append(mag)
                depths.append(depth)
                
                if time_ms >= recent_cutoff:
                    recent_count += 1
                
                if mag >= 5.0:
                    magnitude_5plus += 1
            
            # Calculate statistics
            max_magnitude = max(magnitudes) if magnitudes else 0.0
            avg_magnitude = sum(magnitudes) / len(magnitudes) if magnitudes else 0.0
            depth_avg = sum(depths) / len(depths) if depths else 0.0
            
            result = {
                'count': count,
                'earthquakes': earthquakes,
                'max_magnitude': max_magnitude,
                'avg_magnitude': avg_magnitude,
                'recent_count_7d': recent_count,
                'magnitude_5plus': magnitude_5plus,
                'depth_avg': depth_avg
            }
            
            logger.info(
                f"USGS: {count} earthquakes near ({lat}, {lon}), "
                f"max magnitude: {max_magnitude:.1f}, "
                f"recent (7d): {recent_count}, "
                f"magnitude 5+: {magnitude_5plus}"
            )
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"USGS API error for ({lat}, {lon}): {e}")
            return {
                'count': 0,
                'earthquakes': [],
                'max_magnitude': 0.0,
                'avg_magnitude': 0.0,
                'recent_count_7d': 0,
                'magnitude_5plus': 0,
                'depth_avg': 0.0,
                'error': str(e)
            }
    
    def get_seismic_features(self, lat: float, lon: float) -> Dict[str, float]:
        """
        Get seismic activity features for ML model.
        
        Args:
            lat: Latitude
            lon: Longitude
        
        Returns:
            Dictionary of features:
            {
                'earthquakes_30d': int,
                'earthquakes_7d': int,
                'earthquake_max_magnitude': float,
                'earthquake_avg_magnitude': float,
                'earthquake_5plus': int,
                'seismic_activity_trend': float  # ratio of recent to total
            }
        """
        # Get 30-day earthquake data
        quakes_30d = self.get_earthquakes(lat, lon, radius_km=200, days=30, min_magnitude=2.5)
        
        # Calculate trend (increasing or decreasing activity)
        total_count = quakes_30d['count']
        recent_count = quakes_30d['recent_count_7d']
        
        # Trend: ratio of recent (7d) to expected based on 30d rate
        # If ratio > 1: increasing activity, < 1: decreasing
        expected_recent = (total_count / 30.0) * 7.0
        seismic_trend = recent_count / expected_recent if expected_recent > 0 else 0.0
        
        features = {
            'earthquakes_30d': total_count,
            'earthquakes_7d': recent_count,
            'earthquake_max_magnitude': quakes_30d['max_magnitude'],
            'earthquake_avg_magnitude': quakes_30d['avg_magnitude'],
            'earthquake_5plus': quakes_30d['magnitude_5plus'],
            'seismic_activity_trend': seismic_trend
        }
        
        logger.debug(f"Seismic features for ({lat}, {lon}): {features}")
        return features


    def get_global_earthquakes(
        self,
        start_date: str,
        end_date: str,
        min_magnitude: float = 2.5
    ) -> List[Dict]:
        """
        Get all global earthquakes in date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_magnitude: Minimum magnitude
            
        Returns:
            List of earthquake dictionaries
        """
        self._rate_limit()
        
        params = {
            'format': 'geojson',
            'starttime': start_date,
            'endtime': end_date,
            'minmagnitude': min_magnitude,
            'orderby': 'time-asc'
        }
        
        try:
            logger.info(f"Fetching global USGS earthquakes ({start_date} to {end_date}, min mag {min_magnitude})")
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            features = data.get('features', [])
            
            logger.info(f"  ✓ Fetched {len(features):,} earthquakes")
            
            # Convert to list of dicts
            earthquakes = []
            for feature in features:
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})
                
                coords = geom.get('coordinates', [0, 0, 0])
                time_ms = props.get('time', 0)
                
                earthquakes.append({
                    'latitude': coords[1],
                    'longitude': coords[0],
                    'depth_km': coords[2],
                    'time': datetime.fromtimestamp(time_ms / 1000).isoformat(),
                    'mag': props.get('mag', 0.0),
                    'place': props.get('place', 'Unknown'),
                    'type': props.get('type', 'earthquake')
                })
            
            return earthquakes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"USGS API error: {e}")
            return []


def cache_usgs_data(start_date: str, end_date: str, output_path: str = 'outputs/usgs_earthquakes_cache.csv'):
    """
    Cache global USGS earthquake data to CSV.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        output_path: Output CSV path
    """
    import pandas as pd
    from pathlib import Path
    
    print("="*60)
    print("USGS EARTHQUAKE DATA CACHING")
    print("="*60)
    print(f"\nDate Range: {start_date} to {end_date}")
    print(f"Output: {output_path}\n")
    
    client = USGSClient()
    
    # Fetch data
    print("Fetching data from USGS API...")
    earthquakes = client.get_global_earthquakes(start_date, end_date, min_magnitude=2.5)
    
    if not earthquakes:
        print("WARNING: No earthquakes fetched!")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(earthquakes)
    
    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Save
    df.to_csv(output_path, index=False)
    
    print(f"\n✓ Cached {len(df):,} earthquakes to {output_path}")
    print(f"\nStatistics:")
    print(f"  Date Range: {df['time'].min()} to {df['time'].max()}")
    print(f"  Magnitude Range: {df['mag'].min():.1f} to {df['mag'].max():.1f}")
    print(f"  Magnitude ≥5.0: {(df['mag'] >= 5.0).sum()}")
    print(f"  Magnitude ≥6.0: {(df['mag'] >= 6.0).sum()}")
    print(f"  Magnitude ≥7.0: {(df['mag'] >= 7.0).sum()}")
    print(f"\n✓ Cache complete!")


def test_usgs_client():
    """Test USGS client with seismically active location."""
    client = USGSClient()
    
    # Test Tokyo (seismically active region)
    print("Testing USGS API with Tokyo...")
    lat, lon = 35.6762, 139.6503
    
    quakes = client.get_earthquakes(lat, lon, radius_km=200, days=30)
    
    print(f"\n✓ Earthquakes detected (30d): {quakes['count']}")
    print(f"✓ Max magnitude: {quakes['max_magnitude']:.1f}")
    print(f"✓ Avg magnitude: {quakes['avg_magnitude']:.1f}")
    print(f"✓ Recent count (7d): {quakes['recent_count_7d']}")
    print(f"✓ Magnitude 5+: {quakes['magnitude_5plus']}")
    print(f"✓ Avg depth: {quakes['depth_avg']:.1f} km")
    
    # Get ML features
    features = client.get_seismic_features(lat, lon)
    print(f"\nML Features: {features}")
    print(f"Seismic trend: {features['seismic_activity_trend']:.2f} ({'increasing' if features['seismic_activity_trend'] > 1 else 'stable/decreasing'})")


if __name__ == "__main__":
    import sys
    import argparse
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser(description='USGS Earthquake Data Tool')
    parser.add_argument('--cache', action='store_true', help='Cache earthquake data to CSV')
    parser.add_argument('--start-date', type=str, default='2024-05-01', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default='2024-12-31', help='End date (YYYY-MM-DD)')
    parser.add_argument('--output', type=str, default='outputs/usgs_earthquakes_cache.csv', help='Output CSV path')
    
    args = parser.parse_args()
    
    if args.cache:
        cache_usgs_data(args.start_date, args.end_date, args.output)
    else:
        test_usgs_client()
