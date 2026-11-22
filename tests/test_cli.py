import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from toktree import __version__
from toktree.cli import main


class TestCli(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "a.txt").write_text("hello world")
        (self.root / "b.txt").write_text("你好世界")
        self.sub = self.root / "sub"
        self.sub.mkdir()
        (self.sub / "c.py").write_text("x = 1\n")

    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_json_report(self):
        code, out, _ = self._run(["--json", str(self.root)])
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual(doc["tool"], "toktree")
        self.assertEqual(doc["version"], __version__)
        self.assertEqual(doc["files"], 3)
        self.assertGreater(doc["total_tokens"], 0)
        self.assertEqual(len(doc["all_files"]), 3)
        self.assertIn("claude-sonnet", doc["fit"])

    def test_table_report_mentions_sections(self):
        _, out, _ = self._run([str(self.root)])
        for section in ("Summary", "Will it fit?", "Largest files",
                        "By directory", "By type"):
            self.assertIn(section, out)
        self.assertIn("a.txt", out)

    def test_markdown_report_is_markdown(self):
        _, out, _ = self._run(["--markdown", str(self.root)])
        self.assertIn("## toktree", out)
        self.assertIn("| model | window | used | verdict |", out)
        self.assertIn("✅ fits", out)

    def test_single_file_mode(self):
        _, out, _ = self._run(["--json", str(self.root / "a.txt")])
        doc = json.loads(out)
        self.assertEqual(doc["files"], 1)

    def test_single_nested_file_mode(self):
        _, out, _ = self._run(["--json", str(self.sub / "c.py")])
        doc = json.loads(out)
        self.assertEqual(doc["files"], 1)
        self.assertEqual(doc["all_files"][0]["path"], "c.py")

    def test_missing_path_fails_cleanly(self):
        code, _, err = self._run(["/nonexistent/definitely-missing"])
        self.assertEqual(code, 1)
        self.assertIn("no such file or directory", err)

    def test_custom_model_flag(self):
        _, out, _ = self._run(["--json", "--model", "64k", str(self.root)])
        doc = json.loads(out)
        self.assertIn("64k", doc["fit"])
        self.assertEqual(doc["fit"]["64k"]["window_tokens"], 64_000)

    def test_model_rejects_garbage(self):
        code, _, err = self._run(["--json", "--model", "bogus", str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn("unknown --model value", err)

    def test_version_flag(self):
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
