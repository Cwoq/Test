@echo off
REM ============================================================
REM FEI Low Entry Show Search - One-click setup & run (Windows)
REM ============================================================
REM Usage: double-click this file, or run: run.bat
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================
echo   FEI Low Entry Show Search
echo   Finding shows with fewest competitors
echo ============================================
echo.

REM --- Step 1: Create virtual environment ---
if not exist ".venv" (
    echo [1/5] Creating virtual environment...
    python -m venv .venv
) else (
    echo [1/5] Virtual environment exists, skipping.
)

REM --- Step 2: Activate venv ---
echo [2/5] Activating virtual environment...
call .venv\Scripts\activate.bat

REM --- Step 3: Install dependencies ---
echo [3/5] Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet flask sqlalchemy pandas jinja2 beautifulsoup4 lxml requests

REM --- Step 4: Seed the database ---
echo [4/5] Seeding database with 5 years of historical FEI show data...
set PYTHONPATH=.
python scripts\seed_data.py

REM --- Step 5: Launch the dashboard ---
echo.
echo [5/5] Launching dashboard...
echo.
echo ============================================
echo.
echo   Dashboard is ready!
echo.
echo   Open your browser to:
echo.
echo     http://localhost:5000
echo.
echo   Press Ctrl+C to stop the server.
echo.
echo ============================================
echo.

python -m src.web.app

pause
