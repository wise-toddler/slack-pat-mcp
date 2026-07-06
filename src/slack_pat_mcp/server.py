"""Slack PAT MCP Server."""
import json
import re
import sys
from . import api

_user_cache = {}

TOOLS = [
    {
        "name": "slack_channel",
        "description": "Manage Slack conversations. Actions: list, list_dms, history, thread, open_dm",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "list_dms", "history", "thread", "open_dm"]},
                "types": {"type": "string", "default": "public_channel,private_channel", "description": "Channel types (for list)"},
                "channel": {"type": "string", "description": "Channel ID (for history/thread)"},
                "thread_ts": {"type": "string", "description": "Parent message timestamp (for thread)"},
                "users": {"type": "string", "description": "Comma-separated user IDs (for open_dm)"},
                "oldest": {"type": "string", "description": "Unix timestamp lower bound (for history)"},
                "latest": {"type": "string", "description": "Unix timestamp upper bound (for history)"},
                "cursor": {"type": "string", "description": "Pagination cursor"},
                "limit": {"type": "integer", "default": 20, "description": "Results per page"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "slack_chat",
        "description": "Send, edit, delete messages and react. Actions: post, update, delete, react_add, react_remove",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["post", "update", "delete", "react_add", "react_remove"]},
                "channel": {"type": "string", "description": "Channel ID"},
                "text": {"type": "string", "description": "Message text (for post/update)"},
                "ts": {"type": "string", "description": "Message timestamp (for update/delete/react)"},
                "thread_ts": {"type": "string", "description": "Reply to thread (for post)"},
                "emoji": {"type": "string", "description": "Emoji name without colons (for react)"},
            },
            "required": ["action", "channel"]
        }
    },
    {
        "name": "slack_search",
        "description": "Search messages. Supports Slack syntax: from:user in:channel has:emoji before:date after:date",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "sort": {"type": "string", "default": "timestamp", "enum": ["timestamp", "score"]},
                "count": {"type": "integer", "default": 20},
                "cursor": {"type": "string", "description": "Pagination cursor"},
            },
            "required": ["query"]
        }
    },
    {
        "name": "slack_files",
        "description": "File operations. Actions: list, info, upload, delete",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "info", "upload", "delete"]},
                "channel": {"type": "string", "description": "Channel ID (for list/upload)"},
                "file_id": {"type": "string", "description": "File ID (for info/delete)"},
                "content": {"type": "string", "description": "Text content to upload (for upload)"},
                "filename": {"type": "string", "default": "file.txt", "description": "Filename (for upload)"},
                "title": {"type": "string", "description": "File title (for upload)"},
                "cursor": {"type": "string", "description": "Pagination cursor"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["action"]
        }
    },
    {
        "name": "slack_users",
        "description": "User operations. Actions: list, info, profile, usergroups",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "info", "profile", "usergroups", "set_status"]},
                "user_id": {"type": "string", "description": "User ID (for info/profile)"},
                "status_text": {"type": "string", "description": "Status message (for set_status)"},
                "status_emoji": {"type": "string", "description": "Status emoji e.g. :coffee: (for set_status)"},
                "status_expiration": {"type": "integer", "default": 0, "description": "Unix timestamp when status expires, 0=no expiry (for set_status)"},
                "cursor": {"type": "string", "description": "Pagination cursor"},
                "limit": {"type": "integer", "default": 100},
            },
            "required": ["action"]
        }
    },
]


def _condense_channel(ch):
    return {
        "id": ch.get("id"),
        "name": ch.get("name", ch.get("id")),
        "type": "im" if ch.get("is_im") else "mpim" if ch.get("is_mpim") else "channel",
        "is_member": ch.get("is_member", False),
        "num_members": ch.get("num_members", 0),
    }


def _resolve_mentions(text):
    """Replace <@U...> with <@U...> (display_name)."""
    if not text:
        return text
    _ensure_user_cache()
    return re.sub(r"<@(U[A-Z0-9]+)>", lambda m: f"<@{m.group(1)}> ({_user_cache.get(m.group(1), m.group(1))})", text)


def _condense_message(msg):
    return {
        "ts": msg.get("ts"),
        "user": msg.get("user"),
        "text": _resolve_mentions(msg.get("text")),
        "reactions": msg.get("reactions"),
        "reply_count": msg.get("reply_count"),
        "thread_ts": msg.get("thread_ts"),
    }


def _condense_file(f):
    return {
        "id": f.get("id"),
        "name": f.get("name"),
        "title": f.get("title"),
        "filetype": f.get("filetype"),
        "size": f.get("size"),
        "user": f.get("user"),
        "channels": f.get("channels", []),
        "url_private": f.get("url_private"),
        "created": f.get("created"),
    }


def _condense_user(u):
    p = u.get("profile", {})
    return {
        "id": u.get("id"),
        "name": u.get("name"),
        "real_name": u.get("real_name", p.get("real_name", "")),
        "display_name": p.get("display_name", ""),
        "email": p.get("email", ""),
    }


def _ensure_user_cache():
    global _user_cache
    if _user_cache:
        return
    result = api.users_list(limit=200)
    for u in result.get("members", []):
        p = u.get("profile", {})
        _user_cache[u["id"]] = p.get("display_name") or u.get("real_name") or u.get("name", "")


def _paginated(data, key):
    items = data.get(key, [])
    cursor = data.get("response_metadata", {}).get("next_cursor", "")
    return {key: items, "next_cursor": cursor}


def handle_channel(args):
    action = args["action"]
    if action == "list":
        data = api.conversations_list(args.get("types", "public_channel,private_channel"), args.get("cursor", ""), args.get("limit", 100))
        r = _paginated(data, "channels")
        r["channels"] = [_condense_channel(ch) for ch in r["channels"]]
        return r
    if action == "list_dms":
        data = api.conversations_list("im,mpim", args.get("cursor", ""), args.get("limit", 50))
        _ensure_user_cache()
        dms = [{"channel_id": ch.get("id"), "user_id": ch.get("user", ""), "user_name": _user_cache.get(ch.get("user", ""), ch.get("user", ""))} for ch in data.get("channels", [])]
        return {"dms": dms, "next_cursor": data.get("response_metadata", {}).get("next_cursor", "")}
    if action == "history":
        data = api.conversations_history(args["channel"], args.get("cursor", ""), args.get("limit", 20), args.get("oldest", ""), args.get("latest", ""))
        r = _paginated(data, "messages")
        r["messages"] = [_condense_message(m) for m in r["messages"]]
        return r
    if action == "thread":
        data = api.conversations_replies(args["channel"], args["thread_ts"], args.get("cursor", ""), args.get("limit", 50))
        r = _paginated(data, "messages")
        r["messages"] = [_condense_message(m) for m in r["messages"]]
        return r
    if action == "open_dm":
        return api.conversations_open(args["users"])
    return {"error": f"Unknown action: {action}"}


def handle_chat(args):
    action = args["action"]
    if action == "post":
        return api.chat_post(args["channel"], args["text"], args.get("thread_ts", ""))
    if action == "update":
        return api.chat_update(args["channel"], args["ts"], args["text"])
    if action == "delete":
        api.chat_delete(args["channel"], args["ts"])
        return {"success": True}
    if action == "react_add":
        api.reactions_add(args["channel"], args["ts"], args["emoji"])
        return {"success": True}
    if action == "react_remove":
        api.reactions_remove(args["channel"], args["ts"], args["emoji"])
        return {"success": True}
    return {"error": f"Unknown action: {action}"}


def handle_files(args):
    action = args["action"]
    if action == "list":
        data = api.files_list(args.get("channel", ""), args.get("cursor", ""), args.get("limit", 20))
        files = [_condense_file(f) for f in data.get("files", [])]
        paging = data.get("paging", {})
        return {"files": files, "paging": paging}
    if action == "info":
        return _condense_file(api.files_info(args["file_id"]).get("file", {}))
    if action == "upload":
        return api.files_upload(args.get("channel", ""), args["content"], args.get("filename", "file.txt"), args.get("title", ""))
    if action == "delete":
        api.files_delete(args["file_id"])
        return {"success": True}
    return {"error": f"Unknown action: {action}"}


def handle_users(args):
    action = args["action"]
    if action == "list":
        data = api.users_list(args.get("cursor", ""), args.get("limit", 100))
        r = _paginated(data, "members")
        r["members"] = [_condense_user(u) for u in r["members"]]
        return r
    if action == "info":
        return _condense_user(api.users_info(args["user_id"]).get("user", {}))
    if action == "profile":
        return api.users_profile(args["user_id"])
    if action == "usergroups":
        return api.usergroups_list()
    if action == "set_status":
        profile = {
            "status_text": args.get("status_text", ""),
            "status_emoji": args.get("status_emoji", ""),
            "status_expiration": args.get("status_expiration", 0),
        }
        return api.users_profile_set(profile)
    return {"error": f"Unknown action: {action}"}


def handle_tool(name, args):
    try:
        if name == "slack_channel":
            return handle_channel(args)
        if name == "slack_chat":
            return handle_chat(args)
        if name == "slack_files":
            return handle_files(args)
        if name == "slack_search":
            return api.search_messages(args["query"], args.get("sort", "timestamp"), args.get("cursor", ""), args.get("count", 20))
        if name == "slack_users":
            return handle_users(args)
        return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    """MCP server main loop."""
    for ln in sys.stdin:
        try:
            msg = json.loads(ln)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "initialize":
            res = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "slack-pat-mcp", "version": "0.1.3"}
            }
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            params = msg.get("params", {})
            result = handle_tool(params.get("name", ""), params.get("arguments", {}))
            res = {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}
        else:
            res = {}

        response = {"jsonrpc": "2.0", "id": msg_id, "result": res}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
