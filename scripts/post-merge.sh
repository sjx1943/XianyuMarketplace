#!/bin/bash
set -e

echo "=== Post-merge setup ==="

# Install / sync Python dependencies
echo "[1/1] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "=== Post-merge setup complete ==="
