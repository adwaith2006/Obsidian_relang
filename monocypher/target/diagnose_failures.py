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
    func_name = in_data.strip().split('\n')[0] if in_data else "unknown"
    if actual_out == expected_out and res.returncode == 0:
        return (base, func_name, True, "")
    else:
        err = f"Expected:\n{expected_out}\nActual:\n{actual_out}"
        return (base, func_name, False, err)

def main():
    by_func = {}
    with ProcessPoolExecutor() as executor:
        for base, func_name, ok, err in executor.map(run_single, in_files):
            if func_name not in by_func:
                by_func[func_name] = {"pass": 0, "fail": 0, "samples": []}
            if ok:
                by_func[func_name]["pass"] += 1
            else:
                by_func[func_name]["fail"] += 1
                by_func[func_name]["samples"].append((base, err))

    print(f"{'FUNCTION':<35} {'PASS':<8} {'FAIL':<8} {'TOTAL':<8}")
    print("=" * 65)
    for fn, stat in sorted(by_func.items()):
        total = stat["pass"] + stat["fail"]
        print(f"{fn:<35} {stat['pass']:<8} {stat['fail']:<8} {total:<8}")

if __name__ == "__main__":
    main()
