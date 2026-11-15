"""Checks the PAT -> browser-session fallback on missing_scope, and what chat calls send."""

import json

from slack_pat_mcp import api


class _Resp:
    def __init__(self, body):
        self.status_code, self.headers, self._body = 200, {}, body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def _fake_post(calls, pat_body):
    def post(url, headers, data, timeout):
        calls.append(headers)
        return _Resp(pat_body if headers is api.HEADERS else {"ok": True, "via": "session"})
    return post


def test_missing_scope_falls_back_to_session():
    calls = []
    api.requests.post, api.XOXC_TOKEN, api.D_COOKIE = _fake_post(calls, {"ok": False, "error": "missing_scope", "needed": "users.profile:write"}), "xoxc-x", "xoxd-x"
    assert api.users_profile_set({"status_text": "hi"})["via"] == "session"
    assert calls == [api.HEADERS, api.SESSION_HEADERS]


def test_revoked_pat_falls_back_to_session():
    calls = []
    api.requests.post, api.XOXC_TOKEN, api.D_COOKIE = _fake_post(calls, {"ok": False, "error": "token_revoked"}), "xoxc-x", "xoxd-x"
    assert api.conversations_list("public_channel")["via"] == "session"
    assert calls == [api.HEADERS, api.SESSION_HEADERS]


def test_no_fallback_without_keys_or_for_other_errors():
    calls = []
    api.requests.post, api.XOXC_TOKEN, api.D_COOKIE = _fake_post(calls, {"ok": False, "error": "missing_scope", "needed": "users.profile:write"}), "", ""
    try:
        api.users_profile_set({})
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "needs scope: users.profile:write" in str(e), e
    api.requests.post, api.XOXC_TOKEN, api.D_COOKIE = _fake_post(calls, {"ok": False, "error": "channel_not_found"}), "xoxc-x", "xoxd-x"
    try:
        api.chat_post("C1", "x")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "channel_not_found" in str(e), e
    assert api.SESSION_HEADERS not in calls


def test_post_and_update_send_rich_text_blocks():
    """Labelled links go as rich_text link elements; a text-only chat.update on the session token rendered them raw."""
    sent = []

    def post(url, headers, data, timeout):
        sent.append(data)
        return _Resp({"ok": True})
    api.requests.post = post
    text = "see <https://github.com/emergentbase/experiments/pull/2822|experiments#2822> <@U0ALM4FNFJ7>"
    api.chat_post("C1", text)
    api.chat_update("C1", "1.2", text)
    assert len(sent) == 2
    for data in sent:
        assert data["text"] == text
        els = json.loads(data["blocks"])[0]["elements"][0]["elements"]
        assert {"type": "link", "url": "https://github.com/emergentbase/experiments/pull/2822", "text": "experiments#2822"} in els, els
        assert {"type": "user", "user_id": "U0ALM4FNFJ7"} in els, els


class _File:
    def __init__(self, ctype, status=200):
        self.headers, self.content, self.status_code, self.ok = {"Content-Type": ctype}, b"x", status, status < 400


def test_download_bad_pat_falls_back_to_session():
    """A bad PAT gets a 403 or Slack's HTML login page instead of the file; the session cookie gets the file."""
    for pat_reply in (_File("text/html; charset=utf-8"), _File("text/html", 403)):
        seen = []

        def get(url, headers, timeout):
            seen.append("Cookie" in headers)
            return _File("image/png") if "Cookie" in headers else pat_reply
        api.requests.get, api.XOXC_TOKEN, api.D_COOKIE = get, "xoxc-x", "xoxd-x"
        assert api._get_file("https://files.slack.com/x.png", "image/png").headers["Content-Type"] == "image/png"
        assert seen == [False, True]
    api.XOXC_TOKEN = ""
    try:
        api._get_file("https://files.slack.com/x.png", "image/png")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "HTTP 403" in str(e), e


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
