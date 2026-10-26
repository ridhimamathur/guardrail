# GuardRAIL Architecture (Phase 1)

## Purpose

GuardRAIL is a runtime Policy Enforcement Point (PEP) between an action-capable AI agent and enterprise tools. The agent may **propose** actions; only GuardRAIL may **authorize** them; only the Tool Proxy may **execute** them with third-party credentials.

**Phase 1 label:** Working prototype with synthetic data and test integrations. Not production-ready.

## Final Architecture Diagram

```text
┌─────────────┐
│    User     │
│  (Browser)  │
└──────┬──────┘
       │ JWT login / task create / approve
       ▼
┌──────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                         │
│  Login · Dashboard · Live Monitor · Approvals · Audit · Demo │
└────────────────────────────┬─────────────────────────────────┘
                             │ REST + WebSocket
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (GuardRAIL)                │
│                                                              │
│  Auth (JWT) ──► Task API ──► Mock LLM Agent                  │
│                      │              │                        │
│                      ▼              ▼                        │
│              ┌─────────────────────────────────┐             │
│              │   Policy Enforcement Point      │             │
│              │   POST /api/v1/actions/inspect  │             │
│              └──────────────┬──────────────────┘             │
│                             ▼                                │
│              ┌─────────────────────────────────┐             │
│              │ Context Analyzer                │             │
│              │ (trust, injection indicators)   │             │
│              └──────────────┬──────────────────┘             │
│                             ▼                                │
│              ┌─────────────────────────────────┐             │
│              │ Intent Aligner                  │             │
│              │ (user intent vs proposed action)│             │
│              └──────────────┬──────────────────┘             │
│                             ▼                                │
│              ┌─────────────────────────────────┐             │
│              │ Policy Decision Point           │             │
│              │ Risk 0–100 → ALLOW / APPROVAL / │             │
│              │ BLOCK + rules P1–P10            │             │
│              └──────────────┬──────────────────┘             │
│                             ▼                                │
│              ┌─────────────────────────────────┐             │
│              │ Grant Manager                   │             │
│              │ One-time HMAC-signed grant      │             │
│              └──────────────┬──────────────────┘             │
│                             ▼                                │
│              ┌─────────────────────────────────┐             │
│              │ Secure Tool Proxy               │             │
│              │ (credentials stay here only)    │             │
│              └───┬──────────┬──────────┬───────┘             │
│                  │          │          │                     │
│  Audit Chain ◄───┴──────────┴──────────┴──► Live WS Feed     │
└──────────────────┼──────────┼──────────┼─────────────────────┘
                   ▼          ▼          ▼
            ┌──────────┐ ┌────────┐ ┌─────────────┐
            │ MailHog  │ │ MinIO  │ │ GitHub Issues│
            │ (SMTP)   │ │(S3)    │ │ (test repo)  │
            └──────────┘ └────────┘ └─────────────┘
                   ▲
                   │
            ┌──────────────┐
            │  PostgreSQL  │
            └──────────────┘
```

## Core Security Rule

```text
User → AI Agent → GuardRAIL PEP → PDP → One-time signed grant → Tool Proxy → External tool
```

- Agent process never receives SMTP, GitHub, MinIO, or DB credentials for tools.
- Direct tool bypass is rejected (P10).
- Grants are single-use, parameter-bound, and expire.

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| Mock LLM Agent | Propose structured tool actions only; no policy decisions |
| PEP | Accept action proposals; orchestrate inspection pipeline |
| Context Analyzer | Classify trust; detect injection indicators |
| Intent Aligner | Compare original user intent to proposed action |
| Risk Engine | Explainable 0–100 score from risk factors |
| PDP | ALLOW / REQUIRE_APPROVAL / BLOCK via P1–P10 |
| Grant Manager | Issue, validate, consume HMAC grants |
| Tool Proxy | Hold credentials; execute frozen approved actions |
| Audit Logger | Tamper-evident SHA-256 hash chain |
| Frontend | Operate demos, approvals, live feed, audit |

## Decision Thresholds

| Risk | Decision (if auth passes) |
|------|---------------------------|
| 0–39 | ALLOW |
| 40–69 | REQUIRE_APPROVAL |
| 70–100 | BLOCK |

Immediate BLOCK for: missing auth, expired/reused/invalid grant, parameter mismatch, unapproved external destination, direct bypass, capability violation, expired session.

## Data Flow (Demo A)

1. User creates task with invoice intent.
2. Mock agent proposes `search_email`.
3. PEP inspects → ALLOW → grant → Tool Proxy reads seeded inbox.
4. Agent proposes `upload_file` → ALLOW → MinIO upload.
5. Agent proposes `create_ticket` → ALLOW → GitHub Issue.
6. Dashboard + audit timeline updated via WebSocket.

## Out of Scope (Phase 1)

LLM semantic analysis, memory poisoning defenses, ML anomaly detection, multi-agent isolation, OPA, Prometheus/Grafana, policy editor UI.
