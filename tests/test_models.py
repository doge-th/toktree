import unittest

from toktree.models import parse_model


class TestParseModel(unittest.TestCase):
    def test_preset_name(self):
        label, window = parse_model("claude-sonnet")
        self.assertEqual(label, "claude-sonnet")
        self.assertEqual(window, 200_000)

    def test_size_suffix(self):
        self.assertEqual(parse_model("128k")[1], 128_000)
        self.assertEqual(parse_model("1m")[1], 1_000_000)
        self.assertEqual(parse_model("1M")[1], 1_000_000)

    def test_raw_count(self):
        self.assertEqual(parse_model("200000")[1], 200_000)

    def test_invalid_raises_with_hint(self):
        with self.assertRaises(ValueError) as ctx:
            parse_model("not-a-model")
        self.assertIn("unknown --model value", str(ctx.exception))

    def test_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            parse_model("0")


if __name__ == "__main__":
    unittest.main()
