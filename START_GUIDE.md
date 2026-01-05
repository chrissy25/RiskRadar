# 🌍 RiskRadar V4 - Ultra-Simple Start Guide

## Für Kommilitonen - In 3 Schritten starten!

### ✅ Voraussetzungen
- **Docker Desktop** installiert: https://www.docker.com/products/docker-desktop/
- Das wars! 🎉

---

### 🚀 Schritt 1: NASA FIRMS API Key holen (2 Minuten, kostenlos)

1. Gehe zu: **https://firms.modaps.eosdis.nasa.gov/api/area/**
2. Registriere dich (nur Email)
3. Du bekommst sofort deinen **MAP_KEY**
4. Öffne die Datei `.env` und trage den Key ein:
   ```
   FIRMS_MAP_KEY=dein_key_hier
   ```

---

### 🎯 Schritt 2: System starten

**Mac/Linux:**
```bash
./start.sh
```

**Windows:**
```
Doppelklick auf start.bat
```

Das wars! 🎉

---

### 🗺️ Schritt 3: Ergebnisse ansehen

Öffne im Browser:
```
http://localhost:8080/sensor_forecast_map.html
```

---

## 📋 Weitere Befehle

### System aktualisieren (neue Daten laden)
**Mac/Linux:** `./update.sh`  
**Windows:** `update.bat`

### System stoppen
**Mac/Linux:** `./stop.sh`  
**Windows:** `stop.bat`

---

## ⏱️ Wie lange dauert es?

- **Erstes Mal:** ~5 Min (Container bauen) + 60 Min (Modelle trainieren)
- **Danach:** ~7 Sekunden! ⚡

**Hinweis:** Die 60 Minuten musst du nur **EINMAL** machen! Danach sind die Modelle fertig und du kannst jederzeit in 7 Sekunden neue Vorhersagen erstellen.

---

## 🆘 Hilfe?

**Problem:** Docker läuft nicht  
**Lösung:** Docker Desktop öffnen und warten, bis der Wal-Icon grün ist

**Problem:** Port 8080 belegt  
**Lösung:** In `docker-compose.yml` den Port ändern (z.B. 9090:80)

**Mehr Details:** Siehe `DOCKER_GUIDE.md`

---

## 🎓 Was macht das System?

RiskRadar analysiert:
- 🔥 **8,6 Millionen** Satelliten-Feuer-Detektionen (NASA FIRMS)
- 🌍 **16.468** Erdbeben (USGS)
- 🌤️ Wetterdaten (OpenMeteo)

Und erstellt:
- 🔮 **72h-Vorhersagen** für 35 Standorte weltweit
- 🗺️ Interaktive Karte mit Risiko-Scores
- 📊 CSV-Ergebnisse für weitere Analysen

---

## 📚 Weitere Dokumentation

- `DOCKER_GUIDE.md` - Vollständige Docker-Anleitung
- `FIRMS_UPDATE_ANLEITUNG.md` - Daten aktualisieren
- `PROJEKT_ABSCHLUSS.md` - Projekt-Zusammenfassung
- `README.md` - Technische Details

---

## 🎉 Das wars!

**Viel Erfolg bei der Präsentation!** 🚀

Bei Fragen: Siehe `DOCKER_GUIDE.md` → Troubleshooting
