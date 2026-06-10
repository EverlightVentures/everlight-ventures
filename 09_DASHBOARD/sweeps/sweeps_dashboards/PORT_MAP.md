# Local Dashboard Port Map (2026-05-12)

Canonical source. Mirrors the agent-side memory at `reference_local_dashboard_map.md`.
Always served on `127.0.0.1`. External Tailnet exposure handled separately.

## Bands

```
2000        MASTER HUB                      hub
2100-2199   Markets / Trading               markets
2200-2299   Reports / Ops                   reports
2300-2399   Intel Center                    intel
2400-2499   Consumer / Apps                 apps
2500-2599   Personal / Health               health
2600-2699   reserved
2700-2799   Memory cluster + Lucrex CC       lucrex
```

## Live entries

### 2000 -- Master Hub `hub`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2000/` | Master tree of every band + every dashboard. Click to launch. | `serve_master_hub.sh` |

### 2100 band -- Markets / Trading `markets`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2100/` | XLM Bot Dashboard (local mirror) | TBD (bot lives on Oracle Micro) |

### 2200 band -- Reports / Ops `reports`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2200/` | Reports band root + dashboards landing | `serve_local_reports.sh` |
| `127.0.0.1:2200/reports/` | All 76+ generated reports (HTML) | same |
| `127.0.0.1:2200/dashboards/` | Dashboard index page (mirror of master hub) | same |

### 2300 band -- Intel Center `intel`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2300/` | Intel Center static dashboard (Preact + Tailwind) | `python3 -m http.server 2300` |
| `127.0.0.1:2300/clients.html` | Clients view (`2300.1`) | same |
| `127.0.0.1:2300/resources.html` | Resources catalog (`2300.2`) | same |
| `127.0.0.1:2301/` | OSINT FastAPI | `serve_osint.sh` (REPORTS_PORT=2301) |
| `127.0.0.1:2301/api/docs` | Swagger UI (`2301.1`) | same |
| `127.0.0.1:2302/` | E-Sign service (UETA + E-SIGN Act compliant, `2302`) | `esign_server.py` |
| `127.0.0.1:2302/sign/{token}` | Per-recipient signing URL (`2302.1`) | same |

### 2400 band -- Consumer / Apps `apps`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2400/game_v6.html` | Alley Kingz prototype | `apps ak` zsh function |

### 2500 band -- Personal / Health `health`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2500/` | MMA Fight Camp dashboard | `mma` launcher |
| `127.0.0.1:2500/05_Fitness/` | Phase 4 Fitness Mirror (`2500.1`) | same |

### 2700 band -- Memory cluster + Lucrex `lucrex`
| Address | What | Spawned by |
|---|---|---|
| `127.0.0.1:2700/` | Blinko RAG (local lite fallback; canonical is e5-mother:1111) | `dashboards_watchdog.sh` -> `blinko_lite.py` |
| `127.0.0.1:2701/` | MCP HTTP bridge (reads local blinko) | `dashboards_watchdog.sh` -> uvicorn |
| `127.0.0.1:2702/` | Lucrex OS -- Next.js command center (`lucrex-os`), rehomed 2026-05-24 from `129.159.38.250:8080/lucrex/` | `serve_lucrex.sh` |

## Aliases (zsh)

| Alias | Purpose | Examples |
|---|---|---|
| `hub` | Open master hub at :2000 | `hub` |
| `markets` | Open 2100 markets | `markets` / `markets list` |
| `reports` | Open 2200 reports | `reports` / `reports recent` / `reports search foo` |
| `intel` | Open 2300 intel | `intel` / `intel api` / `intel logs` |
| `apps` | Open 2400 apps | `apps` / `apps ak` |
| `health` | Open 2500 health | `health` / `health rebuild` |
| `lucrex` | Open 2702 Lucrex Command Center | `lucrex` |
| `dashboards` | Print this map to terminal | `dashboards` |

## Rehomed 2026-05-24
- `129.159.38.250:8080/lucrex/` -> `127.0.0.1:2702/` (Lucrex Command Center; 2700 itself is the local Blinko lite, so Lucrex sits at 2702 in-band; serve via `serve_lucrex.sh`)
- `129.159.38.250:1111` -> `e5-mother:1111` (Blinko RAG on e5-mother, tailnet; 34 live refs repointed)

## Still parked (not rehomed)
- `129.159.38.250:5678` parked n8n (parked permanently 2026-04-24, refs deletable)

## Dot-notation convention
`2100.1`, `2100.2` in the hub UI = sub-pages on the same port, different URL paths.
Different services in a band get separate integer ports (`2300` vs `2301`).
