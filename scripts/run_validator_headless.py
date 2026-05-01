"""Headless wrapper that loads every DataTable JSON and runs BuildValidator.
Prints a structured summary by severity. Useful for CI / scripted checks.
"""
import sys, os, json
from pathlib import Path

# Stub out the GUI imports so SandboxZoneEditor can be imported headlessly.
# tkinter is fine to import even without a display on Windows; we just don't
# instantiate any widgets.
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import SandboxZoneEditor as sze

def main():
    docs = {}
    for key, (fname, stem, label) in sze.DATATABLES.items():
        p = sze.WGR_DIR / fname
        d = sze.DataTableDoc(key, p, stem, label)
        if d.load():
            docs[key] = d
        else:
            print(f"[skip] {key}: {p} not found", file=sys.stderr)

    v = sze.BuildValidator(docs)
    issues = v.run()

    by_sev = {'error': [], 'warning': [], 'info': []}
    for it in issues:
        by_sev.setdefault(it.severity, []).append(it)

    print("=" * 78)
    print(f"VALIDATOR RESULTS: {len(issues)} issue(s)")
    for sev in ('error', 'warning', 'info'):
        bucket = by_sev.get(sev, [])
        print(f"  {sev.upper()}: {len(bucket)}")
    print("=" * 78)

    for sev in ('error', 'warning', 'info'):
        bucket = by_sev.get(sev, [])
        if not bucket: continue
        print(f"\n--- {sev.upper()} ({len(bucket)}) ---")
        for it in bucket:
            print(f"  [{it.check}] ({it.doc_key}) {it.detail}")

    return len(by_sev.get('error', []))

if __name__ == '__main__':
    sys.exit(main())
