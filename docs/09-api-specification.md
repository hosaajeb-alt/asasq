# API Specification (Phase 1)

Base: `/api/v1`  
Auth: `Authorization: Bearer <access_token>`  
Errors: `{ "detail": str, "code": str }`  
All list endpoints: `?q&page&page_size&sort`

## Auth
- `POST /auth/login` `{email, password}` → `{access_token, refresh_token, user}`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET  /auth/me`

## Users / teams
- `GET|POST /users`  `GET|PATCH /users/{id}`
- `GET|POST /teams`  `POST /teams/{id}/members`

## Datasets
- `GET|POST /datasets`
- `GET|PATCH /datasets/{id}`
- `GET /datasets/{id}/records`
- `GET /datasets/{id}/versions`
- `GET /datasets/{id}/profile`
- `GET /datasets/{id}/schema`

## Import wizard
- `POST /imports/upload` (multipart)
- `GET  /imports/{id}`
- `POST /imports/{id}/meta`
- `POST /imports/{id}/detect-schema`
- `POST /imports/{id}/map-fields`
- `POST /imports/{id}/profile`
- `POST /imports/{id}/commit`
- `POST /imports/{id}/cancel`

## Search
- `POST /search` `{q, mode, filters, page}`
- `GET  /search/suggest?q=`

## Entities
- `GET|POST /entities`
- `GET /entities/{id}`
- `GET /entities/{id}/graph`
- `POST /entities/resolve`  (run ER on a dataset or pair)
- `POST /entities/{id}/merge`
- `POST /entities/{id}/unmerge`

## Investigations
- `GET|POST /investigations`
- `GET|PATCH /investigations/{id}`
- `POST /investigations/{id}/items`
- `POST /investigations/{id}/notes`
- `POST /investigations/{id}/evidence`

## Registry / admin
- `GET|POST /semantic-types`
- `GET /audit`
- `GET /metrics`
- `GET /health`

## Evidence / quality
- `GET /evidence/{id}`
- `GET /quality/overview`
