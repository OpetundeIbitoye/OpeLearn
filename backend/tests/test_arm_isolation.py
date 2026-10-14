"""The arm identifier may only be interpreted inside the conditions slice."""

import pathlib
import re

ALLOWED = {"app/conditions/", "tests/"}
PATTERN = re.compile(r"[\"']A[123][\"']")


def test_no_arm_literals_outside_conditions() -> None:
    offenders = []
    for file in pathlib.Path("app").rglob("*.py"):
        if any(allowed in str(file) for allowed in ALLOWED):
            continue
        for line_number, line in enumerate(file.read_text().splitlines(), 1):
            if PATTERN.search(line) and not line.strip().startswith("#"):
                offenders.append(f"{file}:{line_number}: {line.strip()}")
    assert not offenders, "arm literals outside conditions/:\n" + "\n".join(offenders)
