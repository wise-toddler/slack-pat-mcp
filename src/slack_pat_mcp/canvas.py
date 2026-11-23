"""Convert Slack canvas HTML (the canvas file's download) to markdown, with section ids for canvases.edit."""

from html.parser import HTMLParser

_BLOCKS = {"h1": "# ", "h2": "## ", "h3": "### ", "p": "", "li": "- "}
_MARKS = {"b": "**", "strong": "**", "i": "_", "em": "_", "s": "~~", "del": "~~", "strike": "~~", "code": "`"}


class _Canvas(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines, self.sections = [], []
        self.buf, self.block, self.links = [], None, []
        self.row, self.rows_done, self.in_cell = [], 0, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.in_cell, self.buf = True, []
        elif tag in _BLOCKS and not self.in_cell and self.block is None:
            self.block, self.buf = (tag, a.get("id")), [_BLOCKS[tag]]
        elif tag in _MARKS:
            self.buf.append(_MARKS[tag])
        elif tag in ("lnk", "a"):
            self.links.append((a.get("href", ""), len(self.buf)))
        elif tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.row.append("".join(self.buf).strip().replace("\n", " "))
            self.in_cell, self.buf = False, []
        elif tag == "tr":
            self.lines.append("| " + " | ".join(self.row) + " |")
            if self.rows_done == 0:
                self.lines.append("|" + "---|" * len(self.row))
            self.rows_done += 1
        elif tag == "table":
            self.rows_done = 0
        elif self.block and tag == self.block[0]:
            text = "".join(self.buf).rstrip()
            self.lines.append(text)
            if self.block[1] and text.strip():
                self.sections.append({"id": self.block[1], "type": tag, "text": text})
            self.block, self.buf = None, []
        elif tag in _MARKS:
            self.buf.append(_MARKS[tag])
        elif tag in ("lnk", "a") and self.links:
            href, start = self.links.pop()
            label = "".join(self.buf[start:]).strip()
            self.buf[start:] = [f"[{label}]({href})" if label and label != href else href]

    def handle_data(self, data):
        if self.block or self.in_cell:
            self.buf.append(data)
        elif data.strip():
            self.lines.append(data.strip())


def html_to_markdown(html):
    """Return (markdown, sections) for a canvas; sections are [{id, type, text}] usable as canvases.edit section_id."""
    p = _Canvas()
    p.feed(html)
    p.close()
    return "\n".join(p.lines).strip("\n"), p.sections
