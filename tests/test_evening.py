import os
import tempfile
import unittest
from pathlib import Path

from envparity.core import EnvError, compare, parse_env, read_env


class EveningAuditTests(unittest.TestCase):
    def test_trailing_unicode_separator_is_significant(self):
        self.assertEqual(parse_env("TOKEN=secret\u2028"), {"TOKEN": "secret\u2028"})
        self.assertEqual(compare(parse_env("TOKEN=secret\u2028"), parse_env("TOKEN=secret")).changed, ["TOKEN"])

    def test_leading_unicode_whitespace_is_significant(self):
        self.assertEqual(parse_env("TOKEN=\u00a0secret"), {"TOKEN": "\u00a0secret"})

    def test_unicode_whitespace_before_hash_is_not_a_comment(self):
        self.assertEqual(parse_env("TOKEN=secret\u2028#suffix"), {"TOKEN": "secret\u2028#suffix"})

    def test_ascii_whitespace_still_trims(self):
        self.assertEqual(parse_env("  export\tTOKEN = \tvalue \t # comment  "), {"TOKEN": "value"})

    def test_unicode_whitespace_after_quote_is_rejected(self):
        with self.assertRaisesRegex(EnvError, "unexpected text"):
            parse_env('TOKEN="secret"\u2028')

    def test_unicode_whitespace_in_export_prefix_is_rejected(self):
        with self.assertRaisesRegex(EnvError, "invalid assignment"):
            parse_env("export\u00a0TOKEN=secret")

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"), "POSIX FIFO required")
    def test_fifo_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / "input.env"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(EnvError, "not a regular file"):
                read_env(fifo)

    def test_directory_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(EnvError):
                read_env(Path(directory))

    def test_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            left = Path(directory) / "left.env"
            left.write_bytes(b"TOKEN=secret\n")
            before = left.read_bytes()
            read_env(left)
            self.assertEqual(left.read_bytes(), before)

    def test_non_ascii_in_key_rejected(self):
        with self.assertRaisesRegex(EnvError, "invalid assignment"):
            parse_env("T\u00d6KEN=secret")
