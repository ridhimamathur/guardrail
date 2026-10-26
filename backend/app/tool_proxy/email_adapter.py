"""Email adapter — local seeded inbox + MailHog SMTP for approved sends."""

from __future__ import annotations

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from app.config import get_settings


class EmailAdapter:
    def __init__(self, inbox_path: Path | None = None) -> None:
        settings = get_settings()
        base = Path(settings.synthetic_data_dir)
        self.inbox_path = inbox_path or (base / "inbox.json")
        self.settings = settings

    def _load_inbox(self) -> list[dict[str, Any]]:
        if not self.inbox_path.exists():
            return []
        return json.loads(self.inbox_path.read_text(encoding="utf-8"))

    def search_email(self, query: str, max_results: int = 5) -> dict[str, Any]:
        q = (query or "").lower()
        messages = self._load_inbox()
        hits = []
        for msg in messages:
            blob = f"{msg.get('subject','')} {msg.get('body','')} {msg.get('from','')}".lower()
            if all(part in blob for part in q.split() if part):
                hits.append(
                    {
                        "id": msg["id"],
                        "from": msg["from"],
                        "to": msg.get("to"),
                        "subject": msg["subject"],
                        "received_at": msg.get("received_at"),
                        "tags": msg.get("tags", []),
                    }
                )
            if len(hits) >= max_results:
                break
        return {"count": len(hits), "messages": hits}

    def read_email(self, message_id: str) -> dict[str, Any]:
        for msg in self._load_inbox():
            if msg["id"] == message_id:
                return {
                    "id": msg["id"],
                    "from": msg["from"],
                    "to": msg.get("to"),
                    "subject": msg["subject"],
                    "body": msg["body"],
                    "attachments": msg.get("attachments", []),
                    "trust_hint": msg.get("trust_hint", "external"),
                }
        raise ValueError(f"Email not found: {message_id}")

    def send_email(self, *, to: str, subject: str, body: str, from_addr: str = "agent@guardrail.local") -> dict[str, Any]:
        msg = EmailMessage()
        msg["From"] = from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(self.settings.mailhog_smtp_host, self.settings.mailhog_smtp_port, timeout=10) as smtp:
            smtp.send_message(msg)
        return {"status": "sent", "to": to, "subject": subject, "via": "mailhog"}
