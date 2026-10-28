# EcoLens – AI Environmental Analyzer

EcoLens shows how healthy it is outside **right now** – air quality, temperature, humidity, UV and noise – rolls it into one **Environmental Health Score (0–100)**, explains risky patterns in plain English, gives advice for your health profile, keeps history for trend analysis and raises alerts when limits are crossed.

It runs on your own computer as a small website (Flask + SQLite). Live data comes from the free **Open-Meteo** APIs (no API key needed).

The capstone edition also includes a modern responsive app shell, local profile preferences, location comparison, printable environmental reports, installable PWA shell, offline asset caching, and progressive enhancement when browser features such as notifications, GPS, or microphone access are unavailable.

| Feature | Where in the app |
|---|---|
| 1. Live Environment Dashboard (search, my location, 5 colour-coded cards, noise meter) | **Dashboard** |
| 2. AI Environment Analyzer (score ring, condition label, pattern detection, "How is this calculated?") | **Dashboard** (top) |
| 3. Personalised Recommendations (profile, "Go outside?" verdict, actions, best 2-hour window) | **Dashboard** (bottom) |
| 4. History & Trends (SQLite, Pandas, NumPy trend + 6-hour estimate, CSV) | **Trends** |
| 5. Smart Alerts (banners, stored alerts, clear all, browser notifications) | **Dashboard** banners + **Alerts** |

---

## 1. Prerequisites

1. **Install Python** (one time only)
   - Go to <https://www.python.org/downloads/> and download **Python 3.13** (3.11, 3.12 and 3.14 also work).
   - Run the installer. On the **first screen tick ☑ "Add python.exe to PATH"**, then click **Install Now**.
2. **Check it worked**
   - Press `Win + R`, type `cmd`, press Enter.
   - Type `python --version` and press Enter. You should see something like `Python 3.13.9`.
   - If you see *"'python' is not recognized"* or the Microsoft Store opens, re-run the installer, choose **Modify**, and make sure **"Add Python to environment variables"** is ticked.
3. **Internet connection** – needed for the first run (to install packages) and for live data. After that the app can show cached data offline.
4. **Google Chrome or Microsoft Edge** (latest). Firefox works too, but microphone and notification prompts look different.

> Python 3.15 or newer is **not** supported yet (the pinned NumPy/Pandas versions have no installers for it). `run.bat` automatically picks a supported version if you have several installed.

---

## 2. Extract the ZIP with WinRAR

1. Find **`EcoLens.zip`** (usually in your **Downloads** folder).
2. **Right-click** it → choose **"Extract to EcoLens\"**.
   (On Windows 11 you may need to click **"Show more options"** first. Without WinRAR you can use **Extract All…**.)
3. A new folder **`EcoLens`** appears next to the ZIP, e.g. `C:\Users\<you>\Downloads\EcoLens\`.
   Open it – you should see `app.py`, `run.bat`, `README.md` and folders `analysis`, `services`, `static`, `templates`, `tests`.
   *If you see another `EcoLens` folder inside, open that one – that's the project folder.*
4. **Important:**
   - **Do NOT** double-click `run.bat` inside WinRAR's window or the ZIP preview. Windows runs it from a temporary folder that is deleted, and nothing works. (`run.bat` detects this and tells you.)
   - **Avoid long or special-character paths.** A simple place like `C:\Projects\EcoLens` or `D:\EcoLens` is best. Avoid `&`, `%`, `!`, `#` and non-English letters in folder names, and avoid OneDrive-synced folders if you have problems.

---

## 3. Run it – Method A (easiest): double-click `run.bat`

Open the extracted `EcoLens` folder and **double-click `run.bat`**. A black window opens and does four steps:

| Step | What you see | What is happening |
|---|---|---|
| `[1/4] Using Python:` `Python 3.13.x` | Which Python was found | It looks for Python 3.13, 3.12, 3.14 or 3.11 |
| `[2/4] Creating virtual environment in "venv" (first run only)...` | Takes ~10–20 s, first time only | Makes a private `venv` folder so packages don't affect the rest of your PC |
| `[3/4] Installing / checking packages (first run takes 1-3 minutes)...` | Quiet for a while – be patient | Downloads Flask, Requests, NumPy, Pandas, pytest. Later runs take 2–3 seconds |
| `[4/4] Starting EcoLens at http://127.0.0.1:5000` | The server lines below | The app is running |

After ~3 seconds your browser opens **http://127.0.0.1:5000** automatically.

**Keep the black window open** while you use EcoLens – closing it stops the app. To stop, click the window and press **Ctrl + C** (then **Y** if asked), or just close it.

If Windows shows **"Windows protected your PC"**, click **More info → Run anyway** (it's a plain text batch file you can open in Notepad to check).
If **Windows Firewall** asks about Python, you can click **Cancel** – the app only listens on your own computer (127.0.0.1).

---

## 4. Run it – Method B: Command Prompt or VS Code terminal

1. Open **Command Prompt** (`Win + R` → `cmd`) **or** open the `EcoLens` folder in **VS Code** and use **Terminal → New Terminal**.
2. Go to the project folder (change the path to yours):
   ```bat
   cd /d C:\Users\<you>\Downloads\EcoLens
   ```
3. Create a virtual environment (first time only):
   ```bat
   python -m venv venv
   ```
4. Activate it:
   ```bat
   venv\Scripts\activate
   ```
   Your prompt now starts with `(venv)`.
   *VS Code PowerShell error "running scripts is disabled"?* Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or switch the terminal to **Command Prompt** with the ⌄ next to the + button.
5. Install the packages:
   ```bat
   pip install -r requirements.txt
   ```
6. Start the app:
   ```bat
   python app.py
   ```
7. Open **http://127.0.0.1:5000** in Chrome or Edge.

Next time you only need steps 2, 4 and 6.

**Optional – run the automated tests** (59 tests, no internet needed, API responses are mocked):
```bat
python -m pytest -q
```
Expected last line: `59 passed in 1.2s` (time varies).

---

## 5. Expected output guide

### 5.1 Terminal

After `[4/4]` (or after `python app.py`) you should see exactly this (the database path will be your folder):

```
============================================================
  EcoLens - AI Environmental Analyzer
  Database : C:\Users\<you>\Downloads\EcoLens\ecolens.db
  Open     : http://127.0.0.1:5000
  Stop     : press CTRL+C in this window
============================================================
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
```

The yellow/red **WARNING** line is normal for every Flask project run on a laptop – it is not an error.
Each time the browser asks for something, a line is added, e.g.:

```
127.0.0.1 - - [24/Oct/2026 21:40:12] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Oct/2026 21:40:14] "GET /api/current?lat=18.5204&lon=73.8567&name=Pune...&profile=general HTTP/1.1" 200 -
```

`200` = OK. `503` on `/api/current` means the weather service couldn't be reached and nothing was cached yet (check internet). The SQLite file **`ecolens.db`** is created automatically on first run.

### 5.2 Dashboard (http://127.0.0.1:5000)

*Sample values below are illustrative for Pune on an October afternoon – yours will be today's real data.*

1. **Top row** – city search box, **Use my location**, **Profile** selector (General).
2. **Location bar** – "Pune, Maharashtra, India", a green **● Live** badge, *Last updated: 24 Oct, 02:15 PM (just now)*, coordinates, and a green **Refresh** button. While loading, grey shimmering **skeleton** blocks are shown.
3. **Alert banners** (only when a limit is crossed), e.g. an orange *WARNING – Very high UV: index 8* with "Avoid sun 11:00-16:00; use SPF 50+ and a hat." Click × to hide it for this session.
4. **Score ring** – e.g. **64 / 100 – Good**, the ring filling to 64 % in the label's colour, with "Noise not measured — weights renormalised over 4 factors." and the **How is this calculated?** link.
5. **What the analyzer sees** – detected patterns, e.g. *Midday sun alert (High): UV index 8 can burn unprotected skin in about 15 minutes…* or a green "No risky patterns detected".
6. **Five cards** (each has a coloured top edge and a status badge):

   | Card | Sample | Badge colours |
   |---|---|---|
   | Air Quality | **92** US AQI, PM2.5 31.5 µg/m³, PM10 58 µg/m³, a pin on the AQI colour scale | 🟢 Good 0–50 · 🟡 Moderate 51–100 · 🟠 Unhealthy for Sensitive Groups 101–150 · 🔴 Unhealthy 151–200 · 🟣 Very Unhealthy 201–300 · 🟤 Hazardous 301+ (US EPA) |
   | Temperature | **30.8** °C, feels like 31.9 °C, heat index 31.4 °C | 🔵 Cold <10 · 🔵 Cool 10–17 · 🟢 Comfortable 18–26 · 🟡 Warm 27–31 · 🟠 Hot 32–37 · 🔴 Very Hot 38+ |
   | Humidity | **41** %, wind 9 km/h, a filled bar | 🟡 Dry <30 · 🟢 Comfortable 30–60 · 🟡 Humid 61–70 · 🟠 Very Humid >70 |
   | UV Index | **7.6**, today's max 8.4 | 🟢 Low 0–2 · 🟡 Moderate 3–5 · 🟠 High 6–7 · 🔴 Very High 8–10 · 🟣 Extreme 11+ (WHO) |
   | Noise | "—" and grey **Not measured yet** until you measure | 🟢 Quiet <40 · 🟡 Normal 40–60 · 🟠 Loud 60–80 · 🔴 Harmful >80 dB |

7. **Go outside?** – a big verdict: 🟢 **Safe**, 🟠 **Take precautions** or 🔴 **Avoid**, a one-line summary, the reasons (e.g. "UV index 8 – sun protection needed.") and action tiles: **mask / no mask (N95)**, **outdoor exercise**, **sunscreen SPF**, **hydration**, **windows/ventilation** (+ an inhaler tip for the Asthma profile).
8. **Best time to go out** – e.g. **Today 17:00 – 19:00** with chips *AQI ~78, UV ~0.4, Feels ~28 °C*, and a 24-bar AQI outlook where the chosen 2 hours are outlined.

**What the colours mean everywhere:** green = good, yellow = moderate, orange = caution / sensitive groups, red = unhealthy, purple/maroon = very unhealthy / hazardous, blue = cold, grey = no data.

### 5.3 Trends (http://127.0.0.1:5000/trends)

- **Location** dropdown (e.g. "Pune, Maharashtra, India (49 readings)") and **24 h / 7 days / 30 days** buttons.
- An info line, e.g. *25 hourly points (1 live refreshes, 48 API hourly) · moving average: 3 h*.
- Three **stat cards** (Avg / Min / Max) for AQI, temperature and score – e.g. AQI 96 / 61 / 138.
- Three **line charts** (AQI, Temperature, Health Score) each with a filled line, a thin **moving-average** line, and (for AQI and temperature) a **dashed "Estimate (linear)"** extension for the next 6 hours.
- A **trend pill** on each chart: ▲ **Improving** (green), ▼ **Worsening** (red), → **Stable** (grey), or ↗ Rising / ↘ Falling for temperature – from the NumPy `polyfit` slope, with the change per 24 h.
- **Next 6 hours – ESTIMATE** table (e.g. 15:30 → AQI ~94, ~31.2 °C).
- If nothing is stored yet you see **"No history yet – Refresh the dashboard a few times to build history"**. Loading the dashboard once also stores the API's real hourly data for the past 2 days, so charts appear straight away.

### 5.4 Alerts (http://127.0.0.1:5000/alerts)

- A **Thresholds** row: AQI > 150 (General, Athlete), AQI > 100 (Asthma, Children, Elderly), UV ≥ 8, Heat index > 40 °C, Noise > 80 dB.
- A list of stored alerts, newest first, each with **Warning** (orange) or **Critical** (red), title, one-line action, location and time, e.g. *Very high UV: index 8 · Pune, Maharashtra, India · 24 Oct, 01:05 PM (20 min ago)*.
- The same alert type for the same place is stored **once per hour** (no duplicates when you refresh repeatedly).
- A red count bubble on the **Alerts** menu item shows how many are stored.
- Empty state: "No alerts – Nothing has crossed a threshold yet."

### 5.5 About (http://127.0.0.1:5000/about)

Project description, team, guide, HOD, tech stack, data sources, score weights, limitations and future scope.
➡ **Edit your real names** in `config.py` (the `ABOUT` section at the bottom), save, and restart the app.

### 5.6 Every button – what should happen

| Button / control | Expected behaviour |
|---|---|
| **City search** | Type 2+ letters (e.g. `mumb`). After ~0.3 s a list appears: *Mumbai, Maharashtra, India 19.07, 72.88*. Use ↑/↓ + Enter or click. Cards reload for that city; the city is remembered next time. "No matching places found" for nonsense. |
| **Use my location** | Browser asks *"127.0.0.1 wants to know your location"* → **Allow**. The location changes to **"My location"** with your coordinates. If you **Block**, a message explains how to allow it or search instead. |
| **Measure noise** | Browser asks to use the **microphone** → **Allow**. The button shows *Listening… 5 s → 1 s* while the number and meter move live. Then *Noise saved: ~45 dB* appears, the badge changes (e.g. 🟡 Normal), the score now includes noise (5 %), and a talk/clap test above 80 dB raises a *Harmful noise* alert. Values are approximate. |
| **Manual dB + Save** | Type e.g. `72` → **Save** → badge 🟠 Loud, score updates. Values outside 0–140 are rejected with a message. |
| **Refresh** | The icon spins, data reloads, *Last updated* becomes "just now", a new reading is saved for Trends. |
| **Profile** | Switching General → **Asthma / Respiratory** reloads advice: with AQI 120 the verdict changes from **Take precautions** to **Avoid** and an AQI alert appears (limit 100). Your choice is remembered (localStorage). |
| **Theme toggle** (☀ / ☾ top-right) | Switches light ↔ dark instantly; remembered next time. Charts recolour. |
| **How is this calculated?** | Opens a window with the weights table, *your current* factor-by-factor breakdown (value, sub-score, weight used, points), the label bands and every threshold table. Close with ×, Esc or clicking outside. |
| **Download CSV** (Trends) | Downloads `ecolens_history_24h.csv` (or 7d/30d) for the selected location – opens in Excel with columns `timestamp_utc, location, lat, lon, source, aqi, pm25, pm10, temperature, feels_like, humidity, uv, wind, heat_index, noise, score`. |
| **24 h / 7 days / 30 days**, **Location** (Trends) | Charts, stats, trend pills and the CSV link update for that range/place. |
| **Clear all** (Alerts) | Asks *"Delete all stored alerts?"* → OK → *Cleared 3 alerts*, list becomes empty, menu bubble disappears. |
| **Enable notifications** (Alerts) | Only now does the browser ask for notification permission → **Allow** → a test pop-up *"EcoLens notifications enabled"*. From then on, each **new** alert raised on the Dashboard also shows a desktop notification. Click again to **Disable**. |
| **Offline behaviour** | Turn Wi-Fi off and press **Refresh** on a city you've loaded before: after a few seconds (8 s timeout × 3 attempts) the orange badge reads **Offline – showing cached data from 24 Oct, 02:15 PM**. For a city never loaded, a friendly red message with **Try again** appears. |

---

## 6. How to demo this to your examiner (about 5 minutes)

**Before the viva:** run the app once at home on the same laptop (so packages are installed and `ecolens.db` has history), put your names in `config.py`, and open the Dashboard on **General** in light mode.

| Time | Do this | Say this |
|---|---|---|
| 0:00 | Show the Dashboard for **Pune**. | "EcoLens answers one question: is it healthy to be outside right now, and what should I do? Live data comes from the Open-Meteo weather and CAMS air-quality APIs." |
| 0:30 | Point at the five cards and their badges. | "Each card is colour-coded with official bands – US EPA for AQI, WHO for UV, and comfort bands for temperature and humidity." |
| 1:00 | Point at the score ring → click **How is this calculated?** | "The analyzer converts each value to a 0–100 sub-score and combines them: AQI 40 %, heat index 25 %, UV 20 %, humidity 10 %, noise 5 %. Noise isn't measured yet, so its weight is redistributed – here's the live breakdown. A weakest-link rule stops one dangerous factor being averaged away." Close the modal. |
| 1:45 | Point at **What the analyzer sees**. | "Pattern rules detect heat stress, stagnant pollution, strong midday sun and harmful noise, in plain English." |
| 2:00 | Click **Measure noise**, allow the mic, clap/talk for 5 s. | "The Web Audio API estimates noise. It's honest: uncalibrated and approximate – that's in the limitations." Show the badge and the score now including noise. (No mic? Type **85** and **Save** – a harmful-noise alert appears.) |
| 2:45 | Change **Profile** to **Asthma / Respiratory**. | "Recommendations are personalised. Asthma treats AQI above 100 as unsafe instead of 150, so the verdict and mask advice tighten." Point to the **Best time to go out** window. "It scans the next 24 h of forecast and picks the 2 hours with the lowest combined AQI, UV and heat." |
| 3:30 | Search **Delhi** (or Mumbai) with autocomplete. | "Any city works through the geocoding API." (Delhi usually shows much worse AQI – good contrast.) |
| 3:50 | Open **Trends**, switch **24 h → 7 days**. | "Every refresh is stored in SQLite. Pandas resamples to hourly, we show a moving average, and NumPy polyfit gives the trend direction. The dashed line is a linear-regression estimate for 6 hours – clearly labelled as an estimate, not a forecast." Click **Download CSV**. |
| 4:30 | Open **Alerts**. | "Alerts are stored once per location per hour, so refreshing doesn't spam. Browser notifications are opt-in." Click **Enable notifications**, then **Clear all**. |
| 4:50 | Click the **theme toggle**, then open **About**. | "It's responsive, has dark mode, works offline from cached data, and uses no CDN – everything is local. Future scope: IoT sensors, ML prediction, a mobile app and location alerts." |
| 5:00 | (If asked) run `python -m pytest -q` in a terminal. | "59 automated tests with mocked API responses cover the analyzer, recommender, trends and API." |

**Likely examiner questions – short answers**
- *Where is the AI?* – A transparent rule-based expert system (weighted scoring, rules, pattern detection) plus statistical modelling (linear regression). Being explainable is deliberate for health advice; ML prediction is future scope.
- *How accurate is the noise?* – It's uncalibrated; mics differ by 10 dB+. It's an indicator, and manual entry exists for a real sound-meter reading.
- *How accurate is AQI?* – Model-based (CAMS, ~10–40 km grid), not a street sensor; local sources can be worse.
- *What if the internet fails?* – 8 s timeout, 2 retries, then the last good response from SQLite with an Offline badge.
- *Security?* – Parameterised SQL only, server-side input validation, escaped output (Jinja auto-escape + `textContent` in JS), a Content-Security-Policy header, and CSV formula-injection protection.

---

## Project structure

```
EcoLens/
  app.py                  Flask routes (pages) + JSON API
  config.py               Settings: API URLs, timeouts, weights, About-page details
  database.py             SQLite schema + parameterised queries (auto-created)
  services/open_meteo.py  Geocoding, weather and air-quality calls, retry, cache
  analysis/analyzer.py    Health score, bands, heat index, pattern detection
  analysis/recommender.py Profiles, verdict, actions, best time window, alert rules
  analysis/trends.py      Pandas/NumPy history, moving average, trend slope, estimate
  templates/              base, dashboard, trends, alerts, about (Jinja2)
  static/css/style.css    Light/dark responsive styles
  static/js/              common, theme, dashboard, noise, trends, alerts
  static/vendor/          chart.min.js (Chart.js 4.4.7, bundled - no CDN)
  tests/                  pytest suite (mocked API responses)
  requirements.txt        Pinned versions
  run.bat                 Windows one-click launcher
```

### API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/search?q=pune` | City autocomplete |
| GET | `/api/current?lat=&lon=&name=&profile=` | Live data + analysis + recommendations + alerts |
| POST | `/api/noise` `{lat, lon, db, method, profile}` | Save a noise reading, return the re-scored dashboard |
| GET | `/api/history?location=&range=` | Saved readings + list of locations |
| GET | `/api/trends?location=&range=24h\|7d\|30d` | Stats, moving averages, trend direction, 6-h estimate |
| GET / DELETE | `/api/alerts` | List / clear all alerts |
| GET | `/api/export.csv?location=&range=` | Download history as CSV |
| GET | `/api/methodology` | Weights and threshold tables (JSON) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python with **Add python.exe to PATH** ticked, then open a *new* Command Prompt. |
| `[ERROR] Python 3.11 - 3.14 was not found` | Install Python 3.13 from python.org. Python 3.15+ isn't supported yet. |
| Package install fails / `No matching distribution found` | Check internet; use Python 3.11–3.14; delete the `venv` folder and run `run.bat` again. On college networks behind a proxy, try a mobile hotspot. |
| Browser shows *"This site can't be reached"* | The black window must stay open. Wait for `Running on http://127.0.0.1:5000`, then refresh. |
| `Address already in use` / port 5000 busy | Another EcoLens window is already running – close it. Or change `PORT = 5000` in `config.py` to `5050` and open http://127.0.0.1:5050. |
| Red message *"Could not reach the weather service…"* | No internet and nothing cached for that city yet. Connect and click **Try again**. |
| Microphone or location doesn't work | Use `http://127.0.0.1:5000` (not a file path). Click the lock icon left of the address → allow **Microphone** / **Location** → reload. Windows: *Settings → Privacy & security → Microphone / Location* → allow desktop apps/browsers. |
| Charts don't show | Check that `static\vendor\chart.min.js` exists (re-extract the ZIP). |
| Want a fresh start | Stop the app and delete `ecolens.db`. It is recreated automatically. |

---

**Data & credits:** Weather, air-quality (CAMS) and geocoding data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0). Charts by Chart.js (MIT). Health thresholds from US EPA (AQI) and WHO (UV index). Advice is general guidance, not medical advice.
