"""GitHub Issues ticket adapter with local fallback when GitHub is disabled."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from app.config import get_settings


class TicketAdapter:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_path = Path(self.settings.synthetic_data_dir) / "tickets.json"
        if not self.local_path.parent.exists():
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.local_path.exists():
            self.local_path.write_text("[]", encoding="utf-8")

    def _local_create(self, title: str, body: str) -> dict[str, Any]:
        tickets = json.loads(self.local_path.read_text(encoding="utf-8"))
        ticket = {
            "id": str(uuid4()),
            "number": len(tickets) + 1,
            "title": title,
            "body": body,
            "html_url": f"local://tickets/{len(tickets) + 1}",
            "backend": "local",
        }
        tickets.append(ticket)
        self.local_path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")
        return ticket

    def create_ticket(self, title: str, body: str, labels: list[str] | None = None) -> dict[str, Any]:
        if not self.settings.github_enabled or not self.settings.github_token:
            return self._local_create(title, body)

        url = f"https://api.github.com/repos/{self.settings.github_owner}/{self.settings.github_repo}/issues"
        headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return {
            "id": data.get("id"),
            "number": data.get("number"),
            "title": data.get("title"),
            "html_url": data.get("html_url"),
            "backend": "github",
        }

    def add_comment(self, issue_number: int, body: str) -> dict[str, Any]:
        if not self.settings.github_enabled or not self.settings.github_token:
            return {"status": "commented", "issue_number": issue_number, "backend": "local"}

        url = (
            f"https://api.github.com/repos/{self.settings.github_owner}/"
            f"{self.settings.github_repo}/issues/{issue_number}/comments"
        )
        headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json={"body": body})
            resp.raise_for_status()
            data = resp.json()
        return {"id": data.get("id"), "html_url": data.get("html_url"), "backend": "github"}
