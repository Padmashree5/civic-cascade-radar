@echo off
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"

echo ================================================
echo   Civic Cascade Radar
 echo ================================================

where py >nul 2>nul
if errorlevel 1 (
  set "PYTHON=python"
) else (
  set "PYTHON=py -3"
)

if not exist "backend\venv\Scripts\python.exe" (
  echo [1/4] Creating Python virtual environment...
  %PYTHON% -m venv "backend\venv"
  if errorlevel 1 goto :error
)

echo [2/4] Installing backend dependencies...
call "backend\venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :error

if not exist "frontend\node_modules\next\package.json" (
  echo [3/4] Installing frontend dependencies. This may take a few minutes...
  pushd "frontend"
  call npm ci
  if errorlevel 1 (popd & goto :error)
  popd
) else (
  echo [3/4] Frontend dependencies already installed.
)

echo [4/4] Starting backend and frontend in separate windows...
start "Civic Cascade Backend" cmd /k "cd /d ""%ROOT%backend"" && call ""%ROOT%backend\venv\Scripts\activate.bat"" && python -m uvicorn app.main:app --reload --port 8000"
start "Civic Cascade Frontend" cmd /k "cd /d ""%ROOT%frontend"" && npm run dev"
echo.
echo Wait for both windows to finish starting.
echo Dashboard: http://localhost:3000
echo API docs:  http://localhost:8000/docs
echo Radar API: http://localhost:8000/cascade/radar?rainfall=80^&top_n=10
echo.
echo Keep both terminal windows open while using the dashboard.
pause
goto :eof

:error
echo.
echo Setup failed. Read the error above. Check that Python and Node.js are installed and on PATH.
pause
exit /b 1
