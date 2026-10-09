"""Convert Slack mrkdwn to rich_text blocks and back (the drafts API only takes rich_text)."""

import re

_LIST_ITEM = re.compile(r"^\s*(?:([•\-*])|\d+[.)])\s+(.*)$")
_QUOTE = re.compile(r"^(?:>|&gt;) ?(.*)$")
_INLINE = re.compile(
    r"<(?P<link>https?://[^|>\s]+)(?:\|(?P<label>[^>]+))?>"
    r"|<@(?P<user>[UW][A-Z0-9]+)(?:\|[^>]*)?>"
    r"|<#(?P<channel>C[A-Z0-9]+)(?:\|[^>]*)?>"
    r"|`(?P<code>[^`\n]+)`"
    r"|(?<![\w*])\*(?!\s)(?P<bold>[^*\n]+?)(?<!\s)\*(?![\w*])"
    r"|(?<![\w_])_(?!\s)(?P<italic>[^_\n]+?)(?<!\s)_(?![\w_])"
    r"|(?<![\w~])~(?!\s)(?P<strike>[^~\n]+?)(?<!\s)~(?![\w~])"
    r"|(?P<url>https?://[^\s<>]*[^\s<>.,;:!?)\]'\"])"
    r"|:(?P<emoji>[a-z0-9_+\-]*[a-z][a-z0-9_+\-]*):(?!//)"
)
_MARKS = {"bold": "*", "italic": "_", "strike": "~"}


def _unescape(s):
    """Undo mrkdwn entity escapes; rich_text text is literal."""
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def _inline(text):
    """Parse inline mrkdwn (styles, links, mentions, emoji) into rich_text elements."""
    out, pos = [], 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            out.append({"type": "text", "text": _unescape(text[pos:m.start()])})
        pos = m.end()
        style = next((s for s in _MARKS if m[s]), None)
        if style:
            for el in _inline(m[style]):
                if el["type"] in ("text", "link"):
                    el.setdefault("style", {})[style] = True
                out.append(el)
        elif m["link"]:
            out.append({"type": "link", "url": m["link"], **({"text": _unescape(m["label"])} if m["label"] else {})})
        elif m["user"]:
            out.append({"type": "user", "user_id": m["user"]})
        elif m["channel"]:
            out.append({"type": "channel", "channel_id": m["channel"]})
        elif m["code"]:
            out.append({"type": "text", "text": _unescape(m["code"]), "style": {"code": True}})
        elif m["url"]:
            out.append({"type": "link", "url": m["url"]})
        else:
            out.append({"type": "emoji", "name": m["emoji"]})
    if pos < len(text):
        out.append({"type": "text", "text": _unescape(text[pos:])})
    return out


def to_blocks(text):
    """Convert mrkdwn to one rich_text block: sections, bullet/ordered lists, quotes, code blocks."""
    elements, buf, kind, code = [], [], None, None

    def flush(next_kind):
        """Emit buffered lines as one element; a section before a non-section ends with a newline, like Slack's composer."""
        if not buf:
            return
        if kind in ("bullet", "ordered"):
            items = [{"type": "rich_text_section", "elements": _inline(b)} for b in buf]
            elements.append({"type": "rich_text_list", "style": kind, "indent": 0, "border": 0, "elements": items})
        else:
            body = "\n".join(buf) + ("\n" if kind == "section" and next_kind in ("bullet", "ordered", "quote", "code") else "")
            if body:
                elements.append({"type": "rich_text_quote" if kind == "quote" else "rich_text_section", "elements": _inline(body)})
        buf.clear()

    def preformatted(lines):
        return {"type": "rich_text_preformatted", "border": 0, "elements": [{"type": "text", "text": "\n".join(lines).strip("\n")}]}

    for line in text.strip("\n").split("\n"):
        if code is not None:
            if line.rstrip().endswith("```"):
                code.append(line.rstrip()[:-3])
                elements.append(preformatted(code))
                code = None
            else:
                code.append(line)
            continue
        if line.lstrip().startswith("```"):
            flush("code")
            kind, rest = None, line.strip()[3:]
            if rest.endswith("```"):
                elements.append(preformatted([rest[:-3]]))
            else:
                code = [rest]
            continue
        m, q = _LIST_ITEM.match(line), _QUOTE.match(line)
        line_kind = ("bullet" if m[1] else "ordered") if m else "quote" if q else "section"
        if line_kind != kind:
            flush(line_kind)
            kind = line_kind
        buf.append(m[2] if m else q[1] if q else line)
    if code is not None:
        elements.append(preformatted(code))
    flush(None)
    return [{"type": "rich_text", "elements": elements}]


def _render(elements):
    """Render inline rich_text elements to mrkdwn, wrapping same-style runs once."""
    out, active = [], set()
    for e in elements:
        style = {k for k, v in e.get("style", {}).items() if v and k in _MARKS}
        out += [_MARKS[k] for k in ("strike", "italic", "bold") if k in active - style]
        out += [_MARKS[k] for k in ("bold", "italic", "strike") if k in style - active]
        active = style
        t = e.get("type")
        if t == "link":
            s = f"<{e['url']}|{e['text']}>" if e.get("text") else e["url"]
        elif t == "user":
            s = f"<@{e['user_id']}>"
        elif t == "channel":
            s = f"<#{e['channel_id']}>"
        elif t == "emoji":
            s = f":{e['name']}:"
        elif t == "usergroup":
            s = f"<!subteam^{e['usergroup_id']}>"
        elif t == "broadcast":
            s = f"<!{e['range']}>"
        else:
            s = e.get("text", "")
        out.append(f"`{s}`" if e.get("style", {}).get("code") else s)
    out += [_MARKS[k] for k in ("strike", "italic", "bold") if k in active]
    return "".join(out)


def to_text(blocks):
    """Render rich_text blocks back to mrkdwn."""
    parts = []
    for block in blocks:
        for el in block.get("elements", []):
            t = el.get("type")
            if t == "rich_text_list":
                start = el.get("offset", 0)
                marks = [f"{start + i + 1}. " if el.get("style") == "ordered" else "• " for i in range(len(el.get("elements", [])))]
                body = "\n".join("  " * el.get("indent", 0) + mk + _render(s.get("elements", [])) for mk, s in zip(marks, el.get("elements", [])))
            elif t == "rich_text_quote":
                body = "\n".join("> " + ln for ln in _render(el.get("elements", [])).split("\n"))
            elif t == "rich_text_preformatted":
                body = "```\n" + _render(el.get("elements", [])) + "\n```"
            else:
                body = _render(el.get("elements", []))
            if parts and not parts[-1].endswith("\n"):
                parts.append("\n")
            parts.append(body)
    return "".join(parts)
