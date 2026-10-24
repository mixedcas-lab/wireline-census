#!/usr/bin/env bash
# Rebuild the wireline list from the adc-census record cache and publish it to GitHub Pages.
# No IEEE API calls: adc-census (its own cron job) fetches the venues; this only re-reads them.
#
#   37 6 * * *  PYTHON=/path/to/python3 /path/to/wireline-census/scripts/update.sh >> /path/to/wireline-census/logs/update.log 2>&1
#
# Environment (optional): PYTHON (default python3), WIRELINE_CENSUS_CACHE (default: "cache" in collector/venues.json).
set -uo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"

echo "=== $(date '+%F %T') ==="
git pull --rebase --quiet origin main || { echo "git pull failed"; exit 1; }

"$PY" collector/build.py
status=$?

git add data/papers.json data/meta.json
if ! git diff --cached --quiet; then
  n=$("$PY" -c "import json;print(json.load(open('data/meta.json')).get('core',0))")
  git commit --quiet -m "data: update $(date +%F) ($n wireline papers)"
  # someone may have edited annotations.csv on the web meanwhile: rebase once and retry
  if git push --quiet origin main || { git pull --rebase --quiet origin main && git push --quiet origin main; }; then
    echo "pushed ($n wireline papers)"
  else
    echo "git push failed"; status=1
  fi
else
  echo "no changes"
fi
exit "$status"
