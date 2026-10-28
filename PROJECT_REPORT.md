# EcoLens Project Report and Run Guide

## 1. Project title

**EcoLens - AI Environmental Analyzer**

EcoLens is a local web application that analyzes current environmental conditions and explains whether it is healthy to go outside. It combines air quality, temperature, humidity, UV index, and optional noise measurements into an Environmental Health Score from 0 to 100.

The application is designed as a final-year project demonstrator. It uses a transparent rule-based expert system rather than an opaque machine-learning model, so each recommendation can be explained during a project presentation.

## 2. Main features

- Live weather and air-quality data from the Open-Meteo APIs
- City search and browser geolocation
- Environmental Health Score from 0 to 100
- AQI, temperature, humidity, UV, and noise cards
- Explainable score breakdown and risk-pattern detection
- Personalized recommendations for general users, children, elderly users, asthma users, and athletes
- Best two-hour outdoor activity window
- SQLite history and trend analysis
- AQI, temperature, and health-score charts
- Smart alerts for unhealthy air, high UV, dangerous heat, and harmful noise
- Manual or microphone-based approximate noise measurement
- Location comparison page
- Local profile preferences page
- Printable environmental report and PDF save option
- Dark mode
- Responsive mobile layout
- Offline cache for previously loaded locations
- Installable PWA shell with service-worker caching
- CSV history export
- Automated tests with mocked API responses

## 3. Technology stack

| Area | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| Data analysis | Pandas, NumPy |
| HTTP client | Requests |
| Frontend | HTML, CSS, vanilla JavaScript |
| Charts | Bundled Chart.js |
| Browser features | Geolocation API, Web Audio API, Notifications API, Service Worker |
| Testing | pytest |
| External data | Open-Meteo Weather, Air Quality, and Geocoding APIs |

No API key is required.

## 4. Project structure

```text
ecolens/
├── app.py                         Flask pages and JSON API routes
├── config.py                      Configuration, thresholds, weights, team details
├── database.py                    SQLite schema and persistence helpers
├── requirements.txt               Python dependencies
├── run.bat                        Windows one-click launcher
├── README.md                      Original detailed user guide
├── PROJECT_REPORT.md              This report and run guide
├── analysis/
│   ├── analyzer.py                Score calculation and pattern detection
│   ├── recommender.py             Profiles, advice, alerts, best-time window
│   └── trends.py                  Pandas/NumPy history and trend calculations
├── services/
│   └── open_meteo.py              Open-Meteo API integration and cache fallback
├── templates/                     Flask HTML pages
├── static/
│   ├── css/style.css              Application styles and responsive design
│   ├── js/                        Frontend interactions
│   ├── vendor/chart.min.js        Local Chart.js copy
│   ├── manifest.webmanifest       PWA metadata
│   └── sw.js                      Offline shell cache
└── tests/                         Automated tests
```

## 5. Requirements

- Windows 10 or Windows 11
- Python 3.11, 3.12, 3.13, or 3.14
- Internet connection for the first package installation and live API data
- Chrome, Edge, or Firefox

Python 3.15 or newer may not work with the pinned NumPy and Pandas versions.

## 6. Easiest way to run on Windows

1. Open the `ecolens` folder.
2. Double-click **`run.bat`**.
3. Wait for the terminal to show:

   ```text
   Starting EcoLens at http://127.0.0.1:5000
   ```

4. Open this address in a browser:

   ```text
   http://127.0.0.1:5000
   ```

5. Keep the black terminal window open while using the application.
6. Press `Ctrl+C` in the terminal to stop the server.

The launcher creates a local `venv` folder and installs the dependencies automatically on first run.

## 6A. Build and run a Windows EXE

EcoLens can also be packaged as a portable Windows application using PyInstaller. The user does not need to install Python to run the generated executable.

1. Open the project folder.
2. Double-click **`build_exe.bat`**.
3. Wait for the builder to finish.
4. Open the generated folder:

   ```text
   EcoLens-Desktop\EcoLens.exe
   ```

5. Double-click `EcoLens.exe`.
6. The local dashboard opens automatically at `http://127.0.0.1:5000`.

The executable keeps the SQLite database beside itself in the `EcoLens-Desktop` folder. Internet access is still required for fresh Open-Meteo data; cached data works for previously loaded locations.

For distribution, compress the complete `EcoLens-Desktop` folder as a ZIP. Windows SmartScreen may show a warning because the executable is not digitally signed. This is normal for locally built student projects; users can choose **More info → Run anyway** after confirming the file came from the project source.

## 7. Manual run commands

Open Command Prompt or PowerShell in the project folder:

```bat
cd /d C:\Users\Om Sai\Downloads\ecolens
```

Create a virtual environment:

```bat
py -3.14 -m venv venv
```

Activate it in Command Prompt:

```bat
venv\Scripts\activate
```

Activate it in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bat
python -m pip install -r requirements.txt
```

Start the application:

```bat
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## 8. Running the tests

From the project folder, with the virtual environment activated:

```bat
python -m pytest -q
```

The upgraded project currently contains **62 passing tests** when run with the pinned dependencies.

The tests cover:

- Page rendering
- API validation
- Mocked weather and air-quality responses
- Offline cache behavior
- Noise submission
- Alert creation and deduplication
- User-profile persistence
- Location comparison
- Trends and CSV export
- CSV formula-injection protection
- Analyzer and recommendation rules

## 9. Recommended final-year demonstration

### Demonstration sequence

1. Start EcoLens with `run.bat`.
2. Open the Dashboard and show the current location.
3. Explain the five environmental cards.
4. Point out the Environmental Health Score.
5. Click **How is this calculated?** and show the weighted breakdown.
6. Change the profile to **Asthma / Respiratory** and refresh.
7. Explain how the same environmental data produces stricter advice for a sensitive profile.
8. Open **Compare** and compare two cities.
9. Open **Trends** and show the charts and estimated next six hours.
10. Open **Alerts** and show threshold-based alerts.
11. Open **Settings** and save a display name/profile.
12. Return to the Dashboard and click **Print report**.
13. Use the browser print dialog to save the report as a PDF.
14. Toggle dark mode and resize the browser to demonstrate responsive design.

### Suggested explanation

> EcoLens collects current weather and air-quality information from Open-Meteo. The analyzer converts each measurement into a 0-to-100 sub-score, applies health-oriented weights, and uses a weakest-link rule so that one dangerous factor cannot be hidden by good conditions elsewhere. The result is a transparent score and a profile-specific recommendation. History is stored in SQLite and analyzed with Pandas and NumPy for trends.

## 10. Score calculation

The default score weights are:

| Factor | Weight |
|---|---:|
| Air quality | 40% |
| Heat index | 25% |
| UV index | 20% |
| Humidity | 10% |
| Noise | 5% |

When noise has not been measured, its weight is removed and the remaining weights are renormalized.

The score labels are:

| Score | Label |
|---:|---|
| 80-100 | Excellent |
| 60-79 | Good |
| 40-59 | Fair |
| 20-39 | Poor |
| 0-19 | Hazardous |

## 11. Important limitations

- Open-Meteo air-quality values are model-based and are not street-level sensor readings.
- Browser microphone noise readings are approximate and uncalibrated.
- Health recommendations are general educational guidance, not medical advice.
- The six-hour trend estimate is a simple linear extrapolation, not a weather forecast.
- Live data requires internet access; previously loaded locations can use the local cache when offline.

## 12. Troubleshooting

### Python is not found

Install Python 3.13 or another supported version and enable **Add Python to PATH** during installation. Then reopen the terminal and run:

```bat
python --version
```

### The browser does not open

Open this address manually:

```text
http://127.0.0.1:5000
```

### Port 5000 is already in use

Close the other Flask process, or change `PORT` in `config.py`.

### API data is unavailable

Check the internet connection. If the location was loaded earlier, EcoLens can display cached data with an Offline badge.

### Microphone or location access is blocked

Use the browser address-bar permissions to allow access, or use city search and manual noise entry instead.

### Test dependencies are missing

Run:

```bat
python -m pip install -r requirements.txt
```

## 13. Personalization before submission

Open `config.py` and replace the placeholder values in the `ABOUT` section:

- College or institute name
- Department
- Academic year
- Team member names and roll numbers
- Project guide
- Head of Department

Then restart the application.

## 14. Future scope

- IoT sensors for hyper-local PM2.5, temperature, humidity, and noise
- Machine-learning prediction trained on stored readings
- Mobile application or richer PWA installation
- Background alerts for saved locations
- User authentication and cloud synchronization
- Community environmental reports
