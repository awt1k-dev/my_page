#!/usr/bin/env bash
# Deploy or update awtik.ru on the VPS.
#
# The server has no git installed, so the code is fetched as a GitHub tarball.
# Everything except .env is replaced on every run; the Caddy certificate lives
# in a Docker volume and survives redeploys.
#
# Usage:
#   ./deploy/deploy.sh
#
# Overrides:
#   APP_DIR=~/awtik_landing REPO=awt1k-dev/my_page BRANCH=main ./deploy/deploy.sh

set -euo pipefail

REPO="${REPO:-awt1k-dev/my_page}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-$HOME/awtik_landing}"
TARBALL="${TARBALL:-https://github.com/$REPO/archive/refs/heads/$BRANCH.tar.gz}"

COMPOSE=(docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml)

# Re-exec from /tmp: the update wipes APP_DIR together with this script.
if [ "${1:-}" != "--inner" ]; then
	inner="$(mktemp /tmp/awtik-deploy.XXXXXX.sh)"
	cp "$0" "$inner"
	exec bash "$inner" --inner
fi

tmp=""
trap 'rm -rf "${tmp:-}" "$0"' EXIT

mkdir -p "$APP_DIR"
cd "$APP_DIR"

if [ ! -f .env ]; then
	cp .env.example .env
	echo "Created $APP_DIR/.env from .env.example." >&2
	echo "Set PUBLIC_BASE_URL and TRUST_PROXY_HEADERS=true, then re-run." >&2
	exit 1
fi

tmp="$(mktemp -d)"
echo "==> Fetching $REPO@$BRANCH"
curl -fsSL "$TARBALL" -o "$tmp/src.tar.gz"
tar -xzf "$tmp/src.tar.gz" -C "$tmp"
src="$(find "$tmp" -mindepth 1 -maxdepth 1 -type d -name 'my_page-*' | head -n1)"
if [ -z "$src" ]; then
	echo "Unexpected tarball layout in $tmp" >&2
	exit 1
fi

echo "==> Stopping containers"
"${COMPOSE[@]}" down --remove-orphans || true

echo "==> Replacing sources (keeping .env)"
find . -mindepth 1 -maxdepth 1 ! -name .env -exec rm -rf {} +
cp -a "$src/." .

echo "==> Building and starting"
"${COMPOSE[@]}" up -d --build --remove-orphans
docker image prune -f >/dev/null

host_port="$(sed -n 's/^PORT=//p' .env | tail -n1)"
host_port="${host_port:-8000}"

echo "==> Waiting for the app on 127.0.0.1:$host_port"
for _ in $(seq 1 30); do
	if curl -fsS "http://127.0.0.1:$host_port/healthz" >/dev/null 2>&1; then
		echo "==> OK: https://awtik.ru/"
		exit 0
	fi
	sleep 2
done

echo "App did not become healthy; check: ${COMPOSE[*]} logs web" >&2
exit 1
