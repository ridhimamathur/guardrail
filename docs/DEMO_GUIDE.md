# Demo Guide

Copy `.env.example` to `.env`, replace each `CHANGE_ME` value with unique local-only values, and set all four `DEMO_*_PASSWORD` values. Start the stack with `docker compose up --build`, then open http://localhost:3000. Log in with a seeded account email and its matching password from `.env`. Never use production credentials. The dashboard refreshes from the API and live audit feed.

1. Open **Demo Scenarios** and choose A. Run it. Watch search/read/upload/ticket actions in **Live Action Monitor**. Inspect the Finance bucket in MinIO.
2. Choose B and run it. The seeded malicious message contains the attacker instruction. The resulting external send should be `BLOCKED`; check MailHog at http://localhost:8025 to confirm it was not sent.
3. Choose C and run it. Sign out and sign in as manager or security admin. In **Approval Queue**, inspect the exact action and either approve (which executes the frozen action) or deny. Confirm the audit events.
4. Open **Audit Explorer** and use Verify chain to check the chained event hashes.

GitHub Issues integration is disabled by default. To enable it, set `GITHUB_ENABLED=true`, a dedicated test `GITHUB_OWNER` and private `GITHUB_REPO`, and a fine-grained token with only Issues read/write and Metadata read. Without that configuration, tickets use the local synthetic adapter. Do not point the prototype at production systems.
