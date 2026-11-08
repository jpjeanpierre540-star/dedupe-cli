import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dedupe_cli.cli import run


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


class TestCLI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_dry_run_deletes_nothing(self):
        a = write(self.root / "a.txt", "dup")
        b = write(self.root / "b.txt", "dup")
        code = run([str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue(a.exists())
        self.assertTrue(b.exists())

    def test_json_output_is_valid_and_correct(self, capsys=None):
        write(self.root / "a.txt", "dup")
        write(self.root / "b.txt", "dup")
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run([str(self.root), "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["duplicate_groups"], 1)
        self.assertEqual(payload["redundant_files"], 1)
        self.assertFalse(payload["applied"])

    def test_apply_actually_deletes_the_redundant_copy(self):
        a = write(self.root / "a.txt", "dup")
        b = write(self.root / "b.txt", "dup")
        run([str(self.root), "--apply"])
        # Exactly one of the two survives (order of traversal picks "first").
        self.assertEqual(a.exists() + b.exists(), 1)

    def test_nonexistent_path_returns_error_code(self):
        code = run([str(self.root / "does_not_exist")])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
