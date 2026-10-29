"""Parse a restricted .env format and compare configurations in memory."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

MAX_FILE_BYTES = 5 * 1024 * 1024
KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class EnvError(Exception):
    """A safe-to-display error that never includes a configuration value."""


def _parse_value(raw: str, line_number: int) -> str:
    raw = raw.lstrip()
    if not raw:
        return ""
    if raw[0] not in ("'", '"'):
        # A hash begins a comment only when preceded by whitespace.
        for index, char in enumerate(raw):
            if char == "#" and index > 0 and raw[index - 1].isspace():
                raw = raw[:index]
                break
        return raw.rstrip()

    quote = raw[0]
    chars: list[str] = []
    pos = 1
    escapes = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\", '"': '"'}
    while pos < len(raw):
        char = raw[pos]
        if char == quote:
            tail = raw[pos + 1 :].strip()
            if tail and not tail.startswith("#"):
                raise EnvError(f"line {line_number}: unexpected text after quoted value")
            return "".join(chars)
        if quote == '"' and char == "\\":
            pos += 1
            if pos >= len(raw) or raw[pos] not in escapes:
                raise EnvError(f"line {line_number}: unsupported escape in quoted value")
            chars.append(escapes[raw[pos]])
        else:
            chars.append(char)
        pos += 1
    raise EnvError(f"line {line_number}: unterminated quoted value")


def parse_env(text: str) -> dict[str, str]:
    """Return keys and values; never include values in parsing errors."""
    result: dict[str, str] = {}
    for line_number, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"export\s+", line):
            line = re.sub(r"^export\s+", "", line, count=1)
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not KEY_PATTERN.fullmatch(key):
            raise EnvError(f"line {line_number}: invalid assignment or key")
        if key in result:
            raise EnvError(f"line {line_number}: duplicate key")
        result[key] = _parse_value(raw_value, line_number)
    return result


def read_env(path: Path) -> dict[str, str]:
    """Read at most 5 MiB, rejecting invalid UTF-8 without exposing input."""
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
    except OSError:
        raise EnvError("cannot read input file") from None
    if len(data) > MAX_FILE_BYTES:
        raise EnvError("input exceeds the 5 MiB limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise EnvError("input is not valid UTF-8") from None
    return parse_env(text)


@dataclass(frozen=True)
class Comparison:
    only_left: list[str]
    only_right: list[str]
    changed: list[str]
    unchanged: int
    left_count: int
    right_count: int

    @property
    def equal(self) -> bool:
        return not (self.only_left or self.only_right or self.changed)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": "equal" if self.equal else "different",
            "only_left": self.only_left,
            "only_right": self.only_right,
            "changed": self.changed,
            "counts": {
                "left": self.left_count,
                "right": self.right_count,
                "unchanged": self.unchanged,
            },
        }


def compare(
    left: dict[str, str],
    right: dict[str, str],
    *,
    ignored: set[str] | None = None,
    keys_only: bool = False,
) -> Comparison:
    ignored = ignored or set()
    a = set(left) - ignored
    b = set(right) - ignored
    common = a & b
    changed = sorted(k for k in common if not keys_only and left[k] != right[k])
    return Comparison(
        only_left=sorted(a - b),
        only_right=sorted(b - a),
        changed=changed,
        unchanged=len(common) - len(changed),
        left_count=len(a),
        right_count=len(b),
    )
