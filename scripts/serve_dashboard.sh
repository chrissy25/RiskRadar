#!/bin/bash
# RiskRadar Dashboard Dev Server
# Starts a local HTTP server for the static dashboard

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "================================"
echo "RiskRadar Dashboard Dev Server"
echo "================================"
echo ""
echo "Serving from: $PROJECT_ROOT"
echo "Dashboard URL: http://localhost:8080/app/dashboard/"
echo ""
echo "Press Ctrl+C to stop the server."
echo ""

cd "$PROJECT_ROOT"
python3 -m http.server 8080
