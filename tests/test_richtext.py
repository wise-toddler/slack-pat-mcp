"""Checks mrkdwn <-> rich_text against the structure Slack's own composer produces."""

from slack_pat_mcp.richtext import to_blocks, to_text


def _rt(*elements):
    return [{"type": "rich_text", "elements": list(elements)}]


def _sec(*els):
    return {"type": "rich_text_section", "elements": list(els)}


def _t(text, **style):
    return {"type": "text", "text": text, **({"style": style} if style else {})}


def test_matches_native_composer():
    """Bold lead line + bullets + links, as the Slack composer stored it for a real message."""
    pr, issue = "https://github.com/emergentbase/xllm/pull/428", "https://github.com/emergentbase/xllm/issues/426"
    md = (f"*<{pr}|xllm#428>: stream idle timeout*\n• *Some Bedrock streams hang*\n• PR adds a `300s` wait\n"
          f"• Open question: each\n<{pr}|PR #428> · <{issue}|issue #426>")
    native = _rt(
        _sec({"type": "link", "url": pr, "text": "xllm#428", "style": {"bold": True}}, _t(": stream idle timeout", bold=True), _t("\n")),
        {"type": "rich_text_list", "style": "bullet", "indent": 0, "border": 0, "elements": [
            _sec(_t("Some Bedrock streams hang", bold=True)),
            _sec(_t("PR adds a "), _t("300s", code=True), _t(" wait")),
            _sec(_t("Open question: each")),
        ]},
        _sec({"type": "link", "url": pr, "text": "PR #428"}, _t(" · "), {"type": "link", "url": issue, "text": "issue #426"}),
    )
    assert to_blocks(md) == native
    assert to_text(native) == md


def test_peer_repro():
    """The reported bug: *a* then a bullet."""
    assert to_blocks("*a*\n• b") == _rt(_sec(_t("a", bold=True), _t("\n")), {"type": "rich_text_list", "style": "bullet", "indent": 0, "border": 0, "elements": [_sec(_t("b"))]})


def test_ordered_quote_code_roundtrip():
    md = "1. one\n2. two\n> quoted *bold*\n```\nx = 1\n\ny = 2\n```\nafter"
    blocks = to_blocks(md)
    kinds = [e["type"] for e in blocks[0]["elements"]]
    assert kinds == ["rich_text_list", "rich_text_quote", "rich_text_preformatted", "rich_text_section"], kinds
    assert blocks[0]["elements"][0]["style"] == "ordered"
    assert blocks[0]["elements"][2]["elements"][0]["text"] == "x = 1\n\ny = 2"
    assert to_text(blocks) == md


def test_inline_edge_cases():
    """snake_case, URLs with underscores, times and label:url must stay literal/links, not styles/emoji."""
    assert to_blocks("use my_var at 10:30:45 see https://x.com/a_b_c.")[0]["elements"][0]["elements"] == [
        _t("use my_var at 10:30:45 see "), {"type": "link", "url": "https://x.com/a_b_c"}, _t(".")]
    assert to_blocks("Link:https://x.com")[0]["elements"][0]["elements"] == [_t("Link:"), {"type": "link", "url": "https://x.com"}]
    assert to_blocks("hey <@U0ALM4FNFJ7> :tada: a &lt; b")[0]["elements"][0]["elements"] == [
        _t("hey "), {"type": "user", "user_id": "U0ALM4FNFJ7"}, _t(" "), {"type": "emoji", "name": "tada"}, _t(" a < b")]
    assert to_text(to_blocks("plain line\nsecond line")) == "plain line\nsecond line"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
