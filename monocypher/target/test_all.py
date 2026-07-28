#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, glob, subprocess

relang_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "relang"))
tester_py = os.path.join(relang_dir, "tester.py")
input_dir = os.path.join(relang_dir, "input")
cmd_target = f"python {os.path.abspath(os.path.join(os.path.dirname(__file__), 'monocypher.py'))}"

test_files = sorted(glob.glob(os.path.join(input_dir, "*.json")))
print(f"Total test cases found: {len(test_files)}")

passed = 0
failed = []

for idx, tf in enumerate(test_files):
    fname = os.path.basename(tf)
    res = subprocess.run([sys.executable, tester_py, cmd_target, tf], capture_output=True, text=True)
    if res.returncode == 0:
        passed += 1
    else:
        failed.append((fname, res.stdout + "\n" + res.stderr))

print(f"\nResults: {passed} passed, {len(failed)} failed out of {len(test_files)}")
if failed:
    print("\nFailed tests summary:")
    for f, err in failed[:20]:
        print(f" - {f}")
        for line in err.strip().split('\n'):
            if "FAIL" in line or "Error" in line or "Mismatch" in line or "diff" in line.lower():
                print(f"     {line}")
