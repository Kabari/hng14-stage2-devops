#!/usr/bin/env bash
# rolling-update.sh — performs a rolling update of all services.
# Usage: bash rolling-update.sh <git-sha>
# The new container must pass its health check within 60 s before the old one
# is stopped. If it does not, the old container is left running.

set -euo pipefail

SHA="${1:?Usage: rolling-update.sh <git-sha>}"
SERVICES=(api worker frontend)

cd "$(dirname "$0")"

for SERVICE in "${SERVICES[@]}"; do
  echo "▶ Rolling update: $SERVICE → $SHA"

  OLD_CONTAINER=$(docker compose ps -q "$SERVICE" 2>/dev/null || true)

  NEW_CONTAINER=$(
    docker compose run -d \
      --name "${SERVICE}_new_${SHA}" \
      --no-deps \
      "$SERVICE"
  )

  echo "  Waiting for ${SERVICE}_new_${SHA} to become healthy (max 60 s)…"
  DEADLINE=$(( $(date +%s) + 60 ))
  HEALTHY=false
  while [ "$(date +%s)" -lt "$DEADLINE" ]; do
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$NEW_CONTAINER" 2>/dev/null || echo "none")
    if [ "$HEALTH" = "healthy" ]; then
      HEALTHY=true
      break
    fi
    sleep 3
  done

  if [ "$HEALTHY" != "true" ]; then
    echo "  ✗ New container did not become healthy within 60 s. Aborting — old container kept."
    docker rm -f "$NEW_CONTAINER" || true
    exit 1
  fi

  echo "  ✓ New container healthy. Stopping old container."
  [ -n "$OLD_CONTAINER" ] && docker rm -f "$OLD_CONTAINER" || true

  docker rename "$NEW_CONTAINER" "${SERVICE}" || true

  echo "  ✓ $SERVICE updated."
done

echo "✅ Rolling update complete."