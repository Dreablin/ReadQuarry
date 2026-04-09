@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Python is not installed or not on PATH.
  exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is required.
  exit /b 1
)

if not exist ".venv\" (
  echo Creating virtual environment...
  python -m venv .venv
)

call "%~dp0.venv\Scripts\activate.bat"
if errorlevel 1 (
  echo Failed to activate virtual environment.
  exit /b 1
)

python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt

echo Starting ReadQuarry at http://127.0.0.1:8000/
start "" "http://127.0.0.1:8000/"
python main.py
if errorlevel 1 (
  echo.
  echo Server exited with error. Check the output above.
  pause
)
