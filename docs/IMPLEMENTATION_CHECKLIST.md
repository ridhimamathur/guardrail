# GuardRAIL Prototype Implementation Checklist

## Planning artifacts
- [x] Architecture diagram (`docs/ARCHITECTURE.md`)
- [x] Database schema (`docs/DATABASE_SCHEMA.md`)
- [x] API contract (`docs/API.md`)
- [x] Repository structure
- [x] This checklist

## Infrastructure
- [x] `docker-compose.yml` (api, frontend, postgres, mailhog, minio, minio-init)
- [x] `.env.example`
- [x] Backend Dockerfile
- [x] Frontend Dockerfile

## Backend core
- [x] Config, database, models, Alembic migrations
- [x] Seed users, roles, agent, capabilities, allowlists, synthetic inbox
- [x] JWT auth + roles
- [x] Agent sessions + task-scoped grants
- [x] Action request model + PEP inspect API
- [x] Context analyzer + injection indicators
- [x] Intent aligner
- [x] Risk engine + PDP (P1–P10)
- [x] One-time grant manager (HMAC, reviewer binding)
- [x] Tool Proxy (MailHog/local inbox, MinIO, GitHub)
- [x] Approval workflow (15 min expiry)
- [x] Audit hash chain
- [x] WebSocket live feed
- [x] Metrics + health

## Frontend
- [x] Login
- [x] Overview dashboard
- [x] Live Action Monitor
- [x] Approval Queue
- [x] Audit Explorer
- [x] Demo Scenarios

## Demos & tests
- [x] Deterministic Demo A / B / C workflow definitions
- [x] Pytest unit suite for all required modules
- [x] Documentation (README + threat model + policies + test plan + demo guide)

## Exit criteria
- [x] Compose configuration validates; local stack startup remains environment-dependent
- [x] Login route and seeded users implemented
- [ ] Verify Demo A/B/C against running Compose services
- [x] Agent provider has no adapter credentials
- [x] Dashboard + audit visibility implemented
- [x] Replay/expire/tamper grant checks implemented
- [x] All current Pytest unit tests pass
