#!/usr/bin/env bash
# deploy.sh — publish the site. The branch decides the environment:
#   main    -> production  https://6b62.com      (container: website,     port 8088, nginx/main.conf)
#   staging -> staging      https://new.6b62.com   (container: website-new, port 8089, nginx/staging.conf, private)
# Run on a machine with tailnet access + SSH to pi-two. Builds site/index.html (exactly 27,490 bytes),
# copies site/ and the nginx config to the matching data dir, pre-gzips the text files (nginx gzip_static),
# validates and reloads nginx in that container (no downtime), then checks the origin byte count.
# Pass a branch name as $1 to override the auto-detected one.
set -euo pipefail
cd "$(dirname "$0")"
HOST=${WEBSITE_HOST:-pi-two}
SIZE=27490
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)}"
case "$BRANCH" in
  main)    W=/home/kbauer/data/website;     CONTAINER=website;     PORT=8088; PUBHOST=6b62.com;;
  staging) W=/home/kbauer/data/website-new; CONTAINER=website-new; PORT=8089; PUBHOST=new.6b62.com;;
  *) echo "deploy.sh: unknown branch '$BRANCH' (expected 'main' or 'staging')" >&2; exit 1;;
esac
echo "Deploying branch '$BRANCH' -> container '$CONTAINER'  (https://$PUBHOST)"

./build.py >/dev/null || { echo "deploy.sh: build failed, nothing deployed" >&2; exit 1; }

tar czf - --owner=0 --group=0 site nginx |
  ssh -o BatchMode=yes "$HOST" "W='$W' CONTAINER='$CONTAINER' CONF='$BRANCH.conf'; "'set -e
    T=$(mktemp -d); trap "rm -rf \"$T\"" EXIT
    tar xzf - -C "$T"
    find "$T/site" -type f \( -name "*.html" -o -name "*.css" -o -name "*.txt" -o -name "*.svg" -o -name "*.json" \) -exec gzip -9 -k -n {} \;
    mkdir -p "$W/site" "$W/nginx"
    rm -rf "$W/site.new" && cp -a "$T/site" "$W/site.new" && chmod -R a+rX "$W/site.new"
    # the container bind-mounts these two files, so overwrite them in place (same inode)
    cp "$T/nginx/nginx.conf" "$W/nginx/nginx.conf"
    cp "$T/nginx/$CONF" "$W/nginx/default.conf"
    # the container bind-mounts $W/site, so swap the contents and keep the directory
    rm -rf "$W/site.old" && mkdir "$W/site.old" && cp -a "$W/site/." "$W/site.old/" 2>/dev/null || true
    find "$W/site" -mindepth 1 -delete
    cp -a "$W/site.new/." "$W/site/" && rm -rf "$W/site.new"
    docker exec "$CONTAINER" nginx -t -q && docker exec "$CONTAINER" nginx -s reload && echo "nginx reloaded"'

origin=$(ssh -o BatchMode=yes "$HOST" "curl -s -H 'Accept-Encoding: identity' http://127.0.0.1:$PORT/ | wc -c")
if [ "$origin" = "$SIZE" ]; then echo "origin: $origin B (ok)"; else echo "origin: $origin B, expected $SIZE" >&2; exit 1; fi
# Every version is exactly $SIZE bytes, so compare content, not size.
osum=$(ssh -o BatchMode=yes "$HOST" "curl -s -H 'Accept-Encoding: identity' http://127.0.0.1:$PORT/ | sha256sum" | cut -c1-16)
psum=$(curl -s -m 8 -H 'Accept-Encoding: identity' "https://$PUBHOST/" | sha256sum | cut -c1-16)
fsum=$(curl -s -m 8 -H 'Accept-Encoding: identity' "https://$PUBHOST/?deploy=$(date +%s%N)" | sha256sum | cut -c1-16)
[ "$fsum" = "$osum" ] && echo "public (fresh): same bytes as the origin" || echo "public (fresh): DIFFERENT from the origin, so Cloudflare rewrites the body" >&2
[ "$psum" = "$osum" ] && echo "public (bare URL): up to date" || echo "public (bare URL): still the previous copy from Cloudflare's cache"
echo "Reminder: purge the Cloudflare cache after a deploy (Caching -> Configuration -> Purge Everything), or wait up to 1 h."
