# 🔥 NASA FIRMS Data Update - Anleitung

## Problem
Die lokalen FIRMS-Daten reichen nur bis **22. Dezember 2025**. Aktuell fehlen **~13 Tage** (23. Dez 2025 - 4. Jan 2026).

## Lösung: NASA FIRMS API

### 📋 Schritt-für-Schritt Anleitung

#### 1. NASA FIRMS MAP_KEY beantragen (KOSTENLOS!)

1. Gehe zu: **https://firms.modaps.eosdis.nasa.gov/api/area/**
2. Klicke auf **"Request a Key"** oder **"Get API Key"**
3. Fülle das Formular aus:
   - Name
   - Email
   - Organization (z.B. "FOM Hochschule")
   - Use Case: "Academic research - wildfire risk prediction"
4. Du erhältst sofort einen **MAP_KEY** per Email

#### 2. MAP_KEY in .env eintragen

Öffne die `.env`-Datei und füge hinzu:

```bash
# NASA FIRMS API
FIRMS_MAP_KEY=your_actual_map_key_here
```

**Beispiel:**
```bash
FIRMS_MAP_KEY=abc123def456ghi789jkl012mno345pqr678stu901vwx234yz
```

#### 3. Update-Skript ausführen

```bash
cd app
python update_firms_data.py
```

Das Skript wird:
- Die letzten 7 Tage von der NASA FIRMS API herunterladen
- Die lokale `fire_nrt_M-C61_699365.csv` aktualisieren
- Duplikate automatisch entfernen

#### 4. Dataset & Modelle neu bauen

```bash
# Dataset neu generieren (mit aktuellen Daten)
python build_sensor_dataset.py

# Modelle neu trainieren
python train_sensor_model.py --model fire
python train_sensor_model.py --model quake

# Neue Vorhersage erstellen
python run_real_forecast.py
```

---

## ⚠️ Wichtige Hinweise

### Free Tier Limitierungen
- **Maximal 7 Tage** auf einmal abrufbar (NRT = Near Real-Time)
- **Keine Rate Limits** für registrierte User
- **Global coverage** (alle Feuer weltweit)

### Wenn mehr als 7 Tage fehlen
Falls mehr als 7 Tage Daten fehlen, musst du das Skript mehrmals ausführen:

```bash
# 1. Erste 7 Tage holen
python update_firms_data.py

# 2. Nächste 7 Tage holen (automatisch)
python update_firms_data.py

# etc.
```

Das Skript erkennt automatisch, welche Daten fehlen!

### Alternative: Manueller Download
Falls die API nicht funktioniert, kannst du die Daten auch manuell herunterladen:

1. Gehe zu: https://firms.modaps.eosdis.nasa.gov/download/
2. Wähle:
   - **Data Source**: MODIS C6.1
   - **Time Range**: "Last 7 days" oder custom
   - **Area**: Global oder Custom Bounding Box
3. Download die CSV-Datei
4. Kopiere sie nach `FIRMS_2025_NRT/fire_nrt_M-C61_699365.csv`

---

## 🎯 Erwartetes Ergebnis

Nach dem Update solltest du haben:
- **FIRMS Daten**: 22. Dez 2023 - 4. Jan 2026 (heute!)
- **~8,7 Millionen** Feuer-Detektionen
- **Aktuelle Vorhersagen** basierend auf neuesten Daten

---

## 🔍 Testen

Prüfe, ob die Daten aktualisiert wurden:

```bash
# Letztes Datum in der NRT-Datei checken
tail FIRMS_2025_NRT/fire_nrt_M-C61_699365.csv

# Sollte zeigen: 2026-01-04 (oder aktuelles Datum)
```

---

## 📚 Weitere Infos

- **FIRMS API Doku**: https://firms.modaps.eosdis.nasa.gov/api/
- **Data Format**: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt
- **Support**: support@earthdata.nasa.gov

---

**Erstellt am**: 4. Januar 2026  
**Letztes Update**: 4. Januar 2026
