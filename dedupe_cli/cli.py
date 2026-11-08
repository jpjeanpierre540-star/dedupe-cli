from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .core import apply_deletions, find_duplicates, plan_deletions

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dedupe-cli", description="Find and (optionally) remove duplicate files in a directory tree.")
    parser.add_argument("path", type=str, help="Directory to scan recursively")
    parser.add_argument("--min-size", type=int, default=1, help="Ignore files smaller than this many bytes (default: 1)")
    parser.add_argument("--follow-symlinks", action="store_true", help="Follow symlinked directories/files while scanning (off by default)")
    parser.add_argument("--keep", choices=["first", "shortest-path"], default="first", help="Which copy to keep in each duplicate group (default: first)")
    parser.add_argument("--apply", action="store_true", help="Actually delete the redundant copies. Without this flag, dedupe-cli only reports what it would do (dry run).")
    parser.add_argument("--trash-dir", type=str, default=None, help="If set with --apply, move duplicates here instead of permanently deleting them.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a human-readable report.")
    return parser

def run(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.path).expanduser().resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    groups = find_duplicates(root, min_size=args.min_size, follow_symlinks=args.follow_symlinks)
    to_delete = plan_deletions(groups, keep=args.keep)
    total_wasted = sum(g.wasted_bytes for g in groups)
    removed = []
    if args.apply:
        trash_dir = Path(args.trash_dir).expanduser().resolve() if args.trash_dir else None
        removed = apply_deletions(to_delete, trash_dir=trash_dir)
    if args.json:
        payload = {
            "root": str(root), "duplicate_groups": len(groups), "redundant_files": len(to_delete),
            "wasted_bytes": total_wasted, "applied": bool(args.apply),
            "removed": [str(p) for p in removed],
            "groups": [{"digest": g.digest, "size": g.size, "paths": [str(p) for p in g.paths]} for g in groups],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(f"Scanned: {root}")
        print(f"Duplicate groups found: {len(groups)}")
        print(f"Redundant files: {len(to_delete)}")
        print(f"Space that could be reclaimed: {total_wasted:,} bytes")
        if not args.apply and to_delete:
            print("\n(dry run — pass --apply to actually remove redundant copies)")
        for g in groups:
            print(f"\n[{g.digest[:12]}] size={g.size}")
            for p in g.paths:
                marker = " (kept)" if p not in to_delete else " (would remove)"
                if args.apply:
                    marker = " (kept)" if p not in removed and p not in to_delete else (" (removed)" if p in removed else " (kept)")
                print(f"  - {p}{marker}")
    return 0

def main() -> None:
    raise SystemExit(run())

if __name__ == "__main__":
    main()
