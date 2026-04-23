# hng14-stage2-devops

A containerised job-processing system built for HNG Stage 2 (DevOps).  
Three services — **frontend** (Node/Express), **api** (Python/FastAPI), **worker** (Python) — plus a **Redis** queue, all wired together with Docker Compose and shipped through a full GitHub Actions CI/CD pipeline.

---

## Architecture

```
Browser → Frontend :3000 → API :8000 → Redis
                                  ↑
                              Worker (polling)
```

| Service  | Technology    | Role                                      |
|----------|---------------|-------------------------------------------|
| frontend | Node 20 / Express | Serves the dashboard UI; proxies to API |
| api      | Python 3.12 / FastAPI | Creates jobs, returns status         |
| worker   | Python 3.12   | Pops jobs from Redis queue and processes  |
| redis    | Redis 7       | Message queue + job-state store           |

---

## Prerequisites

| Tool           | Minimum version |
|----------------|-----------------|
| Docker         | 24.x            |
| Docker Compose | v2 (plugin)     |
| Git            | any recent      |

No cloud account is required. Everything runs locally.

---

## Quick-start (clean machine)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/hng14-stage2-devops.git
cd hng14-stage2-devops
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and set a strong `REDIS_PASSWORD`:

```
REDIS_PASSWORD=my_super_secret_password
FRONTEND_PORT=3000
```

> **Important:** Never commit `.env`. It is listed in `.gitignore`.

### 3. Build and start the stack

```bash
docker compose up --build -d
```

Docker Compose will:
1. Build all three service images.
2. Start Redis with password auth (not exposed on the host).
3. Wait for Redis to be healthy, then start the API and Worker.
4. Wait for the API to be healthy, then start the Frontend.

### 4. Verify everything is healthy

```bash
docker compose ps
```

Expected output — all services should show `healthy`:

```
NAME          IMAGE        STATUS                    PORTS
project-api-1       ...  Up 30 seconds (healthy)
project-frontend-1  ...  Up 20 seconds (healthy)   0.0.0.0:3000->3000/tcp
project-redis-1     ...  Up 35 seconds (healthy)
project-worker-1    ...  Up 30 seconds (healthy)
```

### 5. Open the dashboard

Navigate to **http://localhost:3000** (or the port set in `FRONTEND_PORT`).

Click **Submit New Job**. You should see the job appear as `queued` and transition to `completed` within a few seconds.

---

## Health endpoints

| Service  | Endpoint                        | Expected response         |
|----------|---------------------------------|---------------------------|
| API      | `GET http://localhost:8000/healthz` | `{"status":"ok"}`     |
| Frontend | `GET http://localhost:3000/healthz` | `{"status":"ok"}`     |

---

## Running tests locally

```bash
# Install test dependencies
pip install -r api/requirements.txt pytest pytest-cov httpx

# Run unit tests with coverage
cd api
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## CI/CD Pipeline

The GitHub Actions pipeline (`.github/workflows/ci.yml`) runs on every push:

| Stage            | What it does                                                                 |
|------------------|------------------------------------------------------------------------------|
| **lint**         | `flake8` (Python), `eslint` (JS), `hadolint` (Dockerfiles)                  |
| **test**         | `pytest` with mocked Redis; coverage report uploaded as artifact             |
| **build**        | Builds all 3 images, tags with `<git-sha>` and `latest`, pushes to local registry |
| **security**     | Trivy scans all images; fails on any `CRITICAL` CVE; SARIF uploaded as artifact |
| **integration**  | Brings full stack up, submits a job, polls until `completed`, tears down     |
| **deploy**       | *(main branch only)* SSH rolling update — new container must be healthy before old one is stopped |

A failure in any stage blocks all subsequent stages.

### Required GitHub Secrets (for deploy stage)

| Secret            | Description                            |
|-------------------|----------------------------------------|
| `REDIS_PASSWORD`  | Redis auth password for production     |
| `DEPLOY_HOST`     | IP or hostname of your production server |
| `DEPLOY_USER`     | SSH username                           |
| `SSH_PRIVATE_KEY` | Private key (ed25519 recommended)      |

---

## Stopping the stack

```bash
docker compose down          # stop containers, keep volumes
docker compose down -v       # stop containers and delete Redis data
```

---

## Project structure

```
.
├── api/
│   ├── Dockerfile
│   ├── main.py
│   ├── requirements.txt
│   └── tests/
│       └── test_main.py
├── worker/
│   ├── Dockerfile
│   ├── worker.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── app.js
│   ├── package.json
│   ├── .eslintrc.json
│   └── views/
│       └── index.html
├── scripts/
│   └── rolling-update.sh
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── .env.example
├── .gitignore
├── FIXES.md
└── README.md
```

---

## Security notes

- Redis is not exposed on the host (`ports` mapping intentionally omitted).
- All secrets come from environment variables; nothing is hardcoded.
- `.env` is in `.gitignore` — commit `.env.example` only.
- All containers run as a non-root `app` user.
- Trivy blocks the pipeline on any `CRITICAL` CVE.