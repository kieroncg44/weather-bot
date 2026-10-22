#!/bin/bash
cd "$(dirname "$0")"
python3 scan.py
echo
read -p "Press Return to close..."
