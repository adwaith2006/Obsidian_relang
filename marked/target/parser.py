"""
Parser module for converting Markdown AST tokens into HTML.
"""

from typing import List
from tokens import (
    Token, SpaceToken, HeadingToken, CodeToken, BlockquoteToken,
    ListItemToken, ListToken, TableToken, HrToken, HtmlToken,
    ParagraphToken, TextToken, EscapeToken, LinkToken, ImageToken,
    StrongToken, EmToken, CodespanToken, BrToken, DelToken, CheckboxToken
)
from renderer import HTMLRenderer


class MarkdownParser:
    def __init__(self, renderer: HTMLRenderer = None):
        self.renderer = renderer or HTMLRenderer(parser=self)
        self.renderer.parser = self

    def parse(self, tokens: List[Token]) -> str:
        out = []
        for tok in tokens:
            t_type = tok.type

            if t_type == "space":
                out.append(self.renderer.space(tok))
            elif t_type == "heading":
                inner_html = self.parse_inline(tok.tokens) if tok.tokens else tok.text or ""
                out.append(self.renderer.heading(inner_html, getattr(tok, 'depth', 1)))
            elif t_type == "paragraph":
                inner_html = self.parse_inline(tok.tokens) if tok.tokens else tok.text or ""
                out.append(self.renderer.paragraph(inner_html))
            elif t_type == "code":
                out.append(self.renderer.code(tok.text or "", getattr(tok, 'lang', None), getattr(tok, 'escaped', False)))
            elif t_type == "blockquote":
                inner_html = self.parse(tok.tokens) if tok.tokens else ""
                out.append(self.renderer.blockquote(inner_html))
            elif t_type == "hr":
                out.append(self.renderer.hr())
            elif t_type == "list":
                items_html = ""
                is_list_loose = getattr(tok, 'loose', False)
                for item in getattr(tok, 'items', []):
                    item_is_loose = getattr(item, 'loose', is_list_loose)
                    item_content = self.parse_list_item(item.tokens, item_is_loose) if item.tokens else item.text or ""
                    items_html += self.renderer.listitem(item_content)
                out.append(self.renderer.list(items_html, getattr(tok, 'ordered', False), getattr(tok, 'start', "")))
            elif t_type == "html":
                out.append(self.renderer.html(tok.text or ""))
            elif t_type == "table":
                # Header
                header_cells_html = "".join([
                    self.renderer.tablecell(
                        self.parse_inline(cell.tokens) if cell.tokens else cell.text or "",
                        header=True,
                        align=cell.align
                    ) for cell in getattr(tok, 'header', [])
                ])
                header_row_html = self.renderer.tablerow(header_cells_html)

                # Body Rows
                body_rows_html = ""
                for row in getattr(tok, 'rows', []):
                    row_cells_html = "".join([
                        self.renderer.tablecell(
                            self.parse_inline(cell.tokens) if cell.tokens else cell.text or "",
                            header=False,
                            align=cell.align
                        ) for cell in row
                    ])
                    body_rows_html += self.renderer.tablerow(row_cells_html)

                out.append(self.renderer.table(header_row_html, body_rows_html))

            elif t_type == "text":
                out.append(self.renderer.text(tok.text or "", getattr(tok, 'escaped', False)))
            else:
                # Inline fallbacks
                out.append(self.parse_inline([tok]))

        return "".join(out)

    def parse_list_item(self, tokens: List[Token], loose: bool) -> str:
        out = []
        for tok in tokens:
            if tok.type == "paragraph" and not loose:
                out.append(self.parse_inline(tok.tokens) if tok.tokens else tok.text or "")
            else:
                out.append(self.parse([tok]))
        return "".join(out)

    def parse_inline(self, tokens: List[Token]) -> str:
        out = []
        for tok in tokens:
            t_type = tok.type

            if t_type == "paragraph" or t_type == "text":
                if tok.tokens:
                    out.append(self.parse_inline(tok.tokens))
                else:
                    out.append(self.renderer.text(tok.text or "", getattr(tok, 'escaped', False)))
            elif t_type == "escape":
                out.append(self.renderer.text(tok.text or ""))
            elif t_type == "strong":
                inner = self.parse_inline(tok.tokens) if tok.tokens else tok.text or ""
                out.append(self.renderer.strong(inner))
            elif t_type == "em":
                inner = self.parse_inline(tok.tokens) if tok.tokens else tok.text or ""
                out.append(self.renderer.em(inner))
            elif t_type == "codespan":
                out.append(self.renderer.codespan(tok.text or ""))
            elif t_type == "br":
                out.append(self.renderer.br())
            elif t_type == "del":
                inner = self.parse_inline(tok.tokens) if tok.tokens else tok.text or ""
                out.append(self.renderer.del_element(inner))
            elif t_type == "link":
                inner = self.parse_inline(tok.tokens) if tok.tokens else tok.text or ""
                out.append(self.renderer.link(getattr(tok, 'href', ''), getattr(tok, 'title', None), inner))
            elif t_type == "image":
                out.append(self.renderer.image(getattr(tok, 'href', ''), getattr(tok, 'title', None), tok.text or ""))
            elif t_type == "html":
                out.append(self.renderer.html(tok.text or ""))
            elif t_type == "checkbox":
                out.append(self.renderer.checkbox(getattr(tok, 'checked', False)))
            else:
                out.append(self.renderer.text(tok.text or ""))

        return "".join(out)
