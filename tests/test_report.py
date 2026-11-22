import unittest

from toktree.report import (FileEntry, ScanResult, bar, fmt_size, fmt_tokens,
                            fmt_window)


def _res():
    r = ScanResult(root="/tmp/x", estimator="heuristic")
    r.files = [
        FileEntry("src/main.py", 1000, 4000),
        FileEntry("src/util.py", 500, 2000),
        FileEntry("docs/guide.md", 300, 1200),
        FileEntry("README.md", 200, 800),
    ]
    r.total_tokens = 2000
    r.total_size = 8000
    return r


class TestFormatters(unittest.TestCase):
    def test_fmt_tokens(self):
        self.assertEqual(fmt_tokens(999), "999")
        self.assertEqual(fmt_tokens(12_345), "12.3k")
        self.assertEqual(fmt_tokens(1_500_000), "1.50M")

    def test_fmt_window(self):
        self.assertEqual(fmt_window(128_000), "128k")
        self.assertEqual(fmt_window(1_000_000), "1M")
        self.assertEqual(fmt_window(64), "64")

    def test_fmt_size(self):
        self.assertEqual(fmt_size(500), "500 B")
        self.assertEqual(fmt_size(2048), "2.0 KB")

    def test_bar_clamps(self):
        self.assertEqual(bar(2.0), "█" * 16)
        self.assertEqual(bar(-1), "░" * 16)
        self.assertEqual(bar(0.5, width=10), "█████░░░░░")


class TestAggregation(unittest.TestCase):
    def test_by_type(self):
        res = _res()
        by_type = res.by_type()
        self.assertEqual(by_type[0], (".py", 1500, 2))
        self.assertEqual(by_type[1], (".md", 500, 2))

    def test_by_dir(self):
        res = _res()
        self.assertEqual(res.by_dir()[0], ("src", 1500))
        self.assertEqual(res.by_dir()[-1], ("(root)", 200))


if __name__ == "__main__":
    unittest.main()
