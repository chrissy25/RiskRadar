#!/bin/bash

# =============================================================================
# RiskRadar V4 - Stop-Skript
# =============================================================================

echo ""
echo "🛑 Stopping RiskRadar..."
docker-compose down
echo "✓ RiskRadar stopped"
echo ""
