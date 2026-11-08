from __future__ import annotations
import hashlib, os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

@dataclass
class DuplicateGroup:
    digest: str
    size: int
    paths: List[Path] = field(default_factory=list)

    @property
    def wasted_bytes(self) -> int:
        return self.size * (len(self.paths) - 1) if len(self.paths) > 1 else 0

def iter_files(root: Path, follow_symlinks: bool = False) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        for fname in filenames:
            p = Path(dirpath) / fname
            try:
                if p.is_symlink() and not follow_symlinks:
                    continue
                if p.is_file():
                    yield p
            except OSError:
                continue

def hash_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def find_duplicates(root: Path, min_size: int = 1, follow_symlinks: bool = False) -> List[DuplicateGroup]:
    size_buckets: Dict[int, List[Path]] = {}
    for path in iter_files(root, follow_symlinks=follow_symlinks):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < min_size:
            continue
        size_buckets.setdefault(size, []).append(path)

    hash_buckets: Dict[str, DuplicateGroup] = {}
    for size, paths in size_buckets.items():
        if len(paths) < 2:
            continue
        for path in paths:
            try:
                digest = hash_file(path)
            except OSError:
                continue
            key = f"{size}:{digest}"
            group = hash_buckets.setdefault(key, DuplicateGroup(digest=digest, size=size))
            group.paths.append(path)
    return [g for g in hash_buckets.values() if len(g.paths) > 1]

def plan_deletions(groups: List[DuplicateGroup], keep: str = "first") -> List[Path]:
    to_delete: List[Path] = []
    for group in groups:
        paths = list(group.paths)
        if keep == "shortest-path":
            paths.sort(key=lambda p: (len(str(p)), str(p)))
        survivor, rest = paths[0], paths[1:]
        to_delete.extend(rest)
    return to_delete

def apply_deletions(paths: Iterable[Path], trash_dir: Optional[Path] = None) -> List[Path]:
    removed: List[Path] = []
    for path in paths:
        try:
            if trash_dir is not None:
                trash_dir.mkdir(parents=True, exist_ok=True)
                dest = trash_dir / f"{len(removed)}_{path.name}"
                path.rename(dest)
            else:
                path.unlink()
            removed.append(path)
        except OSError:
            continue
    return removed
