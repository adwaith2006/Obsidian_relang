"""
Token definitions for the marked Python Markdown parser.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Token:
    type: str = ""
    raw: str = ""
    text: Optional[str] = None
    tokens: List['Token'] = field(default_factory=list)


@dataclass
class SpaceToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "space"


@dataclass
class HeadingToken(Token):
    depth: int = 1

    def __post_init__(self):
        if not self.type:
            self.type = "heading"


@dataclass
class CodeToken(Token):
    lang: Optional[str] = None
    code_block_style: str = "indented"
    escaped: bool = False

    def __post_init__(self):
        if not self.type:
            self.type = "code"


@dataclass
class BlockquoteToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "blockquote"


@dataclass
class ListItemToken(Token):
    task: bool = False
    checked: Optional[bool] = None
    loose: bool = False

    def __post_init__(self):
        if not self.type:
            self.type = "list_item"


@dataclass
class ListToken(Token):
    ordered: bool = False
    start: Any = ""
    loose: bool = False
    items: List[ListItemToken] = field(default_factory=list)

    def __post_init__(self):
        if not self.type:
            self.type = "list"


@dataclass
class TableCellToken(Token):
    header: bool = False
    align: Optional[str] = None

    def __post_init__(self):
        if not self.type:
            self.type = "tablecell"


@dataclass
class TableRowToken(Token):
    cells: List[TableCellToken] = field(default_factory=list)

    def __post_init__(self):
        if not self.type:
            self.type = "tablerow"


@dataclass
class TableToken(Token):
    header: List[TableCellToken] = field(default_factory=list)
    align: List[Optional[str]] = field(default_factory=list)
    rows: List[List[TableCellToken]] = field(default_factory=list)

    def __post_init__(self):
        if not self.type:
            self.type = "table"


@dataclass
class HrToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "hr"


@dataclass
class HtmlToken(Token):
    block: bool = True
    pre: bool = False
    in_link: bool = False
    in_raw_block: bool = False

    def __post_init__(self):
        if not self.type:
            self.type = "html"


@dataclass
class DefToken(Token):
    tag: str = ""
    href: str = ""
    title: Optional[str] = None

    def __post_init__(self):
        if not self.type:
            self.type = "def"


@dataclass
class ParagraphToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "paragraph"


@dataclass
class TextToken(Token):
    escaped: bool = False

    def __post_init__(self):
        if not self.type:
            self.type = "text"


@dataclass
class EscapeToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "escape"


@dataclass
class LinkToken(Token):
    href: str = ""
    title: Optional[str] = None

    def __post_init__(self):
        if not self.type:
            self.type = "link"


@dataclass
class ImageToken(Token):
    href: str = ""
    title: Optional[str] = None

    def __post_init__(self):
        if not self.type:
            self.type = "image"


@dataclass
class StrongToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "strong"


@dataclass
class EmToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "em"


@dataclass
class CodespanToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "codespan"


@dataclass
class BrToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "br"


@dataclass
class DelToken(Token):
    def __post_init__(self):
        if not self.type:
            self.type = "del"


@dataclass
class CheckboxToken(Token):
    checked: bool = False

    def __post_init__(self):
        if not self.type:
            self.type = "checkbox"

