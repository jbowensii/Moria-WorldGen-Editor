"""Sync the Moria WorldGen Editor source from the parent Moria-Replication project.

Pulls the latest editor + helper scripts from
`Moria-Replication/scripts/` into this repo's `scripts/` folder.

What this DOES:
- Copy SandboxZoneEditor.py, run_validator_headless.py, build_14floor_stairs.py
- Show a summary of what changed (line count diff, byte diff)
- Read DEFAULT_MOD_VERSION from the editor and report it
- Verify the editor imports cleanly after sync

What this does NOT do (intentionally — keep human in the loop):
- Auto-commit, tag, or push
- Modify SandboxZoneEditor.ini (preserves your local config)
- Modify any docs (README, WORLDGEN_GUIDE, RELEASE_NOTES) — those need manual updates per release

Usage:
    python sync.py                  # sync from default parent path
    python sync.py --parent <path>  # custom parent project path
    python sync.py --dry-run        # show what would change, don't copy

After running, manually:
- Update RELEASE_NOTES.md with the new version's highlights
- (Optional) Update WORLDGEN_GUIDE.md if architecture changed
- git add + commit + tag + push
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Files to sync from parent Moria-Replication project
FILES_TO_SYNC = [
    "scripts/SandboxZoneEditor.py",
    "scripts/run_validator_headless.py",
    "scripts/build_14floor_stairs.py",
]

DEFAULT_PARENT = Path(r"C:\Users\johnb\OneDrive\Documents\Projects\Moria-Replication")


def find_repo_root() -> Path:
    """Return the repo root (where this script lives)."""
    return Path(__file__).resolve().parent


def read_editor_version(editor_path: Path) -> str | None:
    """Extract DEFAULT_MOD_VERSION from SandboxZoneEditor.py."""
    if not editor_path.exists():
        return None
    text = editor_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^DEFAULT_MOD_VERSION\s*=\s*['\"]([^'\"]+)['\"]", text, re.M)
    return m.group(1) if m else None


def file_summary(path: Path) -> dict:
    """Return size + line count for a file."""
    if not path.exists():
        return {"exists": False, "size": 0, "lines": 0}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "exists": True,
        "size": path.stat().st_size,
        "lines": text.count("\n") + 1,
    }


def diff_summary(old: dict, new: dict) -> str:
    """Human-readable diff line."""
    if not old["exists"] and new["exists"]:
        return f"NEW    ({new['size']:,} bytes, {new['lines']:,} lines)"
    if old["exists"] and not new["exists"]:
        return "MISSING source!"
    if old == new:
        return "unchanged"
    dsize = new["size"] - old["size"]
    dlines = new["lines"] - old["lines"]
    sign_size = "+" if dsize >= 0 else ""
    sign_lines = "+" if dlines >= 0 else ""
    return f"updated  ({sign_size}{dsize:,} bytes, {sign_lines}{dlines:,} lines)"


def sync_file(parent: Path, repo: Path, rel: str, dry_run: bool) -> tuple[bool, str]:
    """Sync one file. Returns (changed, summary_line)."""
    src = parent / rel
    dst = repo / rel
    if not src.exists():
        return False, f"  {rel:<45} SOURCE MISSING ({src})"

    old = file_summary(dst)
    new = file_summary(src)

    if old == new:
        return False, f"  {rel:<45} unchanged"

    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return True, f"  {rel:<45} {diff_summary(old, new)}"


def verify_import(repo: Path) -> bool:
    """Run a headless import test of SandboxZoneEditor."""
    scripts_dir = repo / "scripts"
    cmd = [
        sys.executable,
        "-c",
        f"import sys; sys.path.insert(0, r'{scripts_dir}'); "
        "import SandboxZoneEditor; print('IMPORT OK')",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return "IMPORT OK" in result.stdout, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument(
        "--parent",
        type=Path,
        default=DEFAULT_PARENT,
        help=f"Parent Moria-Replication project path (default: {DEFAULT_PARENT})",
    )
    p.add_argument("--dry-run", action="store_true", help="Show what would change, don't copy")
    args = p.parse_args()

    repo = find_repo_root()
    parent = args.parent.resolve()

    print(f"Sync source : {parent}")
    print(f"Sync target : {repo}")
    print(f"Mode        : {'DRY RUN' if args.dry_run else 'LIVE COPY'}")
    print()

    if not parent.exists():
        print(f"ERROR: parent path does not exist: {parent}")
        return 2

    # Version check before/after
    old_version = read_editor_version(repo / "scripts/SandboxZoneEditor.py")
    new_version = read_editor_version(parent / "scripts/SandboxZoneEditor.py")

    print(f"Editor version (current repo) : {old_version or '(not present)'}")
    print(f"Editor version (parent source): {new_version or '(not found)'}")
    print()

    print("Files:")
    any_changed = False
    for rel in FILES_TO_SYNC:
        changed, line = sync_file(parent, repo, rel, args.dry_run)
        any_changed = any_changed or changed
        print(line)
    print()

    if args.dry_run:
        print("DRY RUN — no files changed.")
        return 0

    if not any_changed:
        print("Nothing to sync. Repo is already up to date.")
        return 0

    print("Verifying editor imports cleanly...")
    ok, output = verify_import(repo)
    if ok:
        print("  IMPORT OK")
    else:
        print("  IMPORT FAILED")
        print(output[:500])
        return 1
    print()

    print("Sync complete. Suggested next steps:")
    if new_version and new_version != old_version:
        print(f"  1. Update RELEASE_NOTES.md with v{new_version} highlights")
        print(f"  2. (Optional) Update WORLDGEN_GUIDE.md if architecture changed")
        print(f"  3. git add scripts/ RELEASE_NOTES.md")
        print(f"  4. git commit -m \"Sync editor v{new_version} from Moria-Replication\"")
        print(f"  5. git tag -a v{new_version} -m \"Moria WorldGen Editor v{new_version}\"")
        print(f"  6. git push origin main && git push origin v{new_version}")
    else:
        print("  1. git status")
        print("  2. git add scripts/")
        print("  3. git commit -m \"Sync editor source from Moria-Replication\"")
        print("  4. git push origin main")

    return 0


if __name__ == "__main__":
    sys.exit(main())
