#!/bin/bash
cd /c/Users/alega/AIB
while true; do
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "auto-save: $(date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "Pushed at $(date)"
  else
    echo "No changes at $(date)"
  fi
  sleep 1800
done
