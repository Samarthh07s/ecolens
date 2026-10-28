"""
EcoLens configuration.

Everything you might want to tweak lives here: API endpoints, timeouts,
default city, score weights, thresholds and the About-page details.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# In a PyInstaller build, resources are unpacked under a temporary directory,
# while the executable directory is the user-visible place for persistent data.
RUNTIME_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else BASE_DIR

# ---------------------------------------------------------------------------
# App / server
# ---------------------------------------------------------------------------
APP_NAME = "EcoLens"
APP_TAGLINE = "AI Environmental Analyzer"
HOST = "127.0.0.1"
PORT = 5000

# SQLite file. Created automatically on first run. Tests override this
# with the ECOLENS_DB environment variable so they never touch real data.
DB_PATH = os.environ.get("ECOLENS_DB", os.path.join(RUNTIME_DIR, "ecolens.db"))

# ---------------------------------------------------------------------------
# Data sources (Open-Meteo: free, no API key needed)
# ---------------------------------------------------------------------------
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

HTTP_TIMEOUT_SECONDS = 8      # per request
HTTP_RETRIES = 2              # extra attempts after the first one
HTTP_BACKOFF_SECONDS = 0.6    # wait between attempts (grows linearly)
PAST_DAYS = 2                 # hourly history pulled from the API
FORECAST_DAYS = 2             # hourly forecast pulled from the API

# ---------------------------------------------------------------------------
# Default location
# ---------------------------------------------------------------------------
DEFAULT_LOCATION = {
    "name": "Pune, Maharashtra, India",
    "lat": 18.5204,
    "lon": 73.8567,
}

# ---------------------------------------------------------------------------
# Health score weights (must add up to 1.0). If noise has not been
# measured it is dropped and the remaining weights are renormalised.
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "aqi": 0.40,
    "heat_index": 0.25,
    "uv": 0.20,
    "humidity": 0.10,
    "noise": 0.05,
}

# Overall label bands for the 0-100 score (lower bound inclusive).
SCORE_LABELS = [
    (80, "Excellent", "excellent"),
    (60, "Good", "good"),
    (40, "Fair", "fair"),
    (20, "Poor", "poor"),
    (0, "Hazardous", "hazardous"),
]

# Noise bands (dB, approximate)
NOISE_BANDS = [
    (40, "Quiet", "good"),
    (60, "Normal", "moderate"),
    (80, "Loud", "usg"),
    (10_000, "Harmful", "unhealthy"),
]

# Alert thresholds (profile-specific AQI limits live in analysis/recommender.py)
ALERT_UV = 8            # UV index >= this
ALERT_HEAT_INDEX = 40   # heat index (deg C) > this
ALERT_NOISE = 80        # dB > this

# ---------------------------------------------------------------------------
# About page - EDIT THESE with your own details before the demo
# ---------------------------------------------------------------------------
ABOUT = {
    "project_title": "EcoLens - AI Environmental Analyzer",
    "institute": "Your College Name",
    "department": "Department of Computer Engineering",
    "academic_year": "2026-27",
    "team": [
        {"name": "Team Member 1", "roll": "Roll No. 01", "role": "Backend & Analysis"},
        {"name": "Team Member 2", "roll": "Roll No. 02", "role": "Frontend & UI"},
        {"name": "Team Member 3", "roll": "Roll No. 03", "role": "Trends & Testing"},
        {"name": "Team Member 4", "roll": "Roll No. 04", "role": "Documentation"},
    ],
    "guide": "Prof. Guide Name",
    "hod": "Dr. HOD Name",
}
