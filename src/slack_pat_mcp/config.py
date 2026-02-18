"""Slack PAT MCP configuration - loads env vars and builds headers."""

import os

TOKEN = os.environ.get("SLACK_USER_TOKEN", "")
TEAM_ID = os.environ.get("SLACK_TEAM_ID", "")

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/x-www-form-urlencoded",
}
