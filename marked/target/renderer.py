"""
HTML Renderer for marked Python parser.
"""

import re
import urllib.parse
from typing import List, Optional, Any
from tokens import Token, TableCellToken


def escape_html(html: str, encode: bool = False) -> str:
    """Escape special HTML characters."""
    if encode:
        html = re.sub(r'&', '&amp;', html)
        html = re.sub(r'<', '&lt;', html)
        html = re.sub(r'>', '&gt;', html)
        html = re.sub(r'"', '&quot;', html)
        html = re.sub(r"'", '&#39;', html)
    else:
        # Avoid escaping already escaped entities
        html = re.sub(r'&(?!(#[0-9]{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)', '&amp;', html)
        html = re.sub(r'<', '&lt;', html)
        html = re.sub(r'>', '&gt;', html)
        html = re.sub(r'"', '&quot;', html)
        html = re.sub(r"'", '&#39;', html)
    return html


def clean_url(href: str) -> Optional[str]:
    """Clean and encode URL href attributes."""
    try:
        href = urllib.parse.quote(href, safe=":/?#[]@!$&'()*+,;=-_.~%")
    except Exception:
        return None
    return href


class HTMLRenderer:
    def __init__(self, parser=None):
        self.parser = parser

    def space(self, token: Token) -> str:
        return ""

    def code(self, code_text: str, lang: Optional[str] = None, escaped: bool = False) -> str:
        lang_str = lang.strip().split()[0] if lang and lang.strip() else ""
        code_body = code_text.rstrip("\n") + "\n"
        code_formatted = code_body if escaped else escape_html(code_body, encode=True)
        if lang_str:
            return f'<pre><code class="language-{escape_html(lang_str)}">{code_formatted}</code></pre>\n'
        return f'<pre><code>{code_formatted}</code></pre>\n'

    def blockquote(self, quote_html: str) -> str:
        return f'<blockquote>\n{quote_html}</blockquote>\n'

    def html(self, html_text: str) -> str:
        return html_text

    def heading(self, text_html: str, depth: int) -> str:
        return f'<h{depth}>{text_html}</h{depth}>\n'

    def hr(self) -> str:
        return '<hr>\n'

    def list(self, body_html: str, ordered: bool, start: Any = "") -> str:
        tag = "ol" if ordered else "ul"
        start_attr = f' start="{start}"' if ordered and start and str(start) != "1" else ""
        return f'<{tag}{start_attr}>\n{body_html}</{tag}>\n'

    def listitem(self, item_html: str) -> str:
        return f'<li>{item_html}</li>\n'

    def checkbox(self, checked: bool) -> str:
        checked_attr = 'checked="" ' if checked else ''
        return f'<input {checked_attr}disabled="" type="checkbox"> '

    def paragraph(self, text_html: str) -> str:
        return f'<p>{text_html}</p>\n'

    def table(self, header_html: str, body_html: str) -> str:
        tbody = f'<tbody>{body_html}</tbody>' if body_html else ''
        return f'<table>\n<thead>\n{header_html}</thead>\n{tbody}</table>\n'

    def tablerow(self, content_html: str) -> str:
        return f'<tr>\n{content_html}</tr>\n'

    def tablecell(self, cell_html: str, header: bool, align: Optional[str] = None) -> str:
        tag = "th" if header else "td"
        align_attr = f' align="{align}"' if align else ''
        return f'<{tag}{align_attr}>{cell_html}</{tag}>\n'

    def strong(self, text_html: str) -> str:
        return f'<strong>{text_html}</strong>'

    def em(self, text_html: str) -> str:
        return f'<em>{text_html}</em>'

    def codespan(self, code_text: str) -> str:
        return f'<code>{escape_html(code_text, encode=True)}</code>'

    def br(self) -> str:
        return '<br>'

    def del_element(self, text_html: str) -> str:
        return f'<del>{text_html}</del>'

    def link(self, href: str, title: Optional[str], text_html: str) -> str:
        cleaned = clean_url(href)
        if cleaned is None:
            return text_html
        title_attr = f' title="{escape_html(title)}"' if title else ''
        return f'<a href="{cleaned}"{title_attr}>{text_html}</a>'

    def image(self, href: str, title: Optional[str], alt_text: str) -> str:
        cleaned = clean_url(href)
        if cleaned is None:
            return escape_html(alt_text)
        title_attr = f' title="{escape_html(title)}"' if title else ''
        return f'<img src="{cleaned}" alt="{escape_html(alt_text)}"{title_attr}>'

    def text(self, text_content: str, escaped: bool = False) -> str:
        return text_content if escaped else escape_html(text_content)
