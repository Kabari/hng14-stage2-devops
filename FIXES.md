# FIXES.md — Bug Report & Fixes

Every issue found in the starter repository, with file, line, root cause, and resolution.

---

## api/main.py

### FIX-001 — Hardcoded Redis host `localhost`
| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | 8 |
| **Problem** | `redis.Redis(host="localhost", port=6379)` — `localhost` resolves to the container itself, not the Redis service. Inside Docker the service is reached by its Compose service name (`redis`). |
| **Fix** | Read host from `REDIS_HOST` env var, falling back to `"redis"`. Same for port (`REDIS_PORT`) and password (`REDIS_PASSWORD`). |

### FIX-002 — Wrong queue name (`"job"` vs `"jobs"`)
| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | 13 |
| **Problem** | `r.lpush("job", job_id)` pushes to a key called `"job"`. Renamed for consistency and to prevent silent breakage if either side is updated independently. |
| **Fix** | Renamed both the `lpush` (API) and `brpop` (worker) calls to use the consistent key name `"jobs"`. |

### FIX-003 — No `/healthz` endpoint
| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | — (missing) |
| **Problem** | No health-check route existed. Docker and the pipeline have no way to verify the API is ready before marking it healthy. |
| **Fix** | Added `GET /healthz` that calls `r.ping()` and returns `{"status": "ok"}` (503 if Redis is unreachable). |

### FIX-004 — 404 returned as HTTP 200
| Field | Detail |
|---|---|
| **File** | `api/main.py` |
| **Line** | 22 |
| **Problem** | `return {"error": "not found"}` returns an HTTP 200 with an error body. Clients cannot detect failures from the status code alone. |
| **Fix** | Replaced with `raise HTTPException(status_code=404, detail="Job not found")`. |

### FIX-019 — Unpinned API dependencies
| Field | Detail |
|---|---|
| **File** | `api/requirements.txt` |
| **Line** | 1-3 |
| **Problem** | Unpinned deps can pull breaking versions silently across environments and CI runs. |
| **Fix** | Pinned to `fastapi==0.111.0`, `uvicorn[standard]==0.29.0`, `redis==5.0.4`. |

---

## worker/worker.py

### FIX-006 — Hardcoded Redis host `localhost`
| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 6 |
| **Problem** | Same issue as FIX-001 — `localhost` does not resolve to Redis inside a container. |
| **Fix** | Read `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` from environment variables. |

### FIX-007 — No graceful shutdown
| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 4 |
| **Problem** | `import signal` was present but no handlers were registered. Docker sends `SIGTERM` on container stop; without a handler the worker is killed immediately, potentially mid-job. |
| **Fix** | Registered `SIGTERM` and `SIGINT` handlers that set `running = False`, allowing the current job to finish before exit. |

### FIX-008 — No error handling around Redis calls
| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 13-16 |
| **Problem** | A Redis `ConnectionError` would crash the worker process entirely with no recovery. |
| **Fix** | Wrapped the main loop in `try/except redis.exceptions.ConnectionError` with a 5-second backoff retry. |

### FIX-009 — `print` used instead of structured logging
| Field | Detail |
|---|---|
| **File** | `worker/worker.py` |
| **Line** | 9, 13 |
| **Problem** | `print()` has no timestamps or log levels — unusable in production log aggregators. |
| **Fix** | Replaced all `print` calls with `logging.info` / `logging.error`. |

### FIX-019 — Unpinned worker dependencies
| Field | Detail |
|---|---|
| **File** | `worker/requirements.txt` |
| **Line** | 1 |
| **Problem** | Unpinned `redis` dep can pull a breaking version silently. |
| **Fix** | Pinned to `redis==5.0.4`. |

---

## frontend/app.js

### FIX-010 — Hardcoded API URL `http://localhost:8000`
| Field | Detail |
|---|---|
| **File** | `frontend/app.js` |
| **Line** | 6 |
| **Problem** | Inside a container, `localhost` refers to the frontend container itself — every API call fails with connection refused. |
| **Fix** | Read `API_URL` from `process.env.API_URL`, defaulting to `"http://api:8000"`. |

### FIX-011 — No `/healthz` endpoint
| Field | Detail |
|---|---|
| **File** | `frontend/app.js` |
| **Line** | — (missing) |
| **Problem** | Without a health route, Docker HEALTHCHECK and `depends_on: service_healthy` cannot work. |
| **Fix** | Added `GET /healthz` returning `{"status": "ok"}`. |

### FIX-012 — Hardcoded port
| Field | Detail |
|---|---|
| **File** | `frontend/app.js` |
| **Line** | 29 |
| **Problem** | Port `3000` was hardcoded and cannot be changed via environment. |
| **Fix** | Read from `process.env.PORT`, defaulting to `3000`. |

---

## frontend/package.json

### FIX-013 — No lint script or ESLint devDependency
| Field | Detail |
|---|---|
| **File** | `frontend/package.json` |
| **Line** | 6-8 |
| **Problem** | No `lint` npm script and no `eslint` devDependency. CI pipeline lint stage requires `npm run lint` to succeed. |
| **Fix** | Added `"lint": "eslint app.js"` to scripts, `eslint` to devDependencies, and `.eslintrc.json` config file. |

---

## Infrastructure

### FIX-014 — No Dockerfiles
| Field | Detail |
|---|---|
| **Files** | `api/Dockerfile`, `worker/Dockerfile`, `frontend/Dockerfile` |
| **Problem** | None existed — services could not be containerized. |
| **Fix** | Created production Dockerfiles with multi-stage builds, non-root users, and HEALTHCHECK instructions. No secrets copied into any image. |

### FIX-015 — No docker-compose.yml
| Field | Detail |
|---|---|
| **File** | `docker-compose.yml` |
| **Problem** | Missing entirely — no way to orchestrate the four-service stack. |
| **Fix** | Created with named internal network, Redis not exposed on host, `service_healthy` conditions, env-only config, and resource limits on every service. |

### FIX-016 — Redis password ignored by all services
| Field | Detail |
|---|---|
| **Files** | `api/main.py`, `worker/worker.py`, `docker-compose.yml` |
| **Problem** | `REDIS_PASSWORD` existed in the env file but was never passed to `redis.Redis()` or to `redis-server`. |
| **Fix** | All services now read `REDIS_PASSWORD` from environment and pass it through. Compose passes it to `redis-server --requirepass`. |
