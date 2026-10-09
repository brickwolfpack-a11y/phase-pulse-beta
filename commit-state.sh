#!/usr/bin/env bash
set -euo pipefail
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add state.json report.json
if git diff --cached --quiet; then exit 0; fi
git commit -m 'Persist PHASE PULSE check state [skip ci]'
# Fail closed on conflicts. Never deliver before the reservation is durable.
git push origin HEAD
