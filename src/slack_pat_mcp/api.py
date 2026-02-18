"""Slack Web API wrapper using user token with form-encoded POST."""

import time

import requests

from .config import HEADERS

BASE = "https://slack.com/api"


def _post(method: str, data: dict) -> dict:
    """POST to Slack API, retry once on 429, check response ok."""
    resp = requests.post(f"{BASE}/{method}", headers=HEADERS, data=data, timeout=30)
    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 1))
        time.sleep(wait)
        resp = requests.post(f"{BASE}/{method}", headers=HEADERS, data=data, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if not body.get("ok"):
        raise RuntimeError(f"Slack {method}: {body.get('error', body)}")
    return body


def conversations_list(types: str, cursor: str = "", limit: int = 100) -> dict:
    """List conversations by type."""
    return _post("conversations.list", {"types": types, "cursor": cursor, "limit": limit})


def conversations_history(channel: str, cursor: str = "", limit: int = 20, oldest: str = "", latest: str = "") -> dict:
    """Get channel message history."""
    data = {"channel": channel, "cursor": cursor, "limit": limit}
    if oldest:
        data["oldest"] = oldest
    if latest:
        data["latest"] = latest
    return _post("conversations.history", data)


def conversations_replies(channel: str, ts: str, cursor: str = "", limit: int = 50) -> dict:
    """Get thread replies."""
    return _post("conversations.replies", {"channel": channel, "ts": ts, "cursor": cursor, "limit": limit})


def conversations_open(users: str) -> dict:
    """Open a DM/group DM with comma-separated user IDs."""
    return _post("conversations.open", {"users": users})


def chat_post(channel: str, text: str, thread_ts: str = "") -> dict:
    """Post a message to a channel or thread."""
    data = {"channel": channel, "text": text}
    if thread_ts:
        data["thread_ts"] = thread_ts
    return _post("chat.postMessage", data)


def chat_update(channel: str, ts: str, text: str) -> dict:
    """Update an existing message."""
    return _post("chat.update", {"channel": channel, "ts": ts, "text": text})


def chat_delete(channel: str, ts: str) -> dict:
    """Delete a message."""
    return _post("chat.delete", {"channel": channel, "ts": ts})


def reactions_add(channel: str, timestamp: str, name: str) -> dict:
    """Add a reaction emoji to a message."""
    return _post("reactions.add", {"channel": channel, "timestamp": timestamp, "name": name})


def reactions_remove(channel: str, timestamp: str, name: str) -> dict:
    """Remove a reaction emoji from a message."""
    return _post("reactions.remove", {"channel": channel, "timestamp": timestamp, "name": name})


def search_messages(query: str, sort: str = "timestamp", cursor: str = "", count: int = 20) -> dict:
    """Search messages in the workspace."""
    data = {"query": query, "sort": sort, "count": count}
    if cursor:
        data["cursor"] = cursor
    return _post("search.messages", data)


def users_list(cursor: str = "", limit: int = 100) -> dict:
    """List workspace users."""
    return _post("users.list", {"cursor": cursor, "limit": limit})


def users_info(user: str) -> dict:
    """Get info for a single user."""
    return _post("users.info", {"user": user})


def users_profile(user: str) -> dict:
    """Get detailed profile for a user."""
    return _post("users.profile.get", {"user": user})


def usergroups_list() -> dict:
    """List all user groups in the workspace."""
    return _post("usergroups.list", {"include_users": "true"})
