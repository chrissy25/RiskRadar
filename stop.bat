@echo off
REM =============================================================================
REM RiskRadar V4 - Windows Stop Script
REM =============================================================================

echo.
echo 🛑 Stopping RiskRadar...
docker-compose down
echo ✓ RiskRadar stopped
echo.
pause
