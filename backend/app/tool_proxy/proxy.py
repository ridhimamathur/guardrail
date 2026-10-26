"""Secure Tool Proxy — only component that holds external credentials and executes tools."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.tool_proxy.email_adapter import EmailAdapter
from app.tool_proxy.storage_adapter import StorageAdapter
from app.tool_proxy.ticket_adapter import TicketAdapter

ALLOWED_ACTIONS = {
    ("email", "search_email"),
    ("email", "read_email"),
    ("email", "send_email"),
    ("storage", "list_files"),
    ("storage", "read_file"),
    ("storage", "upload_file"),
    ("storage", "share_file"),
    ("ticket", "create_ticket"),
    ("ticket", "add_comment"),
}


class ToolProxy:
    def __init__(self) -> None:
        self.email = EmailAdapter()
        self.storage = StorageAdapter()
        self.ticket = TicketAdapter()

    def execute(self, tool: str, action: str, parameters: dict[str, Any]) -> dict[str, Any]:
        if (tool, action) not in ALLOWED_ACTIONS:
            if action == "delete_file":
                raise PermissionError("delete_file is blocked in Phase 1 (P5)")
            raise PermissionError(f"Tool Proxy rejects unknown or unauthorized action: {tool}.{action}")

        params = parameters or {}

        if tool == "email":
            if action == "search_email":
                return self.email.search_email(params.get("query", ""), int(params.get("max_results", 5)))
            if action == "read_email":
                return self.email.read_email(params["message_id"])
            if action == "send_email":
                return self.email.send_email(
                    to=params["to"],
                    subject=params.get("subject", "GuardRAIL message"),
                    body=params.get("body", ""),
                )

        if tool == "storage":
            if action == "list_files":
                return self.storage.list_files(params.get("bucket"), params.get("prefix", ""))
            if action == "read_file":
                result = self.storage.read_file(params["object_name"], params.get("bucket"))
                # Strip raw bytes from API-facing summary
                return {k: v for k, v in result.items() if k != "content_bytes"}
            if action == "upload_file":
                return self.storage.upload_file(
                    object_name=params["object_name"],
                    content=params.get("content", ""),
                    bucket=params.get("bucket"),
                    content_type=params.get("content_type", "text/plain"),
                )
            if action == "share_file":
                return self.storage.share_file(
                    object_name=params["object_name"],
                    recipient=params["recipient"],
                    bucket=params.get("bucket"),
                    note=params.get("note", ""),
                )

        if tool == "ticket":
            if action == "create_ticket":
                return self.ticket.create_ticket(
                    title=params["title"],
                    body=params.get("body", ""),
                    labels=params.get("labels"),
                )
            if action == "add_comment":
                return self.ticket.add_comment(int(params["issue_number"]), params.get("body", ""))

        raise PermissionError(f"Unhandled action: {tool}.{action}")


@lru_cache
def get_tool_proxy() -> ToolProxy:
    return ToolProxy()
