# Security Policies

Current policy version: `1.0.0`. The PDP records an explainable risk score with factors for untrusted source (+20), prompt injection (+25), intent mismatch (+25), confidential data (+15), external destination (+20), write (+10), destructive action (+30), and bulk access (+15), capped at 100.

| Rule | Enforcement |
|---|---|
| P1/P2 Capability scope | Block tools/actions absent from the agent capability profile |
| P3 External email | Block external sends unless destination is allowlisted |
| P4 Confidential destination | Block confidential data to an unapproved destination |
| P5 Deletion | Always block `delete_file` |
| P6 Public sharing | Block public links and unrestricted sharing |
| P7 Approval binding | Bind reviewer decision to action parameters and policy version; grant is one-use |
| P8 Intent integrity | Untrusted content cannot alter the original request |
| P9 Session validity | Reject expired or revoked sessions |
| P10 Proxy boundary | Reject attempts to bypass the Tool Proxy |

After authorization rules: scores 0–39 allow, 40–69 require approval, and 70–100 block. Immediate authorization failures always block. The confidential synthetic report share with the specifically allowlisted auditor is forced into approval. Approvals expire after 15 minutes. No grant is issued for blocked or pending actions.

Only `search_email`, `read_email`, `send_email`, `list_files`, `read_file`, `upload_file`, `share_file` (restricted and approval checked), `create_ticket`, and `add_comment` are implemented. The storage adapter has no delete path. GitHub must use a fine-grained test-repository token with Issues read/write and Metadata read only.
