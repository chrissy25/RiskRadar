# =============================================================================
# RiskRadar V4 - Docker Image
# Sensor-based Wildfire & Earthquake Risk Prediction System
# =============================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy FIRMS data directories (read-only, large files)
COPY FIRMS_2024_ARCHIVE/ ./FIRMS_2024_ARCHIVE/
COPY FIRMS_2025_NRT/ ./FIRMS_2025_NRT/

# Create necessary directories
RUN mkdir -p /app/data/cache /app/outputs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command: Show help/usage
CMD ["python", "-c", "print('\\n' + '='*70 + '\\n' + 'RiskRadar V4 - Available Commands:\\n' + '='*70 + '\\n' + '1. Update FIRMS data:     docker-compose run --rm radar python app/update_firms_data.py\\n' + '2. Build dataset:         docker-compose run --rm radar python app/build_sensor_dataset.py\\n' + '3. Train fire model:      docker-compose run --rm radar python app/train_sensor_model.py --model fire\\n' + '4. Train quake model:     docker-compose run --rm radar python app/train_sensor_model.py --model quake\\n' + '5. Run forecast:          docker-compose run --rm radar python app/run_real_forecast.py\\n' + '\\n' + 'View results: http://localhost:8080/sensor_forecast_map.html\\n' + '='*70 + '\\n')"]
