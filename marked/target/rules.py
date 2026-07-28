"""
Regular expression patterns for Markdown parsing (Block & Inline elements).
"""

import re

# Block regexes
RE_NEWLINE = re.compile(r'^(?:[ \t]*(?:\n|$))+')
RE_CODE_INDENT = re.compile(r'^((?:(?: {4}|\t)[^\n]*(?:\n|$)|[ \t]*(?:\n|$))+)')
RE_FENCES = re.compile(r'^ {0,3}(`{3,}(?=[^`\n]*(?:\n|$))|~{3,})([^\n]*)(?:\n|$)(?:|([\s\S]*?)(?:\n|$))(?: {0,3}\1[~`]* *(?=\n|$)|$)')
RE_HR = re.compile(r'^ {0,3}((?:-[\t ]*){3,}|(?:_[ \t]*){3,}|(?:\*[ \t]*){3,})(?:\n+|$)')
RE_HEADING = re.compile(r'^ {0,3}(#{1,6})(?=\s|$)(.*)(?:\n+|$)')
RE_LHEADING = re.compile(r'^([^\n]+)\n {0,3}(=+|-+) *(?:\n+|$)')
RE_BLOCKQUOTE = re.compile(r'^(?: {0,3}>[^\n]*(?:\n|$))+')
RE_LIST_BULLET = re.compile(r'^ {0,3}([*+-]|\d{1,9}[.)])')
RE_LIST_ITEM = re.compile(r'^( {0,3}(?:[*+-]|\d{1,9}[.)]))((?:[ \t][^\n]*)?(?:\n|$))')
RE_DEF = re.compile(r'^ {0,3}\[([^\]]+)\]: *(?:\n[ \t]*)?([^<\s][^\s]*|<.*?>)(?:(?: +(?:\n[ \t]*)?| *\n[ \t]*)(?:"((?:\\"?|[^"\\])*)"|\'([^\'\n]*(?:\n[^\'\n]+)*\n?)\'|\(([^()]*)\)))? *(?:\n+|$)')
RE_TABLE = re.compile(r'^ *([^\n ].*)\n {0,3}((?:\| *)?:?-+:? *(?:\| *:?-+:? *)*(?:\| *)?)(?:\n((?:(?! *\n| {0,3}#{1,6}| {0,3}>| (?: {4}|\t)[^\n]| {0,3}(?:`{3,}|~{3,})| {0,3}(?:[*+-]|\d{1,9}[.)])).*(?:\n|$))*)\n*|$)')

HTML_TAGS = r'address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|meta|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul'
RE_HTML_BLOCK = re.compile(
    r'^ {0,3}(?:'
    r'<(script|pre|style|textarea)[\s>][\s\S]*?(?:</\1>[^\n]*\n+|$)|'
    r'<!--[\s\S]*?(?:-->[^\n]*\n+|$)|'
    r'<\?[\s\S]*?(?:\?>[^\n]*\n+|$)|'
    r'<![A-Z][\s\S]*?(?:>[^\n]*\n+|$)|'
    r'<!\[CDATA\[[\s\S]*?(?:\]\]>[^\n]*\n+|$)|'
    r'</?(?:' + HTML_TAGS + r')(?: +|\n|/?>)[\s\S]*?(?:(?:\n[ \t]*)+\n|$)|'
    r'<(?!script|pre|style|textarea)([a-z][\w-]*)(?: +[a-zA-Z:_][\w.:-]*(?: *= *"[^"\n]*"| *= *\'[^\'\n]*\'| *= *[^\s"\'=<>`]+)?)? */?>(?=[ \t]*(?:\n|$))[\s\S]*?(?:(?:\n[ \t]*)+\n|$)|'
    r'</(?!script|pre|style|textarea)[a-z][\w-]*\s*>(?=[ \t]*(?:\n|$))[\s\S]*?(?:(?:\n[ \t]*)+\n|$)'
    r')', re.IGNORECASE
)

RE_PARAGRAPH = re.compile(r'^([^\n]+(?:\n(?!\s*?\n| {0,3}#{1,6}| {0,3}>| {0,3}(?:`{3,}|~{3,})| {0,3}(?:[*+-]|\d{1,9}[.)])| {0,3}<[^\n>]+>\n)[^\n]+)*)')
RE_TEXT_BLOCK = re.compile(r'^[^\n]+')

# Inline regexes
RE_ESCAPE = re.compile(r'^\\([!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~])')
RE_TAG = re.compile(r'^(?:<!--[\s\S]*?-->|</[a-zA-Z][\w:-]*\s*>|<[a-zA-Z][\w-]*(?:\s+[a-zA-Z:_][\w.:-]*(?:\s*=\s*"[^"]*"|\s*=\s*\'[^\']*\'|\s*=\s*[^\s"\'=<>`]+)?)*\s*/?>|<\?[\s\S]*?\?>|<![a-zA-Z]+\s[\s\S]*?>|<!\[CDATA\[[\s\S]*?\]\]>)')
RE_LINK = re.compile(r'^!?\[((?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?)\]\(\s*(<(?:\\.|[^\n<>\\])+>|[^ \t\n\x00-\x1f]*)(?:[ \t]+(?:"((?:\\"?|[^"\\])*)"|\'((?:\\\'?|[^ ruin\\])*)\'|\(((?:\\\)?|[^)\\])*)\)))?\s*\)')
RE_REFLINK = re.compile(r'^!?\[((?:\[(?:\\[\s\S]|[^\[\]\\])*\]|\\[\s\S]|`+(?!`)[^`]*?`+(?!`)|``+(?=\])|[^\[\]\\`])*?)\]\[((?:(?!\s*\])(?:\\[\s\S]|[^\[\]\\]))+)\]')
RE_NOLINK = re.compile(r'^!?\[((?:(?!\s*\])(?:\\[\s\S]|[^\[\]\\]))+)\](?:\[\])?')
RE_STRONG_EM = re.compile(r'^(?:(\*{1,3}|_{1,3})((?:\\[\s\S]|(?!\1)[\s\S])+?)\1)')
RE_CODESPAN = re.compile(r'^(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)')
RE_BR = re.compile(r'^( {2,}|\\)\n(?!\s*$)')
RE_DEL = re.compile(r'^(~~?)(?=[^\s~])([\s\S]*?[^\s~])\1(?=[^~]|$)')
RE_AUTOLINK = re.compile(r'^<([a-zA-Z][a-zA-Z0-9+.-]{1,31}:[^\s\x00-\x1f<>]*|[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+)>')
RE_URL = re.compile(r'^(?:(https?|ftp):\/\/|www\.)[^\s<]+|^[A-Za-z0-9._+-]+@[a-zA-Z0-9-_]+(?:\.[a-zA-Z0-9-_]*[a-zA-Z0-9])+(?![-_])')
RE_INLINE_TEXT = re.compile(r'^([`~]+|[^`~])(?:(?= {2,}\n)|[\s\S]*?(?:(?=[\\[<!\[`*~_]|https?://|ftp://|www\.)|[^ ](?= {2,}\n)))')
