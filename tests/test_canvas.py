"""Checks canvas HTML -> markdown and the canvas API payloads."""

import json

from slack_pat_mcp import api
from slack_pat_mcp.canvas import html_to_markdown

# Shape copied from a real canvas download: quip div, ids on blocks, <lnk> links, tables with <p> in cells
HTML = (
    '<div class="quip-canvas-content"><h1 id="temp:C:A1">Plan</h1>'
    '<p id="temp:C:A2" class="line">Hi <b>team</b>, see <lnk href="https://x.com">doc</lnk> and '
    '<lnk href="mailto:a@b.co">a@b.co</lnk><br>next line</p>'
    '<ul><li id="temp:C:A3">one</li><li id="temp:C:A4"><i>two</i></li></ul>'
    '<table><tr><th><p id="temp:C:T1" class="line">Name</p></th><th><p id="temp:C:T2" class="line">Count</p></th></tr>'
    '<tr><td><p id="temp:C:T3" class="line">x &amp; y</p></td><td><p id="temp:C:T4" class="line">3</p></td></tr></table>'
    '<p id="temp:C:A5" class="line"></p></div>'
)


def test_html_to_markdown():
    md, sections = html_to_markdown(HTML)
    assert md == ("# Plan\n"
                  "Hi **team**, see [doc](https://x.com) and [a@b.co](mailto:a@b.co)\nnext line\n"
                  "- one\n- _two_\n"
                  "| Name | Count |\n|---|---|\n| x & y | 3 |"), md
    assert [s["id"] for s in sections] == ["temp:C:A1", "temp:C:A2", "temp:C:A3", "temp:C:A4"], sections


class _Resp:
    def __init__(self, body):
        self.status_code, self.headers, self._body = 200, {}, body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_edit_payload_and_session_hint():
    sent = []

    def post(url, headers, data, timeout):
        sent.append((url, data))
        if "Cookie" in headers:
            return _Resp({"ok": False, "error": "not_allowed_token_type"})
        return _Resp({"ok": True} if not url.endswith("canvases.delete") else {"ok": False, "error": "token_revoked"})
    api.requests.post, api.XOXC_TOKEN, api.D_COOKIE = post, "xoxc-x", "xoxd-x"
    api.canvases_edit("F1", "replace", "new **text**", "temp:C:A2")
    url, data = sent[0]
    assert url.endswith("canvases.edit") and data["canvas_id"] == "F1"
    assert json.loads(data["changes"]) == [{"operation": "replace", "document_content": {"type": "markdown", "markdown": "new **text**"}, "section_id": "temp:C:A2"}]
    try:
        api.canvases_delete("F1")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as e:
        assert "needs a valid xoxp PAT" in str(e), e


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
