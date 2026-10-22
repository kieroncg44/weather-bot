#!/bin/bash
cd "$(dirname "$0")"
python3 dashboard.py >/dev/null && open dashboard.html
