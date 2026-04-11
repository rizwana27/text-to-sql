#!/usr/bin/env bash
# infra/install_app.sh — Install Python dependencies, seed DB, build frontend.
# Run as ubuntu user AFTER setup.sh and configure_env.sh have been executed.

set -e  # Exit immediately on any error

APP_DIR="${APP_DIR:-/opt/text-to-sql}"   # Root of the cloned repository
cd "$APP_DIR"

echo "=== [1/7] Creating Python virtual environment ==="
python3.11 -m venv venv                         # Isolate packages from system Python
source venv/bin/activate                         # Activate for all subsequent commands

echo "=== [2/7] Installing Python dependencies ==="
pip install --upgrade pip                        # Ensure pip itself is up to date
pip install -r requirements.txt                  # Install all pinned packages

echo "=== [3/7] Loading .env ==="
set -a                                           # Export all variables
source .env                                      # Read secrets into environment
set +a

echo "=== [4/7] Creating database schema ==="
python -c "
from model.database import get_engine
from model.schema import Base
engine = get_engine()
Base.metadata.create_all(engine)
print('Schema created.')
"

echo "=== [5/7] Seeding database from Olist CSVs ==="
# Expects CSV files in data/raw/. Set KAGGLE_AUTO_DOWNLOAD=1 to download automatically.
python -m data.seed

echo "=== [6/7] Building ChromaDB schema index ==="
python -m agent.build_index                      # Embed semantic schema into vector store

echo "=== [7/7] Building React frontend ==="
cd frontend
npm ci                                           # Clean install from package-lock.json (reproducible)
npm run build                                    # TypeScript compile + Vite bundle → dist/
cd ..

echo "✅ Installation complete."
echo "Next: sudo systemctl enable texttosql && sudo systemctl start texttosql"
