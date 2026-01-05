# 🐳 Docker Quick Start

## Für Kommilitonen - System in 5 Minuten starten!

### 1. Voraussetzungen
- Docker Desktop installiert (https://www.docker.com/products/docker-desktop/)
- Projekt heruntergeladen/geklont

### 2. NASA FIRMS API Key holen (2 Minuten, kostenlos!)
1. Gehe zu: https://firms.modaps.eosdis.nasa.gov/api/area/
2. Registriere dich (nur Email)
3. Erhalte sofort deinen MAP_KEY per Email

### 3. Setup
```bash
# .env Datei erstellen
cp .env.example .env

# NASA FIRMS MAP_KEY eintragen (im Editor öffnen)
nano .env  # oder VSCode, TextEdit, etc.
# Zeile: FIRMS_MAP_KEY=dein_key_hier
```

### 4. Container bauen & starten
```bash
docker-compose build
docker-compose up -d
```

### 5. Vorhersage erstellen
```bash
docker-compose run --rm radar python app/run_real_forecast.py
```

### 6. Ergebnisse ansehen
```
http://localhost:8080/sensor_forecast_map.html
```

---

## 🎯 Für Präsentation

### Vorbereitung (1x durchführen):
```bash
# Container bauen
docker-compose build

# Vorhersage erstellen
docker-compose run --rm radar python app/run_real_forecast.py
```

### Am Präsentationstag:
```bash
# Nur Web-Viewer starten (3 Sekunden!)
docker-compose up -d viewer

# Karte öffnen
open http://localhost:8080/sensor_forecast_map.html
```

---

## 📚 Mehr Infos
- Vollständige Anleitung: `DOCKER_GUIDE.md`
- Troubleshooting: `DOCKER_GUIDE.md#troubleshooting`
- FIRMS-Updates: `FIRMS_UPDATE_ANLEITUNG.md`
