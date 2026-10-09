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
- **slack_users** — list, info, profile, usergroups, set_status
- **slack_drafts** — create, list, update, delete (needs browser session keys below)

## Drafts (optional)

Slack's drafts API rejects xoxp tokens, so drafts use your browser session. In `app.slack.com` DevTools:

- `SLACK_XOXC_TOKEN` — Console: `Object.values(JSON.parse(localStorage.localConfig_v2).teams).map(t => [t.name, t.token])`
- `SLACK_D_COOKIE` — Application → Cookies → `https://app.slack.com` → `d` (copy as-is, URL-encoded)

These are unofficial and stop working when you sign out of Slack in that browser.

## Required Slack OAuth Scopes (User Token)

channels:read, channels:history, groups:read, groups:history, im:read, im:history, im:write, mpim:read, mpim:history, mpim:write, chat:write, reactions:read, reactions:write, search:read, users:read, users:read.email, users.profile:read, usergroups:read
