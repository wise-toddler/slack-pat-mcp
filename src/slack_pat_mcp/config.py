"""Slack PAT MCP configuration - loads env vars and builds headers."""

import os

TOKEN = os.environ.get("SLACK_USER_TOKEN", "")
TEAM_ID = os.environ.get("SLACK_TEAM_ID", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/x-www-form-urlencoded",
}

# Browser session keys: Slack's internal drafts API rejects xoxp tokens (not_allowed_token_type)
XOXC_TOKEN = os.environ.get("SLACK_XOXC_TOKEN", "")
D_COOKIE = os.environ.get("SLACK_D_COOKIE", "")

SESSION_HEADERS = {
    "Authorization": f"Bearer {XOXC_TOKEN}",
    "Cookie": f"d={D_COOKIE}",
    "Content-Type": "application/x-www-form-urlencoded",
}
