# 6b62.com

Konstantin Bauer's personal site / one-page CV (prints as a one-page CV with `Ctrl/Cmd-P`).
Static HTML served by `nginx:alpine` on a Raspberry Pi behind a Cloudflare Tunnel — no external
requests, no open ports.

## Two environments, one branch each

| Branch | URL | Container | Port | Indexed? |
|---|---|---|---|---|
| `main` | https://6b62.com | `website` | 8088 | yes |
| `staging` | https://new.6b62.com | `website-new` | 8089 | no (`noindex`) |

`main` is the stable, public site. `staging` is where experimental versions run first, so `6b62.com`
always has a working version. **Promote** a tested change with a normal merge: `git checkout main &&
git merge staging`, then deploy `main`.

The two branches share everything below (`deploy.sh`, `tests/run`, CI, `nginx/nginx.conf`); they differ
only in `site/` and `nginx/default.conf`. The staging site is the richer design (an inline Canvas
tailnet wireframe + shell, self-hosted fonts); `main` is the current lean, zero-JS site.

## Layout

| Path | What |
|---|---|
| `site/index.html` | The page. |
| `site/404.html` | Matching 404. |
| `site/fonts/` | Self-hosted woff2 (staging only; `main` uses system fonts). |
| `site/.well-known/security.txt` | Security contact. |
| `nginx/default.conf` | Server block + CSP (`default-src 'none'`). |
| `nginx/nginx.conf` | Main config: 1 worker, no access log, `gzip_static`. |
| `deploy.sh` | Publish to the Pi — the branch picks the environment. |
| `tests/run` | Static checks + `nginx -t` + Nu HTML validation. |
| `.github/workflows/ci.yml` | Runs `tests/run` on every push and PR. |

## Deploy

```bash
./deploy.sh            # deploys the CURRENT branch to its environment
./deploy.sh staging    # or name the branch explicitly
```

Needs tailnet access and SSH to `pi-two`. `deploy.sh` reads the current git branch and publishes to the
matching container (`main` → 6b62.com, `staging` → new.6b62.com), with no downtime. After a deploy, purge
the Cloudflare cache (Caching → Configuration → Purge Everything) or wait up to 1 h for the edge TTL.

## Tests

```bash
./tests/run
```

Core checks (files present, no external requests, fonts referenced actually exist, head metadata,
`security.txt`, CSP, correct indexing for the branch) need only `bash` + `grep`. The `nginx -t` and
HTML-validation checks use docker (`nginx:alpine` and the Nu `validator/validator` image) and auto-skip
when docker is unavailable. CI runs the same script on `ubuntu-latest`, where everything runs.

## Infrastructure (on the Pi, one-time)

Both containers live in `pi-two:/opt/stacks/utility-stack/compose.yaml` (`website` and `website-new`):
`nginx:alpine`, read-only, `mem_limit: 32m`, bound to localhost, bind-mounting
`/home/kbauer/data/<website|website-new>/{site,nginx}`.

Cloudflare: each hostname is a Public Hostname on the 6b62.com tunnel (`6b62.com` → `http://website:80`,
`new.6b62.com` → `http://website-new:80`). The zone's single "all incoming requests" cache rule covers
both; the page sends `Cache-Control: s-maxage=3600`, so the edge serves ~1 request/hour per location.

## Fonts (staging)

The staging design self-hosts Archivo + JetBrains Mono (`site/fonts/`, latin + latin-ext, from Google
Fonts via google-webfonts-helper), declared with an inline `@font-face` block and a full system fallback
stack — so there are no external font requests. To change weights, drop new `.woff2` in `site/fonts/` and
update the `@font-face` block.
