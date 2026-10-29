import tempfile
import unittest
from pathlib import Path

from envparity.core import EnvError, MAX_FILE_BYTES, compare, parse_env, read_env


class ParseTests(unittest.TestCase):
    def test_basics(self):
        self.assertEqual(parse_env("# hi\n A = hello  \nexport B=\n"), {"A": "hello", "B": ""})

    def test_hash_inside_value(self):
        self.assertEqual(parse_env("A=a#b\nB=hello # comment\nC='# literal'"), {"A": "a#b", "B": "hello", "C": "# literal"})

    def test_double_quoted_escapes(self):
        self.assertEqual(parse_env(r'A="a\n\"b\\c"'), {"A": 'a\n"b\\c'})

    def test_single_quoted_backslash_is_literal(self):
        self.assertEqual(parse_env(r"A='a\nb'"), {"A": r"a\nb"})

    def test_quoted_comment(self):
        self.assertEqual(parse_env('A="hello"  # comment'), {"A": "hello"})

    def test_duplicate(self):
        with self.assertRaisesRegex(EnvError, "duplicate key"):
            parse_env("A=1\nA=2")

    def test_invalid_key(self):
        with self.assertRaisesRegex(EnvError, "invalid assignment"):
            parse_env("A-B=1")

    def test_missing_equals(self):
        with self.assertRaises(EnvError):
            parse_env("secret-value")

    def test_unterminated_quote(self):
        with self.assertRaisesRegex(EnvError, "unterminated"):
            parse_env('A="secret')

    def test_trailing_text(self):
        with self.assertRaisesRegex(EnvError, "unexpected text"):
            parse_env('A="value"suffix')

    def test_bad_escape(self):
        with self.assertRaisesRegex(EnvError, "unsupported escape"):
            parse_env(r'A="hello\q"')

    def test_multiline_rejected(self):
        with self.assertRaises(EnvError):
            parse_env('A="first\nsecond"')

    def test_export_key_without_prefix(self):
        self.assertEqual(parse_env("export=ok"), {"export": "ok"})

    def test_bom_and_crlf(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.env"
            path.write_bytes(b"\xef\xbb\xbfA=1\r\nB=2\r\n")
            self.assertEqual(read_env(path), {"A": "1", "B": "2"})

    def test_invalid_utf8(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.env"
            path.write_bytes(b"A=\xff")
            with self.assertRaisesRegex(EnvError, "UTF-8"):
                read_env(path)

    def test_file_size_limit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "a.env"
            path.write_bytes(b"A=" + b"x" * MAX_FILE_BYTES)
            with self.assertRaisesRegex(EnvError, "5 MiB"):
                read_env(path)

    def test_missing_file(self):
        with self.assertRaisesRegex(EnvError, "cannot read"):
            read_env(Path("/nonexistent/envparity-test-missing.env"))


class CompareTests(unittest.TestCase):
    def test_equal(self):
        result = compare({"A": "1"}, {"A": "1"})
        self.assertTrue(result.equal)
        self.assertEqual(result.as_dict()["status"], "equal")

    def test_difference_and_order(self):
        result = compare({"Z": "1", "B": "2", "A": "1"}, {"B": "3", "C": "4"})
        self.assertEqual(result.only_left, ["A", "Z"])
        self.assertEqual(result.only_right, ["C"])
        self.assertEqual(result.changed, ["B"])

    def test_ignore(self):
        result = compare({"A": "secret", "B": "ok"}, {"A": "other", "B": "ok"}, ignored={"A"})
        self.assertTrue(result.equal)
        self.assertEqual(result.left_count, 1)

    def test_keys_only(self):
        self.assertTrue(compare({"A": "1"}, {"A": "2"}, keys_only=True).equal)

    def test_empty_value_differs(self):
        self.assertEqual(compare({"A": ""}, {"A": "x"}).changed, ["A"])


if __name__ == "__main__":
    unittest.main()

class AuditRegressionTests(unittest.TestCase):
    def test_unicode_line_separator_stays_in_value(self):
        parsed = parse_env("TOKEN=one\u2028ADMIN=enabled\nOTHER=ok")
        self.assertEqual(parsed, {"TOKEN": "one\u2028ADMIN=enabled", "OTHER": "ok"})

    def test_unicode_next_line_stays_in_value(self):
        self.assertEqual(parse_env("TOKEN=one\u0085ADMIN=enabled"), {"TOKEN": "one\u0085ADMIN=enabled"})

    def test_raw_carriage_return_is_not_a_record_separator(self):
        with self.assertRaisesRegex(EnvError, "control character"):
            parse_env("TOKEN=one\rADMIN=enabled")

    def test_raw_nul_rejected_without_leaking_value(self):
        with self.assertRaises(EnvError) as context:
            parse_env("TOKEN=secret\x00value")
        self.assertNotIn("secret", str(context.exception))

    def test_crlf_remains_supported(self):
        self.assertEqual(parse_env("A=1\r\nB=2\r\n"), {"A": "1", "B": "2"})

    def test_keys_only_does_not_claim_values_unchanged(self):
        result = compare({"A": "secret-one"}, {"A": "secret-two"}, keys_only=True)
        counts = result.as_dict()["counts"]
        self.assertEqual(counts["common"], 1)
        self.assertIsNone(counts["unchanged"])

    def test_value_comparison_counts_common_and_unchanged(self):
        result = compare({"A": "1", "B": "2"}, {"A": "1", "B": "3"})
        counts = result.as_dict()["counts"]
        self.assertEqual(counts["common"], 2)
        self.assertEqual(counts["unchanged"], 1)
