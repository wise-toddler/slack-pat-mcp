"""Checks the PAT -> browser-session fallback on missing_scope."""

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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
