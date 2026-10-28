# Civic Cascade Radar (Windows)

This project provides a smart-city analytics dashboard with **Civic Cascade Radar**, a ranked list of potential waterlogging hotspots.

## Quick start

### Requirements
- Windows 10/11
- Python 3.11 or newer (Python 3.12 is a good choice)
- Node.js 20 or newer (LTS recommended)
- Internet access for the first dependency installation and live map/weather services

### Run
1. Extract this ZIP to a folder such as `D:\civic-cascade-radar`.
2. Open the extracted folder.
3. Double-click `run_windows.bat`.
4. Wait for the backend and frontend terminal windows to start.
5. Open **http://localhost:3000**.
6. API documentation: **http://localhost:8000/docs**.
7. Radar API test: **http://localhost:8000/cascade/radar?rainfall=80&top_n=10**.

The first launch installs Python and Node dependencies and can take several minutes. Keep both terminal windows open while using the app. To stop the app, close both terminal windows.

## Manual start (if the batch file fails)

Backend, in PowerShell:

```powershell
cd .\backend
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Frontend, in a second PowerShell window:

```powershell
cd .\frontend
npm ci
npm run dev
```

If PowerShell blocks activation, use `venv\Scripts\python.exe -m pip install -r requirements.txt` and `venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000` instead.

## Civic Cascade Radar

Open the **Cascade** tab in the existing right-hand panel. It fetches ranked hotspot results from `GET /cascade/radar`, shows the returned score breakdown and source notes, and lets you select a hotspot to center and highlight it on the existing map. You can enter a 0–500 mm what-if rainfall scenario and run the analysis. The scenario is simulated input, not a live measurement or forecast. The panel also labels synthetic weather fallback when the API reports it.

The score is a transparent demonstration heuristic, **not a validated flood forecast**. Garbage proximity is treated as a possible local pressure signal, not proof that garbage caused flooding. Rainfall may come from Open-Meteo or from the existing service's clearly labelled synthetic fallback. Groundwater-potential values are contextual only. Do not use this demo score for emergency decisions.

## Frontend verification (Windows PowerShell)

From the project root, run these commands in the frontend directory after the backend is running in a separate terminal:

```powershell
cd .\frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

The commands above are separate checks: lint checks style/rules, TypeScript checks static types, and the production build checks Next.js compilation. If `npm ci` fails, first check the Node.js LTS installation and network access, then share the full npm error output. Do not copy `node_modules` from another machine.

## Optional API keys

The core dashboard and radar can run without the optional keys. If you want the corresponding integrations, copy `backend/.env.example` to `backend/.env` and add your own keys. Copy `frontend/.env.example` to `frontend/.env.local` only if you use the optional Cesium feature. Do not share or commit `.env` files, API keys, or tokens.

## Troubleshooting

- **Port 8000 or 3000 is busy:** close the other app using that port, or stop its terminal.
- **`py` / Python not found:** install Python and enable “Add Python to PATH”.
- **`npm` not found:** install Node.js LTS and reopen the terminal.
- **Radar returns 404:** ensure the backend terminal is running from this extracted bundle, then refresh the page.
- **Radar returns 500:** check the backend terminal for the traceback and open `/docs` to confirm the route is loaded.
- **No live weather:** the service may use synthetic fallback data; the API marks the source. Internet/API availability can affect other live services.

## Validation notes

The backend radar endpoint has been exercised in an isolated environment. Frontend build status depends on running the frontend checks against this bundle: from `frontend`, run `npm ci`, `npm run lint`, `npx tsc --noEmit`, and `npm run build`. These checks do not replace browser-level integration testing.
