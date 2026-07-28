#!/usr/bin/env python3
"""
Test runner for Python picoc implementation.
"""

import sys
import os
import tempfile
import subprocess

TEST_PROGRAMS = [
    ("Basic Printf & Types", """
#include <stdio.h>
int main() {
    int a = 40;
    int b = 2;
    printf("Sum: %d\\n", a + b);
    return 0;
}
""", "Sum: 42\n"),

    ("Control Flow (for/while/goto)", """
#include <stdio.h>
int main() {
    int sum = 0;
    for (int i = 1; i <= 5; i++) {
        sum += i;
    }
    printf("Sum 1..5: %d\\n", sum);
    return 0;
}
""", "Sum 1..5: 15\n"),

    ("Structs & Unions", """
#include <stdio.h>
struct Point { int x; int y; };
union Data { int i; char str[4]; };

int main() {
    struct Point p = { 10, 20 };
    printf("Point: %d, %d (sizeof: %d)\\n", p.x, p.y, (int)sizeof(struct Point));
    union Data d;
    d.i = 1094861641;
    printf("Union str: %.4s\\n", d.str);
    return 0;
}
""", "Point: 10, 20 (sizeof: 8)\nUnion str: ICBA\n"),

    ("Static Variables", """
#include <stdio.h>
int counter() {
    static int val = 0;
    val += 1;
    return val;
}
int main() {
    printf("%d %d %d\\n", counter(), counter(), counter());
    return 0;
}
""", "1 2 3\n")
]

def run_tests():
    picoc_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "picoc.py")
    passed = 0
    total = len(TEST_PROGRAMS)

    for name, code, expected in TEST_PROGRAMS:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(code)
            tmp_name = f.name

        try:
            res = subprocess.run([sys.executable, picoc_py, tmp_name], capture_output=True, text=True)
            if res.stdout == expected:
                print(f"[PASS] {name}")
                passed += 1
            else:
                print(f"[FAIL] {name}")
                print("  Actual:  ", repr(res.stdout))
                print("  Expected:", repr(expected))
        finally:
            os.remove(tmp_name)

    print(f"\nTest Summary: {passed}/{total} Passed")
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(run_tests())
