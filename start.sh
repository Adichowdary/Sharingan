#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Sharingan — Kali Linux / Linux / macOS Startup Script
#  Usage: ./start.sh
#         ./start.sh setup
#         ./start.sh check
# ═══════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Find python3
PYTHON=$(command -v python3 || command -v python || echo "")
if [ -z "$PYTHON" ]; then
    echo "❌ Python 3 not found. Install it with: sudo apt install python3 python3-pip"
    exit 1
fi

# Use venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

case "${1}" in
    setup)
        echo "⚙️  Running Sharingan setup…"

        # Create venv if it doesn't exist
        if [ ! -d "venv" ]; then
            echo "📦 Creating virtual environment…"
            $PYTHON -m venv venv
            source venv/bin/activate
        fi

        $PYTHON sharingan.py setup
        ;;
    check)
        $PYTHON sharingan.py check
        ;;
    *)
        $PYTHON sharingan.py "$@"
        ;;
esac
