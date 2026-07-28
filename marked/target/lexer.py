"""
Lexer module for tokenizing Markdown text into AST Nodes.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from tokens import (
    Token, SpaceToken, HeadingToken, CodeToken, BlockquoteToken,
    ListItemToken, ListToken, TableCellToken, TableRowToken, TableToken,
    HrToken, HtmlToken, DefToken, ParagraphToken, TextToken, EscapeToken,
    LinkToken, ImageToken, StrongToken, EmToken, CodespanToken, BrToken,
    DelToken, CheckboxToken
)
import rules


def strip_blank_end_lines(text: str) -> str:
    """Trim trailing blank lines from block match (matches marked's ee() function)."""
    lines = text.split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


class LexerState:
    def __init__(self):
        self.in_link = False
        self.in_raw_block = False
        self.top = True


class MarkdownLexer:
    def __init__(self):
        self.tokens: List[Token] = []
        self.links: Dict[str, Dict[str, Optional[str]]] = {}
        self.state = LexerState()

    def lex(self, src: str) -> List[Token]:
        # Normalize carriage returns
        src = src.replace("\r\n", "\n").replace("\r", "\n")
        self.tokens = []
        self.links = {}

        # First pass: collect link reference definitions
        src = self._precollect_defs(src)

        # Main block tokenization pass
        self.block_tokens(src, self.tokens)

        # Second pass: inline tokenization on text nodes
        self._expand_inline_tokens(self.tokens)

        return self.tokens

    def _precollect_defs(self, src: str) -> str:
        """Scan and remove [link id]: href "title" definitions from source."""
        lines = src.split("\n")
        rem_lines = []
        for line in lines:
            m = rules.RE_DEF.match(line + "\n")
            if m:
                tag = m.group(1).lower()
                href = m.group(2)
                title = m.group(3) or m.group(4) or m.group(5)
                if href.startswith("<") and href.endswith(">"):
                    href = href[1:-1]
                if tag not in self.links:
                    self.links[tag] = {"href": href, "title": title}
            else:
                rem_lines.append(line)
        return "\n".join(rem_lines)

    def block_tokens(self, src: str, target_list: List[Token]) -> None:
        while src:
            # 1. Newline / Space
            m = rules.RE_NEWLINE.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                target_list.append(SpaceToken(raw=matched))
                continue

            # 2. Fenced Code Block
            m = rules.RE_FENCES.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                lang = m.group(2).strip() if m.group(2) else None
                code_text = m.group(3) if m.group(3) is not None else ""
                target_list.append(CodeToken(raw=matched, text=code_text, lang=lang, code_block_style="fenced"))
                continue

            # 3. Indented Code Block
            m = rules.RE_CODE_INDENT.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                code_text = re.sub(r'^(?: {1,4}|\t)', '', matched, flags=re.MULTILINE)
                target_list.append(CodeToken(raw=matched, text=code_text, code_block_style="indented"))
                continue

            # 4. Heading (ATX)
            m = rules.RE_HEADING.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                depth = len(m.group(1))
                heading_text = m.group(2).strip()
                # Strip trailing hashes if present
                if heading_text.endswith("#"):
                    heading_text = heading_text.rstrip("#").strip()
                tok = HeadingToken(raw=matched, depth=depth, text=heading_text)
                tok.tokens = self.inline_tokens(heading_text)
                target_list.append(tok)
                continue

            # 5. Setext Heading
            m = rules.RE_LHEADING.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                heading_text = m.group(1).strip()
                depth = 1 if m.group(2).startswith("=") else 2
                tok = HeadingToken(raw=matched, depth=depth, text=heading_text)
                tok.tokens = self.inline_tokens(heading_text)
                target_list.append(tok)
                continue

            # 6. Horizontal Rule
            m = rules.RE_HR.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                target_list.append(HrToken(raw=matched))
                continue

            # 7. Blockquote
            m = rules.RE_BLOCKQUOTE.match(src)
            if m:
                matched = m.group(0)
                rem_src = src[len(matched):]
                cont_lines = []
                lines = rem_src.split("\n")
                for line in lines:
                    if not line.strip() or re.match(r'^ {0,3}(?:>|#{1,6}|`{3,}|~{3,}|[*+-]|\d{1,9}[.)])', line):
                        break
                    cont_lines.append(line)
                if cont_lines:
                    cont_str = "\n".join(cont_lines) + "\n"
                    matched += cont_str
                    rem_src = rem_src[len(cont_str):]
                src = rem_src

                lines = matched.split("\n")
                cleaned_lines = []
                for line in lines:
                    if re.match(r'^ {0,3}>[ \t]?', line):
                        cleaned_lines.append(re.sub(r'^ {0,3}>[ \t]?', '', line))
                    else:
                        cleaned_lines.append(line)
                inner_text = "\n".join(cleaned_lines)
                tok = BlockquoteToken(raw=matched, text=inner_text)
                tok.tokens = []
                self.block_tokens(inner_text, tok.tokens)
                target_list.append(tok)
                continue

            # 8. List
            m = rules.RE_LIST_BULLET.match(src)
            if m:
                list_tok, remaining_src = self._parse_list(src)
                if list_tok:
                    target_list.append(list_tok)
                    src = remaining_src
                    continue

            # 9. HTML Block
            m = rules.RE_HTML_BLOCK.match(src)
            if m:
                matched = m.group(0)
                cleaned = strip_blank_end_lines(matched)
                src = src[len(matched):]
                target_list.append(HtmlToken(raw=cleaned, text=cleaned, block=True))
                continue

            # 10. Table
            m = rules.RE_TABLE.match(src)
            if m:
                table_tok = self._parse_table(m)
                if table_tok:
                    src = src[len(m.group(0)):]
                    target_list.append(table_tok)
                    continue

            # 11. Paragraph
            m = rules.RE_PARAGRAPH.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                text_content = matched.strip()
                tok = ParagraphToken(raw=matched, text=text_content)
                tok.tokens = self.inline_tokens(text_content)
                target_list.append(tok)
                continue

            # Fallback text
            m = rules.RE_TEXT_BLOCK.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                tok = ParagraphToken(raw=matched, text=matched)
                tok.tokens = self.inline_tokens(matched)
                target_list.append(tok)
                continue

            # Guard against infinite loops
            break

    def _parse_list(self, src: str) -> Tuple[Optional[ListToken], str]:
        items: List[ListItemToken] = []
        raw_list = ""
        first_bullet_m = rules.RE_LIST_BULLET.match(src)
        if not first_bullet_m:
            return None, src

        bullet = first_bullet_m.group(1)
        ordered = bullet[-1] in ".)"
        start_val = int(bullet[:-1]) if ordered and bullet[:-1].isdigit() else ""

        rem_src = src
        while rem_src:
            m = rules.RE_LIST_ITEM.match(rem_src)
            if not m:
                break

            bullet_str = m.group(1)
            matched_item = m.group(0)
            rem_src = rem_src[len(matched_item):]

            item_raw = matched_item
            item_text = m.group(2)
            indent_len = len(bullet_str)

            # Consume continuation lines indented under this list item
            lines = rem_src.split("\n")
            consumed_count = 0
            for line in lines:
                if not line.strip():
                    item_text += "\n"
                    item_raw += line + "\n"
                    consumed_count += 1
                    continue
                line_indent = len(line) - len(line.lstrip(" "))
                if line_indent >= 2:  # Indented continuation line or nested list
                    item_text += "\n" + line[min(line_indent, indent_len):]
                    item_raw += line + "\n"
                    consumed_count += 1
                else:
                    break

            if consumed_count > 0:
                rem_src = "\n".join(lines[consumed_count:])

            item_text_clean = item_text.strip()
            item_tok = ListItemToken(raw=item_raw, text=item_text_clean)
            # Check task list
            if item_text_clean.startswith("[ ] "):
                item_tok.task = True
                item_tok.checked = False
                item_text_clean = item_text_clean[4:]
                item_tok.tokens = [CheckboxToken(raw="[ ] ", checked=False)]
                self.block_tokens(item_text_clean, item_tok.tokens)
            elif item_text_clean.startswith("[x] ") or item_text_clean.startswith("[X] "):
                item_tok.task = True
                item_tok.checked = True
                prefix = item_text_clean[:4]
                item_text_clean = item_text_clean[4:]
                item_tok.tokens = [CheckboxToken(raw=prefix, checked=True)]
                self.block_tokens(item_text_clean, item_tok.tokens)
            else:
                item_tok.tokens = []
                self.block_tokens(item_text_clean, item_tok.tokens)

            item_tok.text = item_text_clean
            items.append(item_tok)
            raw_list += item_raw

        if not items:
            return None, src

        list_tok = ListToken(
            raw=raw_list,
            ordered=ordered,
            start=start_val if start_val != 1 else "",
            items=items
        )
        return list_tok, rem_src

    def _parse_table(self, match: re.Match) -> Optional[TableToken]:
        header_raw = match.group(1)
        align_raw = match.group(2)
        rows_raw = match.group(3)

        headers = [h.strip() for h in header_raw.split("|") if h.strip()]
        align_cols = [a.strip() for a in align_raw.split("|") if a.strip()]

        alignments = []
        for col in align_cols:
            if col.startswith(":") and col.endswith(":"):
                alignments.append("center")
            elif col.endswith(":"):
                alignments.append("right")
            elif col.startswith(":"):
                alignments.append("left")
            else:
                alignments.append(None)

        header_cells = [
            TableCellToken(
                raw=h,
                text=h,
                header=True,
                align=alignments[i] if i < len(alignments) else None,
                tokens=self.inline_tokens(h)
            ) for i, h in enumerate(headers)
        ]

        row_tokens = []
        if rows_raw:
            for row_line in rows_raw.strip().split("\n"):
                if not row_line.strip():
                    continue
                cells = [c.strip() for c in row_line.split("|") if c.strip()]
                row_cells = [
                    TableCellToken(
                        raw=c,
                        text=c,
                        header=False,
                        align=alignments[i] if i < len(alignments) else None,
                        tokens=self.inline_tokens(c)
                    ) for i, c in enumerate(cells)
                ]
                row_tokens.append(row_cells)

        return TableToken(
            raw=match.group(0),
            header=header_cells,
            align=alignments,
            rows=row_tokens
        )

    def inline_tokens(self, src: str) -> List[Token]:
        tokens: List[Token] = []
        while src:
            # 1. Escape
            m = rules.RE_ESCAPE.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                tokens.append(EscapeToken(raw=matched, text=m.group(1)))
                continue

            # 2. Codespan
            m = rules.RE_CODESPAN.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                code_text = m.group(2).replace("\n", " ")
                tokens.append(CodespanToken(raw=matched, text=code_text))
                continue

            # 3. Strong / Emphasis
            m = rules.RE_STRONG_EM.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                delim = m.group(1)
                inner_text = m.group(2)
                if len(delim) == 3:
                    strong_tok = StrongToken(raw=matched, text=inner_text)
                    strong_tok.tokens = self.inline_tokens(inner_text)
                    tok = EmToken(raw=matched, text=inner_text)
                    tok.tokens = [strong_tok]
                elif len(delim) == 2:
                    tok = StrongToken(raw=matched, text=inner_text)
                    tok.tokens = self.inline_tokens(inner_text)
                else:
                    tok = EmToken(raw=matched, text=inner_text)
                    tok.tokens = self.inline_tokens(inner_text)
                tokens.append(tok)
                continue

            # 4. Strikethrough (Del)
            m = rules.RE_DEL.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                inner_text = m.group(2)
                tok = DelToken(raw=matched, text=inner_text)
                tok.tokens = self.inline_tokens(inner_text)
                tokens.append(tok)
                continue

            # 5. Direct Link / Image
            m = rules.RE_LINK.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                is_image = matched.startswith("!")
                link_text = m.group(1)
                href = m.group(2)
                title = m.group(3) or m.group(4) or m.group(5)

                if is_image:
                    tokens.append(ImageToken(raw=matched, text=link_text, href=href, title=title))
                else:
                    tok = LinkToken(raw=matched, text=link_text, href=href, title=title)
                    tok.tokens = self.inline_tokens(link_text)
                    tokens.append(tok)
                continue

            # 6. Reference Link
            m = rules.RE_REFLINK.match(src) or rules.RE_NOLINK.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                link_text = m.group(1)
                ref_tag = (m.group(2) if len(m.groups()) >= 2 and m.group(2) else link_text).lower()

                if ref_tag in self.links:
                    ref_data = self.links[ref_tag]
                    tok = LinkToken(raw=matched, text=link_text, href=ref_data["href"], title=ref_data["title"])
                    tok.tokens = self.inline_tokens(link_text)
                    tokens.append(tok)
                else:
                    tokens.append(TextToken(raw=matched, text=matched))
                continue

            # 7. Autolink
            m = rules.RE_AUTOLINK.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                url = m.group(1)
                href = f"mailto:{url}" if "@" in url and not url.startswith("http") else url
                tokens.append(LinkToken(raw=matched, text=url, href=href))
                continue

            # 8. HTML Tag
            m = rules.RE_TAG.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                tokens.append(HtmlToken(raw=matched, text=matched, block=False))
                continue

            # 9. Line Break
            m = rules.RE_BR.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                tokens.append(BrToken(raw=matched))
                continue

            # 10. Plain text fallback
            m = rules.RE_INLINE_TEXT.match(src)
            if m:
                matched = m.group(0)
                src = src[len(matched):]
                tokens.append(TextToken(raw=matched, text=matched))
                continue

            # Single character fallback
            ch = src[0]
            src = src[1:]
            tokens.append(TextToken(raw=ch, text=ch))

        return tokens

    def _expand_inline_tokens(self, tokens_list: List[Token]) -> None:
        """Recursively process tokens list to ensure inline elements are expanded."""
        for tok in tokens_list:
            if tok.tokens:
                self._expand_inline_tokens(tok.tokens)
            if hasattr(tok, 'items') and tok.items:
                for item in tok.items:
                    if item.tokens:
                        self._expand_inline_tokens(item.tokens)
