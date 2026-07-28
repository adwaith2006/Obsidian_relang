#!/usr/bin/env python3
"""Read-only spec extractor. Writes spec to target/SPEC.md"""
import os, glob, json, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDIR = os.path.join(BASE, 'relang', 'input')
OUTDIR = os.path.join(BASE, 'relang', 'output')

infiles = sorted(glob.glob(os.path.join(INDIR, '*.json')))

data = {}
for f in infiles:
    base = os.path.basename(f)
    tc_id = base.replace('.json', '')
    with open(f) as fp:
        tc = json.load(fp)
    out_path = os.path.join(OUTDIR, base)
    out_steps = []
    if os.path.exists(out_path):
        with open(out_path) as fp:
            od = json.load(fp)
        raw = od.get('output', '[]')
        try:
            out_steps = json.loads(raw)
        except Exception:
            out_steps = []
    data[tc_id] = {
        'steps': tc.get('data', {}).get('steps', []),
        'outputs': out_steps,
    }

# Print everything
for tc_id, info in sorted(data.items()):
    steps = info['steps']
    outputs = info['outputs']
    print("=== " + tc_id + " ===")
    for i, step in enumerate(steps):
        req = step.get('request', {})
        exp = step.get('expected', {})
        sc = step.get('storeCookies', {})
        store = step.get('store', {})
        sh = step.get('storeHtml', {})
        method = req.get('method', 'GET')
        path = req.get('path', '/')
        headers = req.get('headers', {})
        body = req.get('body', '')
        status = exp.get('status', '?')
        exp_body = exp.get('body', '')

        out = {}
        for o in outputs:
            if o.get('step') == i + 1:
                out = o
                break

        out_status = out.get('status', '')
        out_body = out.get('body', '')
        out_ct = out.get('content-type', '')

        print("  STEP " + str(i+1) + ": " + method + " " + path + " -> " + str(status))
        if headers:
            print("    headers: " + str(headers))
        if body:
            print("    body: " + str(body)[:200])
        if sc:
            print("    storeCookies: " + str(sc))
        if store:
            print("    store: " + str(store))
        if sh:
            print("    storeHtml: " + str(sh))
        if exp_body:
            print("    expectedBody: " + str(exp_body)[:200])
        if out_body:
            print("    OUT ct=" + out_ct + " body=" + str(out_body)[:400])
    print()
