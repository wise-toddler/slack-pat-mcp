# slack-pat-mcp

MCP server for personal Slack access using user tokens (xoxp-). 4 tools covering channels, DMs, chat, search, and user management.

## Install

```bash
uvx slack-pat-mcp
```

## Claude Code Config

```json
"slack": {
    "command": "uvx",
    "args": ["slack-pat-mcp"],
    "env": {
        "SLACK_USER_TOKEN": "xoxp-...",
        "SLACK_TEAM_ID": "T..."
    }
}
```

## Tools

- **slack_channel** — list, list_dms, history, thread, open_dm
- **slack_chat** — post, update, delete, react_add, react_remove
- **slack_search** — search messages with Slack syntax
- **slack_users** — list, info, profile, usergroups

## Required Slack OAuth Scopes (User Token)

channels:read, channels:history, groups:read, groups:history, im:read, im:history, im:write, mpim:read, mpim:history, mpim:write, chat:write, reactions:read, reactions:write, search:read, users:read, users:read.email, users.profile:read, usergroups:read
