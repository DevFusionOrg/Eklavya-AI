# Eklavya.AI

Eklavya.AI is an AI-enabled scholarship and fellowship management platform for the Ministry of Tribal Affairs. This repository contains the backend, frontend, and local infrastructure baseline.

## Quickstart

Requirements: Docker Desktop with Compose v2.

```bash
cp infra/.env.example infra/.env
make up
```

Services:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend health: http://localhost:8000/health
- MinIO console: http://localhost:9001

Stop services with `make down`. Run checks with `make test` and `make lint`.

The initial scaffold intentionally contains no business data or production credentials. Replace all example secrets before using a deployed environment.

