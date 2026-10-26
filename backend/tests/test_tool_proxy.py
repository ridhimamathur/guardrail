import pytest

from app.tool_proxy.proxy import ToolProxy


def test_proxy_rejects_unknown_and_destructive_actions():
    proxy = ToolProxy()
    with pytest.raises(PermissionError):
        proxy.execute("storage", "delete_file", {"object_name": "anything"})
    with pytest.raises(PermissionError):
        proxy.execute("smtp", "send", {})
