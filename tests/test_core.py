import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dedupe_cli.core import (
    DuplicateGroup,
    apply_deletions,
    find_duplicates,
    hash_file,
    iter_files,
    plan_deletions,
)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestFindDuplicates(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_false_positives_on_unique_files(self):
        write(self.root / "a.txt", "aaaa")
        write(self.root / "b.txt", "bbbb")
        groups = find_duplicates(self.root)
        self.assertEqual(groups, [])

    def test_detects_duplicate_pair(self):
        write(self.root / "a.txt", "same content")
        write(self.root / "sub" / "b.txt", "same content")
        groups = find_duplicates(self.root)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].paths), 2)

    def test_detects_duplicate_triplet(self):
        write(self.root / "a.txt", "triple")
        write(self.root / "b.txt", "triple")
        write(self.root / "c.txt", "triple")
        groups = find_duplicates(self.root)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].paths), 3)

    def test_min_size_filter_excludes_small_files(self):
        write(self.root / "a.txt", "x")
        write(self.root / "b.txt", "x")
        groups = find_duplicates(self.root, min_size=10)
        self.assertEqual(groups, [])

    def test_same_size_different_content_is_not_a_duplicate(self):
        write(self.root / "a.txt", "AAAA")
        write(self.root / "b.txt", "BBBB")
        groups = find_duplicates(self.root)
        self.assertEqual(groups, [])

    def test_wasted_bytes_calculation(self):
        write(self.root / "a.txt", "12345")
        write(self.root / "b.txt", "12345")
        write(self.root / "c.txt", "12345")
        groups = find_duplicates(self.root)
        self.assertEqual(groups[0].wasted_bytes, 5 * 2)  # size * (n_copies - 1)

    def test_single_file_group_has_zero_wasted_bytes(self):
        group = DuplicateGroup(digest="x", size=100, paths=[Path("a")])
        self.assertEqual(group.wasted_bytes, 0)

    def test_symlinks_skipped_by_default(self):
        real = write(self.root / "real.txt", "content")
        link = self.root / "link.txt"
        try:
            link.symlink_to(real)
        except OSError:
            self.skipTest("symlinks not supported on this filesystem")
        files = list(iter_files(self.root, follow_symlinks=False))
        self.assertIn(real, files)
        self.assertNotIn(link, files)


class TestHashFile(unittest.TestCase):
    def test_hash_is_stable_across_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write(Path(tmp) / "f.txt", "stable content")
            self.assertEqual(hash_file(p), hash_file(p))

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = write(Path(tmp) / "a.txt", "one")
            b = write(Path(tmp) / "b.txt", "two")
            self.assertNotEqual(hash_file(a), hash_file(b))


class TestPlanDeletions(unittest.TestCase):
    def test_keep_first_keeps_the_first_listed_path(self):
        group = DuplicateGroup(digest="x", size=1, paths=[Path("a"), Path("b"), Path("c")])
        to_delete = plan_deletions([group], keep="first")
        self.assertEqual(to_delete, [Path("b"), Path("c")])

    def test_keep_shortest_path_keeps_the_shortest(self):
        group = DuplicateGroup(digest="x", size=1, paths=[Path("a/long/path.txt"), Path("short.txt")])
        to_delete = plan_deletions([group], keep="shortest-path")
        self.assertEqual(to_delete, [Path("a/long/path.txt")])


class TestApplyDeletions(unittest.TestCase):
    def test_apply_deletions_removes_files_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = write(Path(tmp) / "dup.txt", "x")
            removed = apply_deletions([f])
            self.assertEqual(removed, [f])
            self.assertFalse(f.exists())

    def test_apply_deletions_moves_to_trash_dir_instead_of_deleting(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = write(Path(tmp) / "dup.txt", "x")
            trash = Path(tmp) / "trash"
            removed = apply_deletions([f], trash_dir=trash)
            self.assertEqual(removed, [f])
            self.assertFalse(f.exists())
            self.assertTrue(any(trash.iterdir()))


if __name__ == "__main__":
    unittest.main()
