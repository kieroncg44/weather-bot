#!/bin/bash
cd "$(dirname "$0")"
python3 report.py
echo
read -p "Press Return to close..."
