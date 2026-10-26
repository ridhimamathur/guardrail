# Threat Model

## Prototype boundary

GuardRAIL mediates proposals between a deterministic mock agent and MailHog, MinIO, and an optional GitHub Issues test repository. Users, task intent, and policy configuration are trusted inputs after authentication. Email/document/tool output is untrusted data. The database and backend process are inside the prototype trust boundary.

## Assets

- Credentials used by Tool Proxy adapters.
- Session and approval grants, bound to an action, parameter hash, policy version, expiry, and nonce.
- Synthetic finance files and destination allowlists.
- Action records and tamper-evident audit history.

## Threats and controls

| Threat | Control in prototype | Remaining limitation |
|---|---|---|
| Indirect prompt injection in email | Context provenance/trust labels, indicator scan, intent alignment and risk policy | String indicators are easy to evade and may yield false positives |
| Unauthorized tool/action proposal | Agent capability profile and PEP policy checks | Admin database compromise can alter capabilities |
| Data exfiltration | External email allowlist, confidential destination rule, risk scoring | Limited destination normalization and synthetic adapter scope |
| Approval replay or tampering | Parameter hash, policy version, expiry, nonce, one-time grant | Grant consumption needs database row locking for concurrent workers |
| Direct proxy bypass | API exposes only inspect and execute; proxy rejects unknown actions | Network isolation is local Compose level; not hardened against host access |
| Audit alteration | SHA-256 event chain and verify endpoint | Database administrators can rewrite the whole chain; not an immutable ledger |
| Credential exposure | Adapter configuration only in backend environment | Local defaults and `.env.example` are for development only |
| Cross-user action access | Task/action ownership checks; reviewer roles | Needs broader API authorization review before production |

## Trust/data handling

User intent is stored separately from email/document content. Context items carry source type, owner, trust level, hash, provenance, received time, and injection score. Audit records redact credential-like fields and execution summaries omit content bodies. The demo data is entirely synthetic.

## Assumptions

The developer controls the local machine and Compose network. The mock agent is deterministic and not an actual LLM. The prototype is not designed for hostile tenants, internet exposure, high availability, or regulatory workloads.
