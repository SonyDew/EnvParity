# EnvParity

Compare two `.env` files by key presence and value equality without printing their values. The tool reads files locally, does not modify them, and has no runtime dependencies.

**Status:** In Development — SonyDev GitHub Marathon, Day 3 (October 29, 2026).

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
- Inline comments after unquoted values when `#` is preceded by whitespace.
- Double-quoted escapes `\\`, `\"`, `\n`, `\r`, and `\t`.
- UTF-8 (with or without a BOM) and LF/CRLF line endings.

Duplicate keys, invalid assignments, unsupported double-quoted escapes, unterminated quotes, embedded NUL bytes, and bare carriage returns are errors. Unicode line separators inside values are not treated as record boundaries. Multiline values and shell interpolation are not supported; variables are treated as literal text. Each input is limited to 5 MiB. Values are compared as parsed strings, not expanded environment variables.

**Security:** The program never prints parsed values, even in parser errors. It reports key names and whether values match, which may itself reveal configuration metadata. Do not treat its output as an anonymized copy of the input. Source files remain unchanged.

## Tests

```sh
python -m unittest discover -s tests -v
```

Day 3 afternoon audit (Python 3.13.5, Linux): 39 unit tests passed. A wheel was built and the CLI was exercised with equal, different, keys-only, JSON, and invalid-ignore cases. Windows and other Python versions have not been tested in this audit.

No GitHub Actions or external services are required.
