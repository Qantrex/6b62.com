#!/usr/bin/env bash
# deploy.sh — publish the site. The branch decides the environment:
#   main    -> production  https://6b62.com      (container: website,     port 8088)
#   staging -> staging      https://new.6b62.com   (container: website-new, port 8089)
# Run on a machine with tailnet access + SSH to pi-two. Copies site/ and nginx/ to the matching
# data dir, pre-gzips the text files (nginx gzip_static), validates and reloads nginx in that
# container (no downtime). Pass a branch name as $1 to override the auto-detected one.
set -euo pipefail
cd "$(dirname "$0")"
HOST=${WEBSITE_HOST:-pi-two}
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)}"
case "$BRANCH" in
  main)    W=/home/kbauer/data/website;     CONTAINER=website;     PORT=8088; PUBHOST=6b62.com;;
  staging) W=/home/kbauer/data/website-new; CONTAINER=website-new; PORT=8089; PUBHOST=new.6b62.com;;
  *) echo "deploy.sh: unknown branch '$BRANCH' (expected 'main' or 'staging')" >&2; exit 1;;
esac
echo "Deploying branch '$BRANCH' -> container '$CONTAINER'  (https://$PUBHOST)"

tar czf - --owner=0 --group=0 site nginx |
  ssh -o BatchMode=yes "$HOST" "W='$W' CONTAINER='$CONTAINER'; "'set -e
    T=$(mktemp -d); trap "rm -rf \"$T\"" EXIT
    tar xzf - -C "$T"
    find "$T/site" -type f \( -name "*.html" -o -name "*.css" -o -name "*.txt" -o -name "*.svg" -o -name "*.json" \) -exec gzip -9 -k -n {} \;
    mkdir -p "$W/site" "$W/nginx"
    rm -rf "$W/site.new" && cp -a "$T/site" "$W/site.new" && chmod -R a+rX "$W/site.new"
    cp "$T"/nginx/*.conf "$W/nginx/"
    # the container bind-mounts $W/site, so swap the contents and keep the directory
    rm -rf "$W/site.old" && mkdir "$W/site.old" && cp -a "$W/site/." "$W/site.old/" 2>/dev/null || true
    find "$W/site" -mindepth 1 -delete
    cp -a "$W/site.new/." "$W/site/" && rm -rf "$W/site.new"
    docker exec "$CONTAINER" nginx -t -q && docker exec "$CONTAINER" nginx -s reload && echo "nginx reloaded"'

ssh -o BatchMode=yes "$HOST" "curl -s -o /dev/null -H 'Accept-Encoding: gzip' -w 'local:  %{http_code} %{size_download} B (gzip)\n' http://127.0.0.1:$PORT/"
curl -s -m 8 -o /dev/null -w "public: %{http_code} cf-cache=%header{cf-cache-status}\n" "https://$PUBHOST/" || echo "public: (not reachable from here)"
echo "Reminder: purge the Cloudflare cache after a deploy (Caching -> Configuration -> Purge Everything), or wait up to 1 h."
