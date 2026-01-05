@echo off
REM =============================================================================
REM RiskRadar V4 - Windows Update Script
REM =============================================================================

echo.
echo 🔄 Updating FIRMS data...
docker-compose run --rm radar python app/update_firms_data.py

echo.
echo 🔮 Generating new forecast...
docker-compose run --rm radar python app/run_real_forecast.py

echo.
echo ✅ Update complete!
echo.
echo 🗺️  View results: http://localhost:8080/sensor_forecast_map.html
echo.
pause
