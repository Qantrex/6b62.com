# 6b62.com

Konstantin Bauer's personal site and one-page CV (prints as a one-page A4 CV with `Ctrl/Cmd-P`).
One static HTML file served by `nginx:alpine` on a Raspberry Pi behind a Cloudflare Tunnel: no external
requests, no JavaScript, no open ports.

## The rule: 27,490 bytes

The page is exactly **27,490 bytes (0x6b62)**, measured as the uncompressed body:

```bash
curl -s -H "Accept-Encoding: identity" https://6b62.com | wc -c   # 27490
```

It is laid out like a linker map. Each block's margin shows its real byte range in the served file and
its size, and the bar at the top shows the whole file as one segment per block. Any range can be checked:

```bash
curl -s -H "Accept-Encoding: identity" https://6b62.com | tail -c +<start+1> | head -c <size>
```

`.notes` (things I broke and fixed in the homelab) is on screen only; print stays a one-page CV.
`.pad` is the last block. It takes whatever is left of the budget: a hex string that decodes to a
message followed by zero bytes (`xxd -r -p`). Response headers are not part of the budget.

## Build

```bash
./build.py           # src/*.html -> site/index.html, exactly 27,490 bytes, or it fails
./build.py --check   # rebuild in memory and compare with site/index.html (used by the tests)
```

Edit the text in `src/` (one file per block, in order: `head`, `about`, `edu`, `job`, `work`, `cert`,
`skills`, `notes`, `contact`, `pad`), never `site/index.html` directly. Every number on the page is a fixed-width
field (`0x0412`, `   910`, `07.3%`), so filling in the real values never changes the length. If the text
grows past the budget, the build fails and says by how much.

## Two environments, one branch each

| Branch | Host | Container | Port | nginx config | Visibility |
|---|---|---|---|---|---|
| `main` | `6b62.com` | `website` | 8088 | `nginx/main.conf` | public |
| `staging` | `new.6b62.com` | `website-new` | 8089 | `nginx/staging.conf` | private, `X-Robots-Tag: noindex, nofollow` |

`main` is the public site. `staging` is for development and testing only. The page bytes are the same on
both; only the nginx config differs, and both configs live on both branches, so a merge never carries
staging settings into production. **Promote** with `git checkout main && git merge staging`, then deploy
`main`.

## Layout

| Path | What |
|---|---|
| `src/*.html` | The page, one file per block. |
| `build.py` | Assembles `site/index.html` at exactly 27,490 bytes. |
| `site/index.html` | The built page (committed, checked by CI). |
| `site/404.html` | Matching 404. |
| `site/.well-known/security.txt` | Security contact (served on `main` only). |
| `nginx/main.conf`, `nginx/staging.conf` | Server block per environment: CSP, headers, flag header. |
| `nginx/nginx.conf` | Main config: 1 worker, no access log, `gzip_static`. |
| `deploy.sh` | Builds, then publishes to the Pi; the branch picks the environment. |
| `tests/run` | Size, linker-map ranges, no scripts or external requests, metadata, nginx, HTML validation. |
| `.github/workflows/ci.yml` | Runs `tests/run` on every push and PR. |

## Deploy

```bash
./deploy.sh            # deploys the CURRENT branch to its environment
./deploy.sh staging    # or name the branch explicitly
```

Needs tailnet access and SSH to `pi-two`. `deploy.sh` runs `build.py` first and stops if it fails, installs
the branch's nginx config as `conf.d/default.conf`, reloads nginx with no downtime, and checks that the
origin serves exactly 27,490 bytes. Then purge the Cloudflare cache (Caching → Configuration → Purge
Everything) and check the public URL with `Accept-Encoding: identity`.

## Cloudflare

The bytes measured at the public URL must equal the file, so Cloudflare must not rewrite the body:
Email Address Obfuscation, Auto Minify, Rocket Loader, Mirage and the Web Analytics beacon must all be off.
Each hostname is a Public Hostname on the 6b62.com tunnel (`6b62.com` → `http://website:80`,
`new.6b62.com` → `http://website-new:80`). The zone's cache rule covers both; the page sends
`Cache-Control: s-maxage=3600`, so the edge serves about one request per hour per location.

## Infrastructure (on the Pi, one-time)

Both containers live in `pi-two:/opt/stacks/utility-stack/compose.yaml` (`website` and `website-new`):
`nginx:alpine`, read-only, `mem_limit: 32m`, bound to localhost, bind-mounting
`/home/kbauer/data/<website|website-new>/site` and the two nginx config files.
