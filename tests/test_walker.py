import subprocess
import tempfile
import unittest
from pathlib import Path

from toktree.walker import discover_files


class TestFallbackWalk(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "a.py").write_text("print('hi')\n")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "b.md").write_text("# doc\n")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "x.js").write_text("var x;\n")
        (self.root / "logo.png").write_bytes(b"\x89PNG fake")

    def test_excludes_noise_dirs_and_binary_exts(self):
        files = {f.relative_to(self.root).as_posix()
                 for f in discover_files(self.root)}
        self.assertIn("a.py", files)
        self.assertIn("sub/b.md", files)
        self.assertNotIn("node_modules/x.js", files)
        self.assertNotIn("logo.png", files)

    def test_extra_exclude_glob(self):
        files = {f.relative_to(self.root).as_posix()
                 for f in discover_files(self.root, extra_excludes=["sub/**"])}
        self.assertNotIn("sub/b.md", files)
        self.assertIn("a.py", files)


class TestGitAware(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "a.py").write_text("x = 1\n")
        (self.root / "keep.txt").write_text("keep\n")
        (self.root / "drop.log").write_text("noise\n")
        (self.root / ".gitignore").write_text("*.log\n")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True,
                       capture_output=True)

    def test_respects_gitignore(self):
        files = {f.relative_to(self.root).as_posix()
                 for f in discover_files(self.root)}
        self.assertIn("a.py", files)
        self.assertIn("keep.txt", files)
        self.assertNotIn("drop.log", files)

    def test_no_ignore_walks_everything(self):
        files = {f.relative_to(self.root).as_posix()
                 for f in discover_files(self.root, no_ignore=True)}
        self.assertIn("drop.log", files)


if __name__ == "__main__":
    unittest.main()
