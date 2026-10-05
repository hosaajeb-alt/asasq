# Docker Development Environment

```
docker compose up --build
```

Services (Phase 1):

| Service | Port | Role |
|---|---|---|
| frontend | 3000 | Next.js UI (proxies `/api/*` to backend) |
| backend | 8000 | FastAPI |
| postgres | 5432 | Metadata + Phase 1 record store |
| redis | 6379 | Cache / job coordination |
| minio | 9000 / 9001 | S3-compatible raw object store |

Optional profiles (commented in compose, attach later):

- `opensearch`
- `clickhouse`
- `kafka`

Default login after seed:

- `admin@nexus.local` / `NexusAdmin!23`
- `analyst@nexus.local` / `NexusAnalyst!23`

Change these before any shared deployment.
