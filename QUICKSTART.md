# RiskRadar - Quick Start Guide

## 🚀 Schnellstart in 3 Schritten

### 1. Installation

```bash
# Repository klonen
git clone <repo-url>
cd RiskRadar

# Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependencies
pip install -r app/requirements.txt
```

### 2. Modell trainieren (einmalig)

```bash
cd app
python train_sensor_model.py
```

**Output:**
- `outputs/fire_model_v4.pkl`
- `outputs/quake_model_v4.pkl`
- Evaluation-Metriken im Terminal

### 3. Vorhersage ausführen

```bash
python run_real_forecast.py
```

**Output:**
- `outputs/real_forecast_72h.csv` - Vorhersagen
- `outputs/real_forecast_map.html` - Interaktive Karte

---

## ⚙️ Konfiguration

Erstelle eine `.env` Datei (optional):

```bash
# Risiko-Parameter
FIRE_RADIUS_KM=50
QUAKE_RADIUS_KM=100
MIN_QUAKE_MAGNITUDE=4.0

# Features
LOOKBACK_DAYS=7
FORECAST_HOURS=72
```

---

## 📊 Standorte anpassen

Editiere `data/standorte.csv`:

```csv
name,lat,lon
Los Angeles,34.0522,-118.2437
San Francisco,37.7749,-122.4194
Anchorage,61.2181,-149.9003
```

---

## 🐳 Docker (Alternative)

```bash
docker-compose up --build
```

---

## 📚 Weitere Infos

- **Vollständige Doku**: Siehe `CONFLUENCE_DOKUMENTATION.md`
- **Details**: Siehe `README.md`

## 🚀 Schnellstart-Optionen

### Option 1: Lokale Ausführung (Einfach)

```bash
# 1. Setup Script ausführbar machen
chmod +x setup_and_run.sh

# 2. Alles automatisch installieren und starten
./setup_and_run.sh
```

Das war's! Die Applikation wird automatisch:
- Python Virtual Environment erstellen
- Alle Dependencies installieren
- Die Risikoanalyse durchführen
- Ergebnisse in `outputs/` speichern

### Option 2: Manuelle Installation

```bash
# 1. Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Dependencies installieren
pip install -r app/requirements.txt

# 3. Applikation starten
cd app
python run.py
```

### Option 3: Docker (Reproduzierbar)

```bash
# Alles mit Docker Compose starten
docker-compose up --build

# Im Hintergrund laufen lassen
docker-compose up -d

# Logs anschauen
docker-compose logs -f radar

# Stoppen
docker-compose down
```

## 📊 Ergebnisse ansehen

Nach der Ausführung finden Sie:

1. **CSV-Dateien** in `outputs/`:
   - `standort_risiko.csv` - Finales Ranking
   - `events_joined.csv` - Detaillierte Event-Daten

2. **Interaktive Karte**:
   ```bash
   # macOS
   open outputs/karte.html
   
   # Linux
   xdg-open outputs/karte.html
   
   # Windows
   start outputs/karte.html
   
   # Oder mit dem Docker nginx Viewer
   open http://localhost:8080/karte.html
   ```

## ⚙️ Konfiguration anpassen

Bearbeiten Sie die `.env` Datei:

```bash
# Beispiel: Nur Waldbrände, letzte 30 Tage
CATEGORY=wildfires
EONET_DAYS=30

# Beispiel: Periodische Ausführung alle 60 Minuten
RUN_INTERVAL_MINUTES=60

# Beispiel: Top 10 Risiko-Standorte anzeigen
TOP_K=10
```

## 🔧 Troubleshooting

### Problem: "Module not found"
```bash
# Stellen Sie sicher, dass Sie im Virtual Environment sind
source venv/bin/activate
pip install -r app/requirements.txt
```

### Problem: "Permission denied"
```bash
# Setup Script ausführbar machen
chmod +x setup_and_run.sh
```

### Problem: Keine Events gefunden
```bash
# Erhöhen Sie das Zeitfenster in .env
EONET_DAYS=30

# Oder entfernen Sie regionale Beschränkungen
REGION_BBOX=
```

## 🎯 Nächste Schritte

1. **Eigene Standorte hinzufügen**:
   - Bearbeiten Sie `data/standorte.csv`
   - Format: `name,lat,lon`

2. **Parameter optimieren**:
   - Passen Sie `BUFFER_KM` und `MAX_AGE_H` an
   - Experimentieren Sie mit verschiedenen Kategorien

3. **Periodisches Monitoring einrichten**:
   - Setzen Sie `RUN_INTERVAL_MINUTES > 0`
   - Applikation läuft im Loop

4. **ML-Modell analysieren**:
   - Schauen Sie sich die Feature-Koeffizienten in den Logs an
   - ROC-AUC Score zeigt Modell-Qualität

## 📚 Weitere Informationen

Siehe `README.md` für:
- Detaillierte Architektur
- ML-Erklärungen
- Best Practices
- Erweiterungsmöglichkeiten
