#!/usr/bin/env bash
# Copies _shared/inmkt.py into every skill folder (each skill must work on its own).
set -e
cd "$(dirname "$0")"
for d in in-*/; do cp _shared/inmkt.py "$d/inmkt.py"; done
echo "copied inmkt.py into $(ls -d in-*/ | wc -l) skill folders"
