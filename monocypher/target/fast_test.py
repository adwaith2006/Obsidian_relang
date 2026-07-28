#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, glob, json, subprocess
from concurrent.futures import ProcessPoolExecutor

target_dir = os.path.dirname(os.path.abspath(__file__))
monocypher_py = os.path.join(target_dir, "monocypher.py")
monocypher_dir = os.path.dirname(target_dir)
input_dir = os.path.join(monocypher_dir, "relang", "input")
output_dir = os.path.join(monocypher_dir, "relang", "output")

in_files = sorted(glob.glob(os.path.join(input_dir, "*.json")))

def run_single(in_path):
    base = os.path.basename(in_path)
    out_path = os.path.join(output_dir, base)
    
    with open(in_path, 'r', encoding='utf-8') as f:
        in_json = json.load(f)
    with open(out_path, 'r', encoding='utf-8') as f:
        out_json = json.load(f)

    in_data = in_json.get("data", "")
    expected_out = out_json.get("output", "")

    res = subprocess.run([sys.executable, monocypher_py], input=in_data, capture_output=True, text=True)
    
    actual_out = res.stdout
    if actual_out == expected_out and res.returncode == 0:
        return (base, True, "")
    else:
        err = f"ReturnCode: {res.returncode}\nExpected:\n{expected_out}\nActual:\n{actual_out}\nStderr:\n{res.stderr}"
        return (base, False, err)

def main():
    print(f"Testing {len(in_files)} test cases across pool...")
    passed = 0
    failed = []
    
    with ProcessPoolExecutor() as executor:
        results = executor.map(run_single, in_files)
        for base, ok, err in results:
            if ok:
                passed += 1
            else:
                failed.append((base, err))

    print(f"\n=========================================")
    print(f"RESULTS: {passed}/{len(in_files)} PASSED")
    print(f"=========================================\n")

    if failed:
        print(f"Failed {len(failed)} test cases:")
        # Group failures by prefix
        failed_by_cat = {}
        for base, err in failed:
            cat = base.split("_")[0] + "_" + base.split("_")[1] if "_" in base else "other"
            failed_by_cat.setdefault(cat, []).append((base, err))

        for cat, items in failed_by_cat.items():
            print(f"\n--- Category: {cat} ({len(items)} failed) ---")
            for base, err in items[:3]: # print sample
                print(f"File: {base}")
                print(err[:300])

if __name__ == "__main__":
    main()
