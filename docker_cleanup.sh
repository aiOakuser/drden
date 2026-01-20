#!/usr/bin/env bash
set -euo pipefail

container="${1:-}"
if [[ -z "$container" ]]; then
  echo "Usage: $(basename "$0") <container-name-or-id>" >&2
  exit 2
fi

if ! docker inspect "$container" >/dev/null 2>&1; then
  echo "Container '$container' not found; skipping cleanup."
  exit 0
fi

if ! docker stop --time=30 "$container" >/dev/null 2>&1; then
  echo "Container '$container' already stopped; continuing."
fi

if ! docker rm -f "$container" >/dev/null 2>&1; then
  echo "Container '$container' already removed; skipping."
fi
