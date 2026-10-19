#!/usr/bin/env bash
# deploy.sh — publish new.6b62.com. Run on a machine with tailnet access + SSH to pi-two.
# Copies site/ and nginx/ to pi-two:/home/kbauer/data/website-new, pre-gzips the text files
# (nginx gzip_static), validates and reloads nginx in the website-new container (no downtime).
# The container itself is defined in pi-two:/opt/stacks/utility-stack/compose.yaml (see README).
set -euo pipefail
cd "$(dirname "$0")"
HOST=${WEBSITE_HOST:-pi-two}

tar czf - --owner=0 --group=0 site nginx |
  ssh -o BatchMode=yes "$HOST" 'set -e
    W=/home/kbauer/data/website-new
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
    docker exec website-new nginx -t -q && docker exec website-new nginx -s reload && echo "nginx reloaded"'

ssh -o BatchMode=yes "$HOST" 'curl -s -o /dev/null -H "Accept-Encoding: gzip" -w "local:  %{http_code} %{size_download} B (gzip)\n" http://127.0.0.1:8089/'
curl -s -m 8 -o /dev/null -w "public: %{http_code} cf-cache=%header{cf-cache-status}\n" https://new.6b62.com/ || echo "public: (not reachable from here)"
echo "Reminder: purge the Cloudflare cache after a deploy (Caching -> Configuration -> Purge Everything), or wait up to 1 h."
