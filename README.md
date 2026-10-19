# 6b62.com

Personal site / one-page CV for Konstantin Bauer, typeset like a disassembly: an address margin, a
continuous hairline ledger, flat light/dark, a hand-drawn Canvas wireframe of the tailnet (no library),
and a small working shell. It **prints as a one-page CV** (`Ctrl/Cmd-P`).

Served at **https://new.6b62.com** from an `nginx:alpine` container on a Raspberry Pi behind a Cloudflare
Tunnel. No external requests: the fonts are self-hosted, so the page loads only from its own origin.

| Path | What |
|---|---|
| `site/index.html` | The page. One inline `<script>` (Canvas wireframe + shell); everything else inline. |
| `site/404.html` | Matching 404 (`0x194`). |
| `site/fonts/` | Self-hosted Archivo + JetBrains Mono (`.woff2`, latin + latin-ext). |
| `site/.well-known/security.txt` | Security contact. |
| `nginx/default.conf` | Server block + CSP (`default-src 'none'`, `font-src 'self'`). |
| `nginx/nginx.conf` | Main config: 1 worker, no access log, `gzip_static`. |
| `deploy.sh` | Publish to the Pi (copy, pre-gzip, `nginx -t`, reload — no downtime). |
| `tests/run` | Static checks + `nginx -t` + Nu HTML validation. |
| `.github/workflows/ci.yml` | Runs `tests/run` on every push and PR. |

## Tests

```bash
./tests/run
```

Core checks (files present, fonts self-hosted and all referenced, no external requests, head metadata,
`security.txt`, CSP) need only `bash` + `grep`. The `nginx -t` and HTML-validation checks use docker
(`nginx:alpine` and the Nu `validator/validator` image) and auto-skip when docker or the image is
unavailable — so they run in CI and on any machine with docker, and a bare laptop still runs the rest.

CI runs the same script on `ubuntu-latest`, where docker and the internet are present, so all checks run.

## Deploy

```bash
./deploy.sh            # publishes to pi-two:/home/kbauer/data/website-new, reloads nginx
```

Needs tailnet access and SSH to `pi-two`. After a deploy, purge the Cloudflare cache
(Caching → Configuration → Purge Everything) or wait up to 1 h for the edge TTL to lapse.

### The container (one-time, on the Pi)

Defined in `pi-two:/opt/stacks/utility-stack/compose.yaml` as the `website-new` service: `nginx:alpine`,
read-only, `mem_limit: 32m`, bound to `127.0.0.1:8089`, with the network alias `website-new`. It
bind-mounts `/home/kbauer/data/website-new/{site,nginx}`.

### Cloudflare

- **Route:** Zero Trust → Networks → Tunnels → (the 6b62.com tunnel) → Public Hostname: `new.6b62.com`
  → `http://website-new:80`. Adding the hostname creates the proxied DNS record automatically.
- **Cache:** the zone's existing "all incoming requests" cache rule already covers `new.6b62.com`; no new
  rule is needed. The page sends `Cache-Control: s-maxage=3600`, so the edge serves ~1 request/hour per
  location.

## Fonts

Archivo + JetBrains Mono are self-hosted in `site/fonts/` (downloaded from Google Fonts via
google-webfonts-helper, latin + latin-ext). The page declares them with an inline `@font-face` block and a
full system fallback stack, so there are no external font requests. To refresh or change weights, drop new
`.woff2` files in `site/fonts/` and update the `@font-face` block + the weights used in the CSS.

## noindex

The page is `noindex, follow` with `<link rel="canonical">` → `https://6b62.com/`, so this preview domain
does not compete with the main site in search. When `new.6b62.com` becomes the primary site: remove the
`robots` meta, point `canonical` and the `og:url` at the real URL, and update `Canonical` in
`security.txt`.
