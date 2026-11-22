import tempfile
import unittest
from pathlib import Path

from toktree.estimator import estimate_file, estimate_text, heuristic_tokens


class TestHeuristic(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(heuristic_tokens(""), 0)

    def test_ascii(self):
        # ~4 chars per token for ASCII
        self.assertEqual(heuristic_tokens("hello world"), 3)

    def test_cjk_one_token_per_char(self):
        self.assertEqual(heuristic_tokens("你好世界"), 4)

    def test_kana_is_cheaper_than_ideographs(self):
        self.assertLess(heuristic_tokens("カタカナ"), 4)

    def test_emoji_counts_at_least_one(self):
        self.assertGreaterEqual(heuristic_tokens("👍"), 1)

    def test_longer_ascii_is_roughly_chars_over_four(self):
        text = "def add(a, b):\n    return a + b\n" * 100
        est = heuristic_tokens(text)
        expected = len(text) / 4
        self.assertAlmostEqual(est, expected, delta=expected * 0.05)

    def test_estimate_text_dispatch(self):
        self.assertEqual(estimate_text("hello world", "heuristic"),
                         heuristic_tokens("hello world"))


class TestEstimateFile(unittest.TestCase):
    def _tmp(self, data: bytes) -> Path:
        f = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        f.write(data)
        f.close()
        return Path(f.name)

    def test_text_file(self):
        p = self._tmp("hello world".encode())
        self.assertGreater(estimate_file(p), 0)
        p.unlink()

    def test_binary_sniff(self):
        p = self._tmp(b"PK\x03\x04\x00\x00\x00\x00rest")
        self.assertIsNone(estimate_file(p))
        p.unlink()

    def test_missing_file(self):
        self.assertIsNone(estimate_file(Path("/nonexistent/nope.txt")))

    def test_invalid_utf8_does_not_crash(self):
        p = self._tmp(b"\xff\xfe hello caf\xe9")
        self.assertGreater(estimate_file(p), 0)
        p.unlink()


if __name__ == "__main__":
    unittest.main()
