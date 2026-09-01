#!/bin/bash
# Double-click this file in Finder to launch CheckPrinter.
# First launch sets up a local Python environment (one-time, ~30s).
set -e
cd "$(dirname "$0")"

# 1) Make sure Tk (the GUI toolkit) is available for Homebrew Python 3.14.
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Installing Tk support (one time)..."
    brew install python-tk@3.14 || {
        echo "Could not install python-tk automatically."
        echo "Run:  brew install python-tk@3.14"
        read -r -p "Press Return to close." _
        exit 1
    }
fi

# 2) Create the local virtual environment and install dependencies once.
if [ ! -d .venv ]; then
    echo "Setting up (one time)..."
    python3 -m venv --system-site-packages .venv
    ./.venv/bin/python -m pip install -q --upgrade pip
    ./.venv/bin/python -m pip install -q -r requirements.txt
fi

# 3) Launch the app.
exec ./.venv/bin/python -m checkprinter
