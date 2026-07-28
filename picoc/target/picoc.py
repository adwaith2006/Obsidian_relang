#!/usr/bin/env python3
"""
picoc - C interpreter in Python 3.
Ported from reference C picoc interpreter.
"""

import sys
import os
import re
import struct
import math
import tempfile

# -----------------------------------------------------------------------------
# Memory Subsystem (Simulated Byte-Addressable Memory)
# -----------------------------------------------------------------------------

class Memory:
    def __init__(self, size=32 * 1024 * 1024):
        self.data = bytearray(size)
        self.string_ptr = 0x1000    # Read-only string literals region
        self.heap_start = 0x100000  # Heap/stack variables start at 1MB
        self.heap_ptr = self.heap_start
        self.allocations = {}
        self.free_blocks = []

    def alloc_string(self, s):
        addr = self.string_ptr
        b_data = s.encode('latin1') + b'\x00'
        self.write_bytes(addr, b_data)
        self.string_ptr += (len(b_data) + 7) & ~7
        return addr

    def malloc(self, size):
        if size <= 0:
            size = 1
        size = (size + 7) & ~7
        for i, (ptr, block_size) in enumerate(self.free_blocks):
            if block_size >= size:
                self.free_blocks.pop(i)
                if block_size > size:
                    self.free_blocks.append((ptr + size, block_size - size))
                self.allocations[ptr] = size
                return ptr

        ptr = self.heap_ptr
        self.heap_ptr += size
        if self.heap_ptr >= len(self.data):
            self.data.extend(bytearray(size + 1024 * 1024))
        self.allocations[ptr] = size
        return ptr

    def calloc(self, num, size):
        total = num * size
        ptr = self.malloc(total)
        self.data[ptr:ptr + total] = b'\x00' * total
        return ptr

    def realloc(self, old_ptr, size):
        if old_ptr == 0:
            return self.malloc(size)
        if size <= 0:
            self.free(old_ptr)
            return 0
        old_size = self.allocations.get(old_ptr, 0)
        new_ptr = self.malloc(size)
        copy_size = min(old_size, size)
        if copy_size > 0:
            self.data[new_ptr:new_ptr + copy_size] = self.data[old_ptr:old_ptr + copy_size]
        self.free(old_ptr)
        return new_ptr

    def free(self, ptr):
        if ptr in self.allocations:
            size = self.allocations.pop(ptr)
            self.free_blocks.append((ptr, size))

    def read_bytes(self, addr, size):
        return bytes(self.data[addr:addr + size])

    def write_bytes(self, addr, b_data):
        self.data[addr:addr + len(b_data)] = b_data

    def read_int(self, addr, size, signed=True):
        raw = self.data[addr:addr + size]
        return int.from_bytes(raw, byteorder='little', signed=signed)

    def write_int(self, addr, size, val, signed=True):
        val = int(val)
        mask = (1 << (size * 8)) - 1
        val = val & mask
        b_data = val.to_bytes(size, byteorder='little', signed=False)
        self.data[addr:addr + size] = b_data

    def read_float(self, addr, size):
        raw = self.data[addr:addr + size]
        if size == 4:
            return struct.unpack('<f', raw)[0]
        elif size == 8:
            return struct.unpack('<d', raw)[0]
        return 0.0

    def write_float(self, addr, size, val):
        if size == 4:
            b_data = struct.pack('<f', float(val))
        else:
            b_data = struct.pack('<d', float(val))
        self.data[addr:addr + size] = b_data

    def read_string(self, addr, max_len=4096):
        end = addr
        while end < len(self.data) and self.data[end] != 0 and (end - addr) < max_len:
            end += 1
        return self.data[addr:end].decode('latin1', errors='replace')

    def write_string(self, addr, s):
        b_data = s.encode('latin1') + b'\x00'
        self.write_bytes(addr, b_data)
        return len(b_data)

mem = Memory()

# -----------------------------------------------------------------------------
# Type System
# -----------------------------------------------------------------------------

TYPE_VOID = 'void'
TYPE_CHAR = 'char'
TYPE_UCHAR = 'unsigned char'
TYPE_SHORT = 'short'
TYPE_USHORT = 'unsigned short'
TYPE_INT = 'int'
TYPE_UINT = 'unsigned int'
TYPE_LONG = 'long'
TYPE_ULONG = 'unsigned long'
TYPE_FLOAT = 'float'
TYPE_DOUBLE = 'double'

class CType:
    def __init__(self, kind, target_type=None, size=4, fields=None, name=None, array_size=None, is_unsigned=False, align=1):
        self.kind = kind
        self.target_type = target_type
        self.size = size
        self.fields = fields or {}
        self.name = name
        self.array_size = array_size
        self.is_unsigned = is_unsigned
        self.align = align

    def is_pointer(self):
        return self.kind == 'POINTER'

    def is_array(self):
        return self.kind == 'ARRAY'

    def is_struct(self):
        return self.kind == 'STRUCT'

    def is_union(self):
        return self.kind == 'UNION'

    def is_numeric(self):
        return self.kind in (TYPE_CHAR, TYPE_UCHAR, TYPE_SHORT, TYPE_USHORT, TYPE_INT, TYPE_UINT, TYPE_LONG, TYPE_ULONG, TYPE_FLOAT, TYPE_DOUBLE)

    def is_fp(self):
        return self.kind in (TYPE_FLOAT, TYPE_DOUBLE)

    def is_int(self):
        return self.is_numeric() and not self.is_fp()

    def __repr__(self):
        if self.kind == 'POINTER':
            return f"{self.target_type}*"
        elif self.kind == 'ARRAY':
            return f"{self.target_type}[{self.array_size}]"
        elif self.kind in ('STRUCT', 'UNION'):
            return f"{self.kind} {self.name}"
        return self.kind

CTYPE_VOID = CType(TYPE_VOID, size=0, align=1)
CTYPE_CHAR = CType(TYPE_CHAR, size=1, align=1)
CTYPE_UCHAR = CType(TYPE_UCHAR, size=1, is_unsigned=True, align=1)
CTYPE_SHORT = CType(TYPE_SHORT, size=2, align=2)
CTYPE_USHORT = CType(TYPE_USHORT, size=2, is_unsigned=True, align=2)
CTYPE_INT = CType(TYPE_INT, size=4, align=4)
CTYPE_UINT = CType(TYPE_UINT, size=4, is_unsigned=True, align=4)
CTYPE_LONG = CType(TYPE_LONG, size=8, align=8)
CTYPE_ULONG = CType(TYPE_ULONG, size=8, is_unsigned=True, align=8)
CTYPE_FLOAT = CType(TYPE_FLOAT, size=4, align=4)
CTYPE_DOUBLE = CType(TYPE_DOUBLE, size=8, align=8)
CTYPE_VOID_PTR = CType('POINTER', target_type=CTYPE_VOID, size=8, align=8)
CTYPE_CHAR_PTR = CType('POINTER', target_type=CTYPE_CHAR, size=8, align=8)

# -----------------------------------------------------------------------------
# Value Representation
# -----------------------------------------------------------------------------

class Value:
    def __init__(self, ctype, val, addr=None, is_lvalue=False):
        self.ctype = ctype
        self.val = val
        self.addr = addr
        self.is_lvalue = is_lvalue

    def get_val(self):
        if self.ctype.is_array():
            return self.addr

        if self.is_lvalue and self.addr is not None:
            if self.ctype.is_pointer():
                return mem.read_int(self.addr, self.ctype.size, signed=False)
            elif self.ctype.is_struct() or self.ctype.is_union():
                return self.addr
            elif self.ctype.is_fp():
                return mem.read_float(self.addr, self.ctype.size)
            elif self.ctype.is_int():
                return mem.read_int(self.addr, self.ctype.size, signed=not self.ctype.is_unsigned)
        return self.val

    def set_val(self, new_val):
        coerced = coerce_value(self.ctype, new_val)
        if self.is_lvalue and self.addr is not None:
            if self.ctype.is_pointer():
                mem.write_int(self.addr, self.ctype.size, int(coerced), signed=False)
            elif self.ctype.is_fp():
                mem.write_float(self.addr, self.ctype.size, float(coerced))
            elif self.ctype.is_int():
                mem.write_int(self.addr, self.ctype.size, int(coerced), signed=not self.ctype.is_unsigned)
            elif self.ctype.is_struct() or self.ctype.is_union():
                if isinstance(coerced, int):
                    mem.write_bytes(self.addr, mem.read_bytes(coerced, self.ctype.size))
        self.val = coerced

def coerce_value(target_type, val):
    if val is None:
        return 0
    if isinstance(val, Value):
        val = val.get_val()

    if target_type.is_pointer():
        return int(val)
    elif target_type.is_fp():
        return float(val)
    elif target_type.is_int():
        ival = int(val)
        if target_type.size == 1:
            ival = ival & 0xFF
            if not target_type.is_unsigned and (ival & 0x80):
                ival -= 256
        elif target_type.size == 2:
            ival = ival & 0xFFFF
            if not target_type.is_unsigned and (ival & 0x8000):
                ival -= 65536
        elif target_type.size == 4:
            ival = ival & 0xFFFFFFFF
            if not target_type.is_unsigned and (ival & 0x80000000):
                ival -= 4294967296
        return ival
    return val

# -----------------------------------------------------------------------------
# Lexer & Preprocessor
# -----------------------------------------------------------------------------

TOKEN_IDENT = 'IDENT'
TOKEN_NUMBER = 'NUMBER'
TOKEN_FLOAT = 'FLOAT'
TOKEN_STRING = 'STRING'
TOKEN_CHAR = 'CHAR'
TOKEN_KEYWORD = 'KEYWORD'
TOKEN_OPERATOR = 'OPERATOR'
TOKEN_PUNCT = 'PUNCT'
TOKEN_EOF = 'EOF'

KEYWORDS = {
    'int', 'char', 'short', 'long', 'float', 'double', 'void',
    'struct', 'union', 'enum', 'typedef', 'if', 'else', 'while', 'do',
    'for', 'switch', 'case', 'default', 'break', 'continue', 'return',
    'goto', 'static', 'sizeof', 'unsigned', 'signed', 'extern', 'const',
    'volatile', 'auto', 'register', 'inline'
}

OPERATORS = [
    '>>=', '<<=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=',
    '==', '!=', '<=', '>=', '&&', '||', '++', '--', '->', '<<', '>>',
    '+', '-', '*', '/', '%', '=', '<', '>', '!', '&', '|', '^', '~', '?', ':'
]

class Token:
    def __init__(self, kind, val, line=1, col=1):
        self.kind = kind
        self.val = val
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.kind}, {repr(self.val)})"

def replace_macros_in_line(line, defines):
    if not defines:
        return line

    def token_replacer(match):
        s = match.group(0)
        if s.startswith('"') or s.startswith("'"):
            return s
        for d_name, d_val in defines.items():
            s = re.sub(r'\b' + re.escape(d_name) + r'\b', d_val, s)
        return s

    pattern = re.compile(r'"(?:\\.|[^\\"])*"|\'(?:\\.|[^\\\'])*\'|[a-zA-Z_]\w*')
    return pattern.sub(token_replacer, line)

def preprocess_code(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return ' '
        else:
            return s
    pattern = re.compile(r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL | re.MULTILINE)
    text = re.sub(pattern, replacer, text)

    lines = text.split('\n')
    out_lines = []
    defines = {'__PICOC__': '1'}
    if_stack = [True]

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            parts = stripped.split(None, 2)
            cmd = parts[0]
            if cmd == '#define' and len(parts) >= 2:
                name = parts[1]
                val = parts[2] if len(parts) > 2 else '1'
                if all(if_stack):
                    defines[name] = val
            elif cmd == '#ifdef' and len(parts) >= 2:
                cond = parts[1] in defines
                if_stack.append(all(if_stack) and cond)
            elif cmd == '#ifndef' and len(parts) >= 2:
                cond = parts[1] not in defines
                if_stack.append(all(if_stack) and cond)
            elif cmd == '#if' and len(parts) >= 2:
                cond_expr = parts[1]
                for d_name, d_val in defines.items():
                    cond_expr = re.sub(r'\b' + re.escape(d_name) + r'\b', d_val, cond_expr)
                cond_expr = cond_expr.strip()
                cond = (cond_expr not in ('0', ''))
                if_stack.append(all(if_stack) and cond)
            elif cmd == '#else':
                if len(if_stack) > 1:
                    parent_state = if_stack[-2]
                    if_stack[-1] = parent_state and not if_stack[-1]
            elif cmd == '#endif':
                if len(if_stack) > 1:
                    if_stack.pop()
            out_lines.append('')
        else:
            if all(if_stack):
                line = replace_macros_in_line(line, defines)
                out_lines.append(line)
            else:
                out_lines.append('')

    return '\n'.join(out_lines)

def tokenize(text):
    tokens = []
    i = 0
    length = len(text)
    line = 1
    col = 1

    while i < length:
        ch = text[i]

        if ch == '\n':
            line += 1
            col = 1
            i += 1
            continue
        elif ch.isspace():
            i += 1
            col += 1
            continue

        if ch.isdigit() or (ch == '.' and i + 1 < length and text[i + 1].isdigit()):
            start = i
            is_float = False
            if text[i:i+2].lower() in ('0x', '0b'):
                i += 2
                while i < length and (text[i].isalnum()):
                    i += 1
            else:
                while i < length and (text[i].isdigit() or text[i] in '.eE+-'):
                    if text[i] in '.eE':
                        is_float = True
                    if text[i] in '+-' and i > start and text[i-1] not in 'eE':
                        break
                    i += 1

            while i < length and text[i].isalpha():
                if text[i].lower() in ('f', 'l', 'u'):
                    is_float = is_float or text[i].lower() == 'f'
                i += 1

            num_str = text[start:i]
            num_clean = re.sub(r'[fFlLuU]+$', '', num_str)
            if is_float:
                val = float(num_clean)
                tokens.append(Token(TOKEN_FLOAT, val, line, col))
            else:
                if num_clean.lower().startswith('0x'):
                    val = int(num_clean, 16)
                elif num_clean.startswith('0') and len(num_clean) > 1 and num_clean[1].isdigit():
                    val = int(num_clean, 8)
                else:
                    val = int(num_clean, 10)
                tokens.append(Token(TOKEN_NUMBER, val, line, col))
            col += (i - start)
            continue

        if ch.isalpha() or ch == '_':
            start = i
            while i < length and (text[i].isalnum() or text[i] == '_'):
                i += 1
            word = text[start:i]
            if word in KEYWORDS:
                tokens.append(Token(TOKEN_KEYWORD, word, line, col))
            else:
                tokens.append(Token(TOKEN_IDENT, word, line, col))
            col += (i - start)
            continue

        if ch == '"':
            i += 1
            start = i
            s_chars = []
            while i < length and text[i] != '"':
                if text[i] == '\\' and i + 1 < length:
                    i += 1
                    ec = text[i]
                    if ec == 'n': s_chars.append('\n')
                    elif ec == 't': s_chars.append('\t')
                    elif ec == 'r': s_chars.append('\r')
                    elif ec == '0': s_chars.append('\0')
                    elif ec == '"': s_chars.append('"')
                    elif ec == '\\': s_chars.append('\\')
                    else: s_chars.append(ec)
                else:
                    s_chars.append(text[i])
                i += 1
            if i < length:
                i += 1
            tokens.append(Token(TOKEN_STRING, "".join(s_chars), line, col))
            col += (i - start)
            continue

        if ch == "'":
            i += 1
            c_val = 0
            if text[i] == '\\' and i + 1 < length:
                i += 1
                ec = text[i]
                if ec == 'n': c_val = ord('\n')
                elif ec == 't': c_val = ord('\t')
                elif ec == 'r': c_val = ord('\r')
                elif ec == '0': c_val = 0
                elif ec == '\'': c_val = ord('\'')
                elif ec == '\\': c_val = ord('\\')
                else: c_val = ord(ec)
            else:
                c_val = ord(text[i])
            i += 1
            if i < length and text[i] == "'":
                i += 1
            tokens.append(Token(TOKEN_CHAR, c_val, line, col))
            continue

        matched_op = None
        for op in OPERATORS:
            if text.startswith(op, i):
                matched_op = op
                break
        if matched_op:
            tokens.append(Token(TOKEN_OPERATOR, matched_op, line, col))
            i += len(matched_op)
            col += len(matched_op)
            continue

        tokens.append(Token(TOKEN_PUNCT, ch, line, col))
        i += 1
        col += 1

    tokens.append(Token(TOKEN_EOF, 'EOF', line, col))
    return tokens

# -----------------------------------------------------------------------------
# Environment & Scopes
# -----------------------------------------------------------------------------

class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.vars = {}
        self.types = {}
        self.structs = {}
        self.functions = {}

    def get_var(self, name):
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.get_var(name)
        return None

    def set_var(self, name, val):
        if name in self.vars:
            self.vars[name].set_val(val)
            return True
        if self.parent:
            return self.parent.set_var(name, val)
        return False

    def define_var(self, name, value_obj):
        self.vars[name] = value_obj

    def get_type(self, name):
        if name in self.types:
            return self.types[name]
        if self.parent:
            return self.parent.get_type(name)
        return None

    def define_type(self, name, ctype):
        self.types[name] = ctype

    def get_struct(self, name):
        if name in self.structs:
            return self.structs[name]
        if self.parent:
            return self.parent.get_struct(name)
        return None

    def define_struct(self, name, ctype):
        self.structs[name] = ctype

    def get_func(self, name):
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.get_func(name)
        return None

    def define_func(self, name, node):
        self.functions[name] = node

# -----------------------------------------------------------------------------
# Exceptions
# -----------------------------------------------------------------------------

class ReturnException(Exception):
    def __init__(self, value):
        self.value = value

class BreakException(Exception): pass
class ContinueException(Exception): pass

class GotoException(Exception):
    def __init__(self, label):
        self.label = label

# -----------------------------------------------------------------------------
# AST Nodes
# -----------------------------------------------------------------------------

class ASTNode: pass

class ASTProgram(ASTNode):
    def __init__(self, decls): self.decls = decls

class ASTVarDecl(ASTNode):
    def __init__(self, ctype, name, init_expr=None, is_static=False):
        self.ctype = ctype
        self.name = name
        self.init_expr = init_expr
        self.is_static = is_static

class ASTFuncDef(ASTNode):
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body

class ASTBlock(ASTNode):
    def __init__(self, stmts): self.stmts = stmts

class ASTIf(ASTNode):
    def __init__(self, cond, then_branch, else_branch=None):
        self.cond = cond
        self.then_branch = then_branch
        self.else_branch = else_branch

class ASTWhile(ASTNode):
    def __init__(self, cond, body, is_do_while=False):
        self.cond = cond
        self.body = body
        self.is_do_while = is_do_while

class ASTFor(ASTNode):
    def __init__(self, init, cond, incr, body):
        self.init = init
        self.cond = cond
        self.incr = incr
        self.body = body

class ASTSwitch(ASTNode):
    def __init__(self, expr, body):
        self.expr = expr
        self.body = body

class ASTCase(ASTNode):
    def __init__(self, expr): self.expr = expr

class ASTDefault(ASTNode): pass
class ASTBreak(ASTNode): pass
class ASTContinue(ASTNode): pass

class ASTReturn(ASTNode):
    def __init__(self, expr=None): self.expr = expr

class ASTGoto(ASTNode):
    def __init__(self, label): self.label = label

class ASTLabel(ASTNode):
    def __init__(self, label): self.label = label

class ASTExprStmt(ASTNode):
    def __init__(self, expr): self.expr = expr

class ASTBinaryOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

class ASTUnaryOp(ASTNode):
    def __init__(self, op, operand, is_postfix=False):
        self.op = op
        self.operand = operand
        self.is_postfix = is_postfix

class ASTTernary(ASTNode):
    def __init__(self, cond, then_expr, else_expr):
        self.cond = cond
        self.then_expr = then_expr
        self.else_expr = else_expr

class ASTCast(ASTNode):
    def __init__(self, target_type, expr):
        self.target_type = target_type
        self.expr = expr

class ASTCall(ASTNode):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

class ASTMemberAccess(ASTNode):
    def __init__(self, expr, member_name, is_arrow=False):
        self.expr = expr
        self.member_name = member_name
        self.is_arrow = is_arrow

class ASTArraySubscript(ASTNode):
    def __init__(self, array_expr, index_expr):
        self.array_expr = array_expr
        self.index_expr = index_expr

class ASTVar(ASTNode):
    def __init__(self, name): self.name = name

class ASTLiteral(ASTNode):
    def __init__(self, ctype, val):
        self.ctype = ctype
        self.val = val

class ASTSizeof(ASTNode):
    def __init__(self, target): self.target = target

class ASTInitList(ASTNode):
    def __init__(self, exprs): self.exprs = exprs

def flatten_init_list(node):
    if not isinstance(node, ASTInitList):
        return [node]
    res = []
    for expr in node.exprs:
        res.extend(flatten_init_list(expr))
    return res

# -----------------------------------------------------------------------------
# Parser
# -----------------------------------------------------------------------------

class CParser:
    def __init__(self, tokens, env):
        self.tokens = tokens
        self.pos = 0
        self.env = env

    def peek(self, offset=0):
        if self.pos + offset < len(self.tokens):
            return self.tokens[self.pos + offset]
        return self.tokens[-1]

    def consume(self):
        tok = self.peek()
        self.pos += 1
        return tok

    def match_keyword(self, kw):
        tok = self.peek()
        if tok.kind == TOKEN_KEYWORD and tok.val == kw:
            self.consume()
            return True
        return False

    def match_punct(self, p):
        tok = self.peek()
        if tok.kind == TOKEN_PUNCT and tok.val == p:
            self.consume()
            return True
        return False

    def match_op(self, op):
        tok = self.peek()
        if tok.kind == TOKEN_OPERATOR and tok.val == op:
            self.consume()
            return True
        return False

    def parse_program(self):
        decls = []
        while self.peek().kind != TOKEN_EOF:
            d = self.parse_top_level()
            if d:
                if isinstance(d, list):
                    decls.extend(d)
                else:
                    decls.append(d)
        return ASTProgram(decls)

    def parse_top_level(self):
        tok = self.peek()
        is_static = False
        if tok.kind == TOKEN_KEYWORD and tok.val == 'static':
            is_static = True
            self.consume()
            tok = self.peek()

        if tok.kind == TOKEN_KEYWORD and tok.val == 'typedef':
            self.consume()
            btype = self.parse_type()
            name_tok = self.consume()
            self.env.define_type(name_tok.val, btype)
            self.match_punct(';')
            return None

        btype = self.parse_type()
        if btype is None:
            self.consume()
            return None

        if self.match_punct(';'):
            return None

        name_tok = self.consume()
        name = name_tok.val

        if self.match_punct('('):
            params = []
            if not self.match_punct(')'):
                while True:
                    p_type = self.parse_type()
                    p_name = None
                    if self.peek().kind == TOKEN_IDENT:
                        p_name = self.consume().val
                    params.append((p_type, p_name))
                    if self.match_punct(')'):
                        break
                    self.match_punct(',')

            if self.match_punct(';'):
                return None

            body = self.parse_block()
            fdef = ASTFuncDef(btype, name, params, body)
            self.env.define_func(name, fdef)
            return fdef

        vars_list = []
        while True:
            var_type = btype
            if name.startswith('*'):
                stars = 0
                while name.startswith('*'):
                    stars += 1
                    name = name[1:]
                for _ in range(stars):
                    var_type = CType('POINTER', target_type=var_type, size=8, align=8)

            arr_dims = []
            while self.match_punct('['):
                if not self.match_punct(']'):
                    arr_s = evaluate_const_expr(self.parse_expression())
                    self.match_punct(']')
                    arr_dims.append(arr_s)
                else:
                    arr_dims.append(None)

            init_expr = None
            if self.match_op('='):
                init_expr = self.parse_expression()
                if isinstance(init_expr, ASTInitList):
                    flat_exprs = flatten_init_list(init_expr)
                    init_expr = ASTInitList(flat_exprs)
                    if arr_dims and arr_dims[-1] is None:
                        inner_count = 1
                        for d in arr_dims[:-1]:
                            if d: inner_count *= d
                        arr_dims[-1] = len(flat_exprs) // inner_count

            if arr_dims:
                for dim in reversed(arr_dims):
                    sz = dim if dim is not None else 1
                    var_type = CType('ARRAY', target_type=var_type, size=var_type.size * sz, array_size=sz, align=var_type.align)

            vars_list.append(ASTVarDecl(var_type, name, init_expr, is_static=is_static))
            if self.match_punct(';'):
                break
            if not self.match_punct(','):
                self.match_punct(';')
                break
            name = self.consume().val

        return vars_list

    def parse_type(self):
        tok = self.peek()
        is_unsigned = False
        if tok.kind == TOKEN_KEYWORD and tok.val == 'unsigned':
            is_unsigned = True
            self.consume()
            tok = self.peek()

        if tok.kind == TOKEN_KEYWORD:
            kw = tok.val
            if kw == 'int':
                self.consume()
                btype = CTYPE_UINT if is_unsigned else CTYPE_INT
            elif kw == 'char':
                self.consume()
                btype = CTYPE_UCHAR if is_unsigned else CTYPE_CHAR
            elif kw == 'short':
                self.consume()
                if self.match_keyword('int'): pass
                btype = CTYPE_USHORT if is_unsigned else CTYPE_SHORT
            elif kw == 'long':
                self.consume()
                if self.match_keyword('int'): pass
                btype = CTYPE_ULONG if is_unsigned else CTYPE_LONG
            elif kw == 'float':
                self.consume()
                btype = CTYPE_FLOAT
            elif kw == 'double':
                self.consume()
                btype = CTYPE_DOUBLE
            elif kw == 'void':
                self.consume()
                btype = CTYPE_VOID
            elif kw in ('struct', 'union'):
                kind = kw.upper()
                self.consume()
                s_name = None
                if self.peek().kind == TOKEN_IDENT:
                    s_name = self.consume().val

                fields = {}
                offset = 0
                max_align = 1
                max_field_size = 0
                if self.match_punct('{'):
                    while not self.match_punct('}'):
                        f_type = self.parse_type()
                        f_name = self.consume().val
                        if self.match_punct('['):
                            arr_s = evaluate_const_expr(self.parse_expression())
                            self.match_punct(']')
                            f_type = CType('ARRAY', target_type=f_type, size=f_type.size * arr_s, array_size=arr_s, align=f_type.align)
                        self.match_punct(';')

                        f_align = f_type.align if hasattr(f_type, 'align') else min(f_type.size, 8)
                        max_align = max(max_align, f_align)

                        if kind == 'UNION':
                            fields[f_name] = (f_type, 0)
                            max_field_size = max(max_field_size, f_type.size)
                        else:
                            if f_align > 0 and (offset % f_align) != 0:
                                offset += f_align - (offset % f_align)
                            fields[f_name] = (f_type, offset)
                            offset += f_type.size

                    if kind == 'UNION':
                        s_size = max_field_size
                        if max_align > 0 and (s_size % max_align) != 0:
                            s_size += max_align - (s_size % max_align)
                    else:
                        s_size = max(offset, 1)
                        if max_align > 0 and (s_size % max_align) != 0:
                            s_size += max_align - (s_size % max_align)

                    s_type = CType(kind, size=s_size, fields=fields, name=s_name, align=max_align)
                    if s_name:
                        self.env.define_struct(s_name, s_type)
                    btype = s_type
                else:
                    btype = self.env.get_struct(s_name) or CType(kind, name=s_name)
            else:
                return None
        elif tok.kind == TOKEN_IDENT:
            t = self.env.get_type(tok.val)
            if t:
                self.consume()
                btype = t
            else:
                return None
        else:
            return None

        while self.match_op('*'):
            btype = CType('POINTER', target_type=btype, size=8, align=8)

        return btype

    def parse_block(self):
        self.match_punct('{')
        stmts = []
        while not self.match_punct('}') and self.peek().kind != TOKEN_EOF:
            s = self.parse_statement()
            if s:
                if isinstance(s, list):
                    stmts.extend(s)
                else:
                    stmts.append(s)
        return ASTBlock(stmts)

    def parse_statement(self):
        tok = self.peek()

        if tok.kind == TOKEN_PUNCT and tok.val == '{':
            return self.parse_block()

        if tok.kind == TOKEN_KEYWORD:
            kw = tok.val
            if kw == 'if':
                self.consume()
                self.match_punct('(')
                cond = self.parse_expression()
                self.match_punct(')')
                then_b = self.parse_statement()
                else_b = None
                if self.match_keyword('else'):
                    else_b = self.parse_statement()
                return ASTIf(cond, then_b, else_b)
            elif kw == 'while':
                self.consume()
                self.match_punct('(')
                cond = self.parse_expression()
                self.match_punct(')')
                body = self.parse_statement()
                return ASTWhile(cond, body)
            elif kw == 'do':
                self.consume()
                body = self.parse_statement()
                self.match_keyword('while')
                self.match_punct('(')
                cond = self.parse_expression()
                self.match_punct(')')
                self.match_punct(';')
                return ASTWhile(cond, body, is_do_while=True)
            elif kw == 'for':
                self.consume()
                self.match_punct('(')
                init = None
                if not self.match_punct(';'):
                    init = self.parse_statement()
                    if not isinstance(init, ASTVarDecl) and not isinstance(init, list):
                        self.match_punct(';')
                cond = None
                if not self.match_punct(';'):
                    cond = self.parse_expression()
                    self.match_punct(';')
                incr = None
                if not self.match_punct(')'):
                    incr = self.parse_expression()
                    self.match_punct(')')
                body = self.parse_statement()
                return ASTFor(init, cond, incr, body)
            elif kw == 'switch':
                self.consume()
                self.match_punct('(')
                expr = self.parse_expression()
                self.match_punct(')')
                body = self.parse_statement()
                return ASTSwitch(expr, body)
            elif kw == 'case':
                self.consume()
                expr = self.parse_expression()
                self.match_punct(':')
                return ASTCase(expr)
            elif kw == 'default':
                self.consume()
                self.match_punct(':')
                return ASTDefault()
            elif kw == 'break':
                self.consume()
                self.match_punct(';')
                return ASTBreak()
            elif kw == 'continue':
                self.consume()
                self.match_punct(';')
                return ASTContinue()
            elif kw == 'return':
                self.consume()
                expr = None
                if not self.match_punct(';'):
                    expr = self.parse_expression()
                    self.match_punct(';')
                return ASTReturn(expr)
            elif kw == 'goto':
                self.consume()
                lbl = self.consume().val
                self.match_punct(';')
                return ASTGoto(lbl)
            elif kw in ('int', 'char', 'short', 'long', 'float', 'double', 'void', 'struct', 'union', 'unsigned', 'signed', 'static'):
                return self.parse_top_level()

        if tok.kind == TOKEN_IDENT and self.peek(1).val == ':':
            lbl = self.consume().val
            self.consume()
            return ASTLabel(lbl)

        expr = self.parse_expression()
        self.match_punct(';')
        return ASTExprStmt(expr)

    def parse_expression(self):
        if self.match_punct('{'):
            exprs = []
            if not self.match_punct('}'):
                while True:
                    exprs.append(self.parse_expression())
                    if self.match_punct('}'):
                        break
                    self.match_punct(',')
            return ASTInitList(exprs)

        return self.parse_assignment()

    def parse_assignment(self):
        left = self.parse_ternary()
        tok = self.peek()
        if tok.kind == TOKEN_OPERATOR and tok.val in ('=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>='):
            op = self.consume().val
            right = self.parse_assignment()
            return ASTBinaryOp(op, left, right)
        return left

    def parse_ternary(self):
        cond = self.parse_logical_or()
        if self.match_op('?'):
            then_expr = self.parse_expression()
            self.match_punct(':')
            else_expr = self.parse_ternary()
            return ASTTernary(cond, then_expr, else_expr)
        return cond

    def parse_logical_or(self):
        left = self.parse_logical_and()
        while self.match_op('||'):
            right = self.parse_logical_and()
            left = ASTBinaryOp('||', left, right)
        return left

    def parse_logical_and(self):
        left = self.parse_bitwise_or()
        while self.match_op('&&'):
            right = self.parse_bitwise_or()
            left = ASTBinaryOp('&&', left, right)
        return left

    def parse_bitwise_or(self):
        left = self.parse_bitwise_xor()
        while self.match_op('|'):
            right = self.parse_bitwise_xor()
            left = ASTBinaryOp('|', left, right)
        return left

    def parse_bitwise_xor(self):
        left = self.parse_bitwise_and()
        while self.match_op('^'):
            right = self.parse_bitwise_and()
            left = ASTBinaryOp('^', left, right)
        return left

    def parse_bitwise_and(self):
        left = self.parse_equality()
        while self.match_op('&'):
            right = self.parse_equality()
            left = ASTBinaryOp('&', left, right)
        return left

    def parse_equality(self):
        left = self.parse_relational()
        while self.peek().kind == TOKEN_OPERATOR and self.peek().val in ('==', '!='):
            op = self.consume().val
            right = self.parse_relational()
            left = ASTBinaryOp(op, left, right)
        return left

    def parse_relational(self):
        left = self.parse_shift()
        while self.peek().kind == TOKEN_OPERATOR and self.peek().val in ('<', '<=', '>', '>='):
            op = self.consume().val
            right = self.parse_shift()
            left = ASTBinaryOp(op, left, right)
        return left

    def parse_shift(self):
        left = self.parse_additive()
        while self.peek().kind == TOKEN_OPERATOR and self.peek().val in ('<<', '>>'):
            op = self.consume().val
            right = self.parse_additive()
            left = ASTBinaryOp(op, left, right)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.peek().kind == TOKEN_OPERATOR and self.peek().val in ('+', '-'):
            op = self.consume().val
            right = self.parse_multiplicative()
            left = ASTBinaryOp(op, left, right)
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.peek().kind == TOKEN_OPERATOR and self.peek().val in ('*', '/', '%'):
            op = self.consume().val
            right = self.parse_unary()
            left = ASTBinaryOp(op, left, right)
        return left

    def parse_unary(self):
        tok = self.peek()
        if tok.kind == TOKEN_OPERATOR and tok.val in ('++', '--', '+', '-', '!', '~', '*', '&'):
            op = self.consume().val
            operand = self.parse_unary()
            return ASTUnaryOp(op, operand)
        elif tok.kind == TOKEN_KEYWORD and tok.val == 'sizeof':
            self.consume()
            if self.match_punct('('):
                t = self.parse_type()
                if t:
                    self.match_punct(')')
                    return ASTSizeof(t)
                else:
                    expr = self.parse_expression()
                    self.match_punct(')')
                    return ASTSizeof(expr)
            else:
                expr = self.parse_unary()
                return ASTSizeof(expr)
        elif tok.kind == TOKEN_PUNCT and tok.val == '(':
            saved_pos = self.pos
            self.consume()
            t = self.parse_type()
            if t and self.match_punct(')'):
                expr = self.parse_unary()
                return ASTCast(t, expr)
            self.pos = saved_pos

        return self.parse_postfix()

    def parse_postfix(self):
        left = self.parse_primary()
        while True:
            if self.match_punct('['):
                index = self.parse_expression()
                self.match_punct(']')
                left = ASTArraySubscript(left, index)
            elif self.match_punct('('):
                args = []
                if not self.match_punct(')'):
                    while True:
                        args.append(self.parse_expression())
                        if self.match_punct(')'):
                            break
                        self.match_punct(',')
                left = ASTCall(left, args)
            elif self.peek().val == '.':
                self.consume()
                member = self.consume().val
                left = ASTMemberAccess(left, member, is_arrow=False)
            elif self.match_op('->'):
                member = self.consume().val
                left = ASTMemberAccess(left, member, is_arrow=True)
            elif self.peek().kind == TOKEN_OPERATOR and self.peek().val in ('++', '--'):
                op = self.consume().val
                left = ASTUnaryOp(op, left, is_postfix=True)
            else:
                break
        return left

    def parse_primary(self):
        tok = self.consume()
        if tok.kind == TOKEN_NUMBER:
            return ASTLiteral(CTYPE_INT, tok.val)
        elif tok.kind == TOKEN_FLOAT:
            return ASTLiteral(CTYPE_DOUBLE, tok.val)
        elif tok.kind == TOKEN_CHAR:
            return ASTLiteral(CTYPE_CHAR, tok.val)
        elif tok.kind == TOKEN_STRING:
            addr = mem.alloc_string(tok.val)
            return ASTLiteral(CTYPE_CHAR_PTR, addr)
        elif tok.kind == TOKEN_IDENT:
            return ASTVar(tok.val)
        elif tok.kind == TOKEN_PUNCT and tok.val == '(':
            expr = self.parse_expression()
            self.match_punct(')')
            return expr
        return ASTLiteral(CTYPE_INT, 0)

def evaluate_const_expr(node):
    if isinstance(node, ASTLiteral):
        return node.val
    elif isinstance(node, ASTBinaryOp):
        l = evaluate_const_expr(node.left)
        r = evaluate_const_expr(node.right)
        if node.op == '+': return l + r
        elif node.op == '-': return l - r
        elif node.op == '*': return l * r
        elif node.op == '/': return l // r if r != 0 else 0
    return 1

# -----------------------------------------------------------------------------
# Standard Library Functions
# -----------------------------------------------------------------------------

def builtin_printf(env, args):
    if not args:
        return 0
    fmt = args[0].get_val()
    if isinstance(fmt, int):
        fmt = mem.read_string(fmt)

    py_args = []
    for arg_val in args[1:]:
        v = arg_val.get_val()
        if isinstance(v, int) and (arg_val.ctype.is_pointer() or arg_val.ctype.is_array()):
            py_args.append(mem.read_string(v) if v != 0 else "(null)")
        else:
            py_args.append(v)

    out = []
    i = 0
    n = len(fmt)
    arg_idx = 0

    while i < n:
        if fmt[i] == '%' and i + 1 < n:
            if fmt[i + 1] == '%':
                out.append('%')
                i += 2
                continue

            m = re.match(r'%([-+0 #]*\d*(?:\.\d*)?)(h|hh|l|ll|z|j|t)?([diuoxXfFeEgGaAcsp])', fmt[i:])
            if m:
                fmt_spec = m.group(0)
                sub_fmt = m.group(1)
                mod = m.group(2)
                type_char = m.group(3)

                if arg_idx < len(py_args):
                    v = py_args[arg_idx]
                    arg_idx += 1

                    if type_char in ('u', 'x', 'X', 'o'):
                        v_unsigned = int(v) & 0xFFFFFFFF
                        clean_spec = f"%{sub_fmt}{type_char}"
                        out.append(clean_spec % v_unsigned)
                    elif type_char in ('d', 'i', 'c', 'f', 'F', 'e', 'E', 'g', 'G', 's'):
                        clean_spec = f"%{sub_fmt}{type_char}"
                        try:
                            out.append(clean_spec % v)
                        except Exception:
                            out.append(str(v))
                    elif type_char == 'p':
                        out.append(f"0x{int(v):x}")
                    else:
                        out.append(str(v))
                else:
                    out.append(fmt_spec)
                i += len(fmt_spec)
                continue

        out.append(fmt[i])
        i += 1

    res_str = "".join(out)
    sys.stdout.write(res_str)
    sys.stdout.flush()
    return len(res_str)

def builtin_sprintf(env, args):
    if len(args) < 2:
        return 0
    buf_ptr = args[0].get_val()
    fmt = args[1].get_val()
    if isinstance(fmt, int):
        fmt = mem.read_string(fmt)

    sub_args = args[1:]
    old_stdout = sys.stdout
    from io import StringIO
    capture = StringIO()
    sys.stdout = capture
    try:
        builtin_printf(env, sub_args)
    finally:
        sys.stdout = old_stdout

    res_str = capture.getvalue()
    mem.write_string(buf_ptr, res_str)
    return len(res_str)

def builtin_snprintf(env, args):
    if len(args) < 3:
        return 0
    buf_ptr = args[0].get_val()
    sub_args = [args[0]] + args[2:]
    return builtin_sprintf(env, sub_args)

def builtin_malloc(env, args):
    size = args[0].get_val() if args else 0
    return mem.malloc(size)

def builtin_calloc(env, args):
    num = args[0].get_val() if len(args) > 0 else 1
    size = args[1].get_val() if len(args) > 1 else 0
    return mem.calloc(num, size)

def builtin_realloc(env, args):
    ptr = args[0].get_val() if len(args) > 0 else 0
    size = args[1].get_val() if len(args) > 1 else 0
    return mem.realloc(ptr, size)

def builtin_free(env, args):
    if args:
        mem.free(args[0].get_val())
    return 0

def builtin_memset(env, args):
    if len(args) < 3: return 0
    ptr = args[0].get_val()
    val = args[1].get_val() & 0xFF
    size = args[2].get_val()
    mem.write_bytes(ptr, bytes([val] * size))
    return ptr

def builtin_memcpy(env, args):
    if len(args) < 3: return 0
    dest = args[0].get_val()
    src = args[1].get_val()
    size = args[2].get_val()
    b_data = mem.read_bytes(src, size)
    mem.write_bytes(dest, b_data)
    return dest

def builtin_strcpy(env, args):
    if len(args) < 2: return 0
    dest = args[0].get_val()
    src = args[1].get_val()
    s = mem.read_string(src)
    mem.write_string(dest, s)
    return dest

def builtin_strlen(env, args):
    if not args: return 0
    src = args[0].get_val()
    if isinstance(src, int):
        s = mem.read_string(src)
        return len(s)
    return 0

def builtin_strcmp(env, args):
    if len(args) < 2: return 0
    s1 = mem.read_string(args[0].get_val())
    s2 = mem.read_string(args[1].get_val())
    if s1 < s2: return -1
    elif s1 > s2: return 1
    return 0

def builtin_exit(env, args):
    code = args[0].get_val() if args else 0
    sys.exit(code)

BUILTIN_FUNCS = {
    'printf': builtin_printf,
    'sprintf': builtin_sprintf,
    'snprintf': builtin_snprintf,
    'malloc': builtin_malloc,
    'calloc': builtin_calloc,
    'realloc': builtin_realloc,
    'free': builtin_free,
    'memset': builtin_memset,
    'memcpy': builtin_memcpy,
    'strcpy': builtin_strcpy,
    'strlen': builtin_strlen,
    'strcmp': builtin_strcmp,
    'exit': builtin_exit,
}

# -----------------------------------------------------------------------------
# CEvaluator Engine
# -----------------------------------------------------------------------------

class CEvaluator:
    def __init__(self, env):
        self.env = env
        self.static_vars = {}

    def eval(self, node):
        if node is None:
            return Value(CTYPE_VOID, 0)
        if isinstance(node, list):
            res = Value(CTYPE_VOID, 0)
            for item in node:
                res = self.eval(item)
            return res
        method_name = 'eval_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_eval)
        return visitor(node)

    def generic_eval(self, node):
        return Value(CTYPE_VOID, 0)

    def eval_ASTProgram(self, node):
        for decl in node.decls:
            self.eval(decl)
        return Value(CTYPE_VOID, 0)

    def eval_ASTVarDecl(self, node):
        if node.is_static:
            key = (id(node), node.name)
            if key in self.static_vars:
                val_obj = self.static_vars[key]
                self.env.define_var(node.name, val_obj)
                return val_obj

        size = node.ctype.size
        addr = mem.malloc(size)
        val_obj = Value(node.ctype, None, addr=addr, is_lvalue=True)
        self.env.define_var(node.name, val_obj)

        if node.init_expr:
            if isinstance(node.init_expr, ASTInitList):
                flat_exprs = flatten_init_list(node.init_expr)
                elem_type = node.ctype.target_type if node.ctype.is_array() else CTYPE_INT
                while elem_type.is_array():
                    elem_type = elem_type.target_type
                for i, expr in enumerate(flat_exprs):
                    ev = self.eval(expr).get_val()
                    elem_addr = addr + i * elem_type.size
                    e_obj = Value(elem_type, ev, addr=elem_addr, is_lvalue=True)
                    e_obj.set_val(ev)
            else:
                init_val = self.eval(node.init_expr).get_val()
                val_obj.set_val(init_val)

        if node.is_static:
            self.static_vars[key] = val_obj

        return val_obj

    def eval_ASTFuncDef(self, node):
        self.env.define_func(node.name, node)
        return Value(CTYPE_VOID, 0)

    def eval_ASTBlock(self, node):
        block_env = Environment(self.env)
        old_env = self.env
        self.env = block_env

        labels = {}
        for idx, stmt in enumerate(node.stmts):
            if isinstance(stmt, ASTLabel):
                labels[stmt.label] = idx

        idx = 0
        try:
            while idx < len(node.stmts):
                stmt = node.stmts[idx]
                try:
                    self.eval(stmt)
                    idx += 1
                except GotoException as g:
                    if g.label in labels:
                        idx = labels[g.label]
                    else:
                        raise g
        finally:
            self.env = old_env
        return Value(CTYPE_VOID, 0)

    def eval_ASTExprStmt(self, node):
        return self.eval(node.expr)

    def eval_ASTIf(self, node):
        cond_val = self.eval(node.cond).get_val()
        if cond_val:
            return self.eval(node.then_branch)
        elif node.else_branch:
            return self.eval(node.else_branch)
        return Value(CTYPE_VOID, 0)

    def eval_ASTWhile(self, node):
        if node.is_do_while:
            while True:
                try:
                    self.eval(node.body)
                except ContinueException:
                    pass
                except BreakException:
                    break
                if not self.eval(node.cond).get_val():
                    break
        else:
            while self.eval(node.cond).get_val():
                try:
                    self.eval(node.body)
                except ContinueException:
                    pass
                except BreakException:
                    break
        return Value(CTYPE_VOID, 0)

    def eval_ASTFor(self, node):
        if node.init:
            self.eval(node.init)
        while True:
            if node.cond and not self.eval(node.cond).get_val():
                break
            try:
                self.eval(node.body)
            except ContinueException:
                pass
            except BreakException:
                break
            if node.incr:
                self.eval(node.incr)
        return Value(CTYPE_VOID, 0)

    def eval_ASTSwitch(self, node):
        val = self.eval(node.expr).get_val()
        if isinstance(node.body, ASTBlock):
            match_found = False
            for stmt in node.body.stmts:
                if isinstance(stmt, ASTCase):
                    c_val = self.eval(stmt.expr).get_val()
                    if c_val == val or match_found:
                        match_found = True
                elif isinstance(stmt, ASTDefault):
                    match_found = True
                elif match_found:
                    try:
                        self.eval(stmt)
                    except BreakException:
                        break
        return Value(CTYPE_VOID, 0)

    def eval_ASTReturn(self, node):
        ret_val = self.eval(node.expr).get_val() if node.expr else 0
        raise ReturnException(ret_val)

    def eval_ASTBreak(self, node): raise BreakException()
    def eval_ASTContinue(self, node): raise ContinueException()
    def eval_ASTGoto(self, node): raise GotoException(node.label)
    def eval_ASTLabel(self, node): return Value(CTYPE_VOID, 0)
    def eval_ASTLiteral(self, node): return Value(node.ctype, node.val)

    def eval_ASTVar(self, node):
        var_obj = self.env.get_var(node.name)
        if var_obj is None:
            if node.name in BUILTIN_FUNCS:
                return Value(CTYPE_VOID_PTR, BUILTIN_FUNCS[node.name])
            return Value(CTYPE_INT, 0)
        return var_obj

    def eval_ASTBinaryOp(self, node):
        if node.op == '=':
            left_val = self.eval(node.left)
            right_val = self.eval(node.right).get_val()
            left_val.set_val(right_val)
            return left_val

        if node.op in ('+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>='):
            left_val = self.eval(node.left)
            l = left_val.get_val()
            r = self.eval(node.right).get_val()
            op_pure = node.op[:-1]
            res = self._calc_bin_op(op_pure, l, r, left_val.ctype, right_type=left_val.ctype)
            left_val.set_val(res)
            return left_val

        left_val = self.eval(node.left)
        right_val = self.eval(node.right)
        l = left_val.get_val()
        r = right_val.get_val()

        if left_val.ctype.is_pointer() and right_val.ctype.is_int():
            elem_size = left_val.ctype.target_type.size if left_val.ctype.target_type else 1
            if node.op == '+':
                return Value(left_val.ctype, l + r * elem_size)
            elif node.op == '-':
                return Value(left_val.ctype, l - r * elem_size)

        res = self._calc_bin_op(node.op, l, r, left_val.ctype, right_val.ctype)
        res_type = CTYPE_DOUBLE if (left_val.ctype.is_fp() or right_val.ctype.is_fp()) else CTYPE_INT
        return Value(res_type, res)

    def _calc_bin_op(self, op, l, r, left_type, right_type=None):
        is_fp = left_type.is_fp() or (right_type is not None and right_type.is_fp())
        if op == '+': return l + r
        elif op == '-': return l - r
        elif op == '*': return l * r
        elif op == '/': return (float(l) / float(r)) if is_fp else (int(l // r) if r != 0 else 0)
        elif op == '%': return int(l % r) if r != 0 else 0
        elif op == '==': return 1 if l == r else 0
        elif op == '!=': return 1 if l != r else 0
        elif op == '<': return 1 if l < r else 0
        elif op == '<=': return 1 if l <= r else 0
        elif op == '>': return 1 if l > r else 0
        elif op == '>=': return 1 if l >= r else 0
        elif op == '&&': return 1 if (l and r) else 0
        elif op == '||': return 1 if (l or r) else 0
        elif op == '&': return int(l) & int(r)
        elif op == '|': return int(l) | int(r)
        elif op == '^': return int(l) ^ int(r)
        elif op == '<<': return int(l) << int(r)
        elif op == '>>': return int(l) >> int(r)
        return 0

    def eval_ASTUnaryOp(self, node):
        if node.op == '&':
            operand_val = self.eval(node.operand)
            return Value(CType('POINTER', target_type=operand_val.ctype, size=8, align=8), operand_val.addr)
        elif node.op == '*':
            operand_val = self.eval(node.operand)
            addr = operand_val.get_val()
            target_t = operand_val.ctype.target_type or CTYPE_INT
            return Value(target_t, None, addr=addr, is_lvalue=True)
        elif node.op in ('++', '--'):
            operand_val = self.eval(node.operand)
            old_v = operand_val.get_val()
            step = operand_val.ctype.target_type.size if operand_val.ctype.is_pointer() else 1
            new_v = old_v + step if node.op == '++' else old_v - step
            operand_val.set_val(new_v)
            return Value(operand_val.ctype, old_v if node.is_postfix else new_v)
        elif node.op == '!':
            v = self.eval(node.operand).get_val()
            return Value(CTYPE_INT, 1 if not v else 0)
        elif node.op == '~':
            v = self.eval(node.operand).get_val()
            return Value(CTYPE_INT, ~int(v))
        elif node.op == '-':
            v = self.eval(node.operand).get_val()
            return Value(CTYPE_INT, -v)
        elif node.op == '+':
            return self.eval(node.operand)
        return Value(CTYPE_INT, 0)

    def eval_ASTTernary(self, node):
        cond = self.eval(node.cond).get_val()
        if cond:
            return self.eval(node.then_expr)
        else:
            return self.eval(node.else_expr)

    def eval_ASTCast(self, node):
        val = self.eval(node.expr).get_val()
        coerced = coerce_value(node.target_type, val)
        return Value(node.target_type, coerced)

    def eval_ASTCall(self, node):
        func_val = self.eval(node.callee)
        args_eval = [self.eval(arg) for arg in node.args]

        if callable(func_val.val):
            res = func_val.val(self.env, args_eval)
            return Value(CTYPE_INT, res)

        func_name = node.callee.name if isinstance(node.callee, ASTVar) else None
        fdef = self.env.get_func(func_name)
        if fdef:
            func_env = Environment(self.env)
            for (p_type, p_name), arg_obj in zip(fdef.params, args_eval):
                if p_name:
                    p_addr = mem.malloc(p_type.size)
                    p_val_obj = Value(p_type, arg_obj.get_val(), addr=p_addr, is_lvalue=True)
                    p_val_obj.set_val(arg_obj.get_val())
                    func_env.define_var(p_name, p_val_obj)

            old_env = self.env
            self.env = func_env
            try:
                self.eval(fdef.body)
            except ReturnException as ret:
                return Value(fdef.return_type, ret.value)
            finally:
                self.env = old_env

        return Value(CTYPE_INT, 0)

    def eval_ASTMemberAccess(self, node):
        obj_val = self.eval(node.expr)
        if node.is_arrow:
            base_addr = obj_val.get_val()
            struct_type = obj_val.ctype.target_type
        else:
            base_addr = obj_val.addr if obj_val.addr is not None else obj_val.get_val()
            struct_type = obj_val.ctype

        if struct_type and node.member_name in struct_type.fields:
            field_type, offset = struct_type.fields[node.member_name]
            field_addr = base_addr + offset
            return Value(field_type, None, addr=field_addr, is_lvalue=True)
        return Value(CTYPE_INT, 0)

    def eval_ASTArraySubscript(self, node):
        arr_val = self.eval(node.array_expr)
        idx_val = self.eval(node.index_expr).get_val()

        if arr_val.ctype.is_array():
            base_addr = arr_val.addr
            elem_type = arr_val.ctype.target_type
        elif arr_val.ctype.is_pointer():
            base_addr = arr_val.get_val()
            elem_type = arr_val.ctype.target_type
        else:
            base_addr = arr_val.get_val()
            elem_type = CTYPE_INT

        elem_addr = base_addr + idx_val * elem_type.size
        return Value(elem_type, None, addr=elem_addr, is_lvalue=True)

    def eval_ASTSizeof(self, node):
        if isinstance(node.target, CType):
            return Value(CTYPE_INT, node.target.size)
        else:
            v = self.eval(node.target)
            return Value(CTYPE_INT, v.ctype.size)

# -----------------------------------------------------------------------------
# Main Interpreter Driver & CLI
# -----------------------------------------------------------------------------

def run_c_program(source_text, filename="<stdin>", args=None):
    clean_code = preprocess_code(source_text)
    tokens = tokenize(clean_code)

    global_env = Environment()
    parser = CParser(tokens, global_env)
    program = parser.parse_program()

    evaluator = CEvaluator(global_env)
    evaluator.eval(program)

    main_func = global_env.get_func('main')
    if main_func:
        args_eval = []
        if len(main_func.params) >= 2:
            argv_list = args or [filename]
            argc = len(argv_list)
            argv_ptrs = []
            for arg_str in argv_list:
                str_addr = mem.malloc(len(arg_str) + 1)
                mem.write_string(str_addr, arg_str)
                argv_ptrs.append(str_addr)

            argv_array_addr = mem.malloc(len(argv_ptrs) * 8)
            for idx, p_addr in enumerate(argv_ptrs):
                mem.write_int(argv_array_addr + idx * 8, 8, p_addr, signed=False)

            args_eval = [Value(CTYPE_INT, argc), Value(CTYPE_CHAR_PTR, argv_array_addr)]

        func_env = Environment(global_env)
        for (p_type, p_name), arg_obj in zip(main_func.params, args_eval):
            if p_name:
                p_addr = mem.malloc(p_type.size)
                p_val_obj = Value(p_type, arg_obj.get_val(), addr=p_addr, is_lvalue=True)
                p_val_obj.set_val(arg_obj.get_val())
                func_env.define_var(p_name, p_val_obj)

        evaluator.env = func_env
        try:
            evaluator.eval(main_func.body)
        except ReturnException as ret:
            return ret.value
    return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: picoc <file1.c>... [- <arg1>...]")
        sys.exit(1)

    param_count = 1
    if sys.argv[param_count] in ("-h", "--help"):
        print("picoc C interpreter in Python")
        sys.exit(0)

    if sys.argv[param_count] == "-c":
        print("picoc Python 3 migration")
        sys.exit(0)

    dont_run_main = False
    if sys.argv[param_count] == "-s":
        dont_run_main = True
        param_count += 1

    files = []
    args = []
    in_args = False

    for arg in sys.argv[param_count:]:
        if arg == "-":
            in_args = True
            continue
        if in_args:
            args.append(arg)
        else:
            files.append(arg)

    if not files:
        sys.exit(0)

    combined_code = []
    for fname in files:
        with open(fname, 'r', encoding='utf-8', errors='replace') as f:
            combined_code.append(f.read())

    code_text = "\n".join(combined_code)
    exit_code = run_c_program(code_text, filename=files[0], args=args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
