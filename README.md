# EnvParity

Compare two `.env` files by key presence and value equality without printing their values. The tool reads files locally, does not modify them, and has no runtime dependencies.

**Status:** Completed MVP (0.1.0) — SonyDev GitHub Marathon, Day 3 (October 29, 2026). This is not a stable release.

## Install

Requires Python 3.10 or later.

```sh
python -m pip install .
```

## Usage

```sh
envparity staging.env production.env
envparity staging.env production.env --keys-only
envparity staging.env production.env --ignore DATABASE_URL --json
```

Example output:

```text
Files differ.
Only in first file: DEBUG
Different values: LOG_LEVEL
Keys: 3 / 2; unchanged: 1
```

Exit codes: `0` for equal, `1` for differences, `2` for invalid input or read errors. `--json` emits `status`, sorted key-name lists (`only_left`, `only_right`, `changed`), and counts. The `counts.common` field reports keys present in both files. `counts.unchanged` reports matching values, or `null` with `--keys-only` because values were not compared. The text output uses `common keys` instead of `unchanged` in that mode. No configuration values or hashes are emitted. Key names are visible in the report. `--ignore` accepts valid key names only and may be repeated.

## Supported syntax

- `KEY=value`, `KEY=`, and `export KEY=value` assignments.
- ASCII variable names matching `[A-Za-z_][A-Za-z0-9_]*`.
- Empty lines and full-line `#` comments.
- Unquoted values, single-quoted values, and double-quoted values.
- Inline comments after unquoted values when `#` is preceded by an ASCII space or tab.
- Double-quoted escapes `\\`, `\"`, `\n`, `\r`, and `\t`.
- UTF-8 (with or without a BOM) and LF/CRLF line endings.

Duplicate keys, invalid assignments, unsupported double-quoted escapes, unterminated quotes, embedded NUL bytes, and bare carriage returns are errors. Unicode whitespace inside unquoted values is preserved; only ASCII spaces and tabs are trimmed around assignments and unquoted values. Multiline values and shell interpolation are not supported; variables are treated as literal text. Each input must be a regular file of at most 5 MiB. Values are compared as parsed strings, not expanded environment variables.

**Security:** The program never prints parsed values, even in parser errors. It reports key names and whether values match, which may itself reveal configuration metadata. Do not treat its output as an anonymized copy of the input. Source files remain unchanged. Avoid passing sensitive values as filenames or CLI arguments: argument parsing and shell diagnostics are outside the value-redaction guarantee.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Development report (2026-10-29)

Evening audit on Linux, Python 3.13.5: 50 tests passed (40 existing tests and 10 new regression tests). The new tests cover Unicode whitespace at value boundaries, comment parsing, special-file rejection, read-only behavior, and invalid keys. A wheel was built and installed locally; the installed CLI was exercised with JSON output and exit codes 0, 1, and 2.

The audit fixed a false-equality case caused by trimming Unicode whitespace from values. It also prevents blocking reads from named pipes on POSIX by opening input files in nonblocking mode and rejecting non-regular files. No GitHub Actions or external services are used.

Limitations: Windows and Python 3.10–3.12 have not been tested. The parser intentionally supports a restricted `.env` syntax, not shell evaluation. `--keys-only` does not compare values. File contents remain in process memory during comparison.
