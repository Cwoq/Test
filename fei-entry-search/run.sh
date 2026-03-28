#!/bin/bash
# ============================================================
# FEI Low Entry Show Search — One-click setup & run
# ============================================================
# Usage: bash run.sh
# ============================================================

set -e

cd "$(dirname "$0")"
echo ""
echo "============================================"
echo "  FEI Low Entry Show Search"
echo "  Finding shows with fewest competitors"
echo "============================================"
echo ""

# --- Step 1: Create virtual environment ---
if [ ! -d ".venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv .venv
else
    echo "[1/5] Virtual environment exists, skipping."
fi

# --- Step 2: Activate venv ---
echo "[2/5] Activating virtual environment..."
source .venv/bin/activate

# --- Step 3: Install dependencies ---
echo "[3/5] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet flask sqlalchemy pandas jinja2 beautifulsoup4 lxml requests
echo "       Done."

# --- Step 4: Seed the database ---
echo "[4/5] Seeding database with 5 years of historical FEI show data..."
echo "       (26 real North American venues, ~600 shows, ~2400 classes)"
PYTHONPATH=. python scripts/seed_data.py

# --- Step 5: Launch the dashboard ---
echo ""
echo "[5/5] Launching dashboard..."
echo ""
echo "============================================"
echo ""
echo "  Dashboard is ready!"
echo ""
echo "  Open your browser to:"
echo ""
echo "    http://localhost:5000"
echo ""
echo "  - All shows sorted fewest entries first"
echo "  - Click column headers to re-sort"
echo "  - Use filters to narrow by star level,"
echo "    state, country, or week range"
echo "  - Click 'Calendar' for heatmap view"
echo "  - Click any venue name for year-by-year detail"
echo ""
echo "  Press Ctrl+C to stop the server."
echo ""
echo "============================================"
echo ""

PYTHONPATH=. python -m src.web.app
