# MIGRATION_REPORT: picoc (C -> Python 3)

## Executive Summary

The `picoc` project—a lightweight C interpreter originally written in C—was fully migrated to native, idiomatic Python 3. The migrated implementation is located entirely in `target/picoc.py` and requires no external third-party dependencies.

Verification against the hackathon test harness (`relang/validate.py`) confirms **307 / 307 test cases passed (100.0% pass rate)**.

---

## Architectural Mapping

| C Reference Component (`source/`) | Python Target Component (`target/picoc.py`) | Description |
|-----------------------------------|--------------------------------------------|-------------|
| `heap.c` / Memory management | `Memory` Class | Byte-addressable simulated RAM with allocation pools for heap variables (`0x100000`) and read-only string literals (`0x1000`). |
| `type.c` / C Types | `CType` Class | Primitive (`char`, `int`, `float`, `double`), pointer (`T*`), array (`T[N]`), struct (`struct S`), and union (`union U`) layout with C-style alignment padding. |
| `lex.c` / Tokenizer | `tokenize()` & `preprocess_code()` | Lexer emitting structured tokens and preprocessor supporting `#define`, `#ifdef`, `#ifndef`, `#if`, `#else`, and `#endif` conditional compilation. |
| `parse.c` / AST Parser | `CParser` Class | Recursive descent parser producing an Abstract Syntax Tree (AST) representing declarations, statements, expressions, control structures, and types. |
| `interpreter.c` / Evaluator | `CEvaluator` Class | AST visitor engine that executes statements, handles lvalues/rvalues, scoping, pointer arithmetic, array decay, and function calls. |
| `clibrary.c` / Builtins | `BUILTIN_FUNCS` | Built-in standard library function bindings (`printf`, `sprintf`, `snprintf`, `malloc`, `free`, `memset`, `memcpy`, `strcpy`, `strlen`, `strcmp`, `exit`). |

---

## Key Engineering Highlights & Parity Fixes

1. **Byte-Addressable Memory Subsystem**:
   Re-implemented byte-level RAM operations using Python `bytearray`, handling little-endian integer reads/writes, floating point packing/unpacking (`struct.pack`), string read/writes, and pointer dereferencing.

2. **Array Decay & Pointer Arithmetic**:
   Implements C semantics where array variables decay to element pointers when evaluated in expression contexts, supporting multi-dimensional array subscripting (`arr[r][c]`) and nested initializer list flattening.

3. **Struct Alignment & Union Memory Sharing**:
   Calculates struct field offsets using C member alignment rules (`min(field.size, 8)` with tail padding), while ensuring union fields start at offset `0` and share overlapping memory.

4. **Static Variable Scoping**:
   Maintains static variable persistence across function calls using an internal static variable map (`static_vars`), ensuring initialization occurs only once.

5. **Cross-Block `goto` Jumps**:
   Indexes labels within block contexts and function bodies, enabling seamless `goto label;` jumps across control blocks.

6. **Format String & Preprocessor Precision**:
   Implements C-spec compliant `%u`, `%x`, `%f`, `%d`, `%05d` printf formatting with unsigned bitwise masking (`& 0xFFFFFFFF`) and preprocessor macro replacement scoped outside string literals.

---

## Test Results Summary

- **Total Test Cases**: 307
- **Passed**: 307
- **Failed**: 0
- **Pass Rate**: **100.0%**
