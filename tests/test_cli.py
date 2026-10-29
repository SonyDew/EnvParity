import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from envparity.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.left = Path(self.temp.name) / "left.env"
        self.right = Path(self.temp.name) / "right.env"
        self.left.write_text("TOKEN=super-secret-123\nDEBUG=1\n", encoding="utf-8")
        self.right.write_text("TOKEN=another-secret-456\nLOG=info\n", encoding="utf-8")

    def run_cli(self, *options):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main([str(self.left), str(self.right), *options])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_differences_and_no_values(self):
        status, out, err = self.run_cli()
        self.assertEqual(status, 1)
        self.assertIn("TOKEN", out)
        self.assertIn("DEBUG", out)
        self.assertIn("LOG", out)
        self.assertNotIn("super-secret-123", out + err)
        self.assertNotIn("another-secret-456", out + err)

    def test_json(self):
        status, out, _ = self.run_cli("--json")
        self.assertEqual(status, 1)
        data = json.loads(out)
        self.assertEqual(data["changed"], ["TOKEN"])
        self.assertEqual(data["only_left"], ["DEBUG"])

    def test_keys_only(self):
        status, out, _ = self.run_cli("--keys-only")
        self.assertEqual(status, 1)
        self.assertNotIn("Different values", out)

    def test_ignore(self):
        self.left.write_text("TOKEN=one", encoding="utf-8")
        self.right.write_text("TOKEN=two", encoding="utf-8")
        status, out, _ = self.run_cli("--ignore", "TOKEN")
        self.assertEqual(status, 0)
        self.assertIn("Files match", out)

    def test_invalid_input_hides_secret(self):
        self.left.write_text('TOKEN="secret-should-not-appear', encoding="utf-8")
        status, out, err = self.run_cli()
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertNotIn("secret-should-not-appear", err)

    def test_read_only(self):
        before = self.left.read_bytes(), self.right.read_bytes()
        self.run_cli()
        self.assertEqual(before, (self.left.read_bytes(), self.right.read_bytes()))

    def test_equal(self):
        self.right.write_bytes(self.left.read_bytes())
        status, out, _ = self.run_cli()
        self.assertEqual(status, 0)
        self.assertIn("Files match", out)


if __name__ == "__main__":
    unittest.main()

class AuditCliRegressionTests(unittest.TestCase):
    setUp = CliTests.setUp
    run_cli = CliTests.run_cli

    def test_invalid_ignore_name_does_not_echo_value(self):
        status, out, err = self.run_cli("--ignore", "secret-bad-key")
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIn("invalid --ignore key", err)
        self.assertNotIn("secret-bad-key", err)

    def test_keys_only_counts_do_not_claim_value_comparison(self):
        self.left.write_text("TOKEN=one", encoding="utf-8")
        self.right.write_text("TOKEN=two", encoding="utf-8")
        status, out, err = self.run_cli("--keys-only", "--json")
        self.assertEqual(status, 0)
        counts = json.loads(out)["counts"]
        self.assertEqual(counts["common"], 1)
        self.assertIsNone(counts["unchanged"])
        self.assertEqual(err, "")

    def test_unicode_separator_does_not_add_key(self):
        self.left.write_text("TOKEN=secret\u2028EXTRA=1", encoding="utf-8")
        self.right.write_text("TOKEN=secret", encoding="utf-8")
        status, out, err = self.run_cli("--json")
        self.assertEqual(status, 1)
        data = json.loads(out)
        self.assertEqual(data["changed"], ["TOKEN"])
        self.assertEqual(data["only_left"], [])
        self.assertEqual(err, "")
