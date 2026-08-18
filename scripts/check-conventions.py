#!/usr/bin/env python3
"""Convention checks for the bilingual ESPHome config layout.

`esphome config` only ever sees one language at a time, so it cannot catch the
defects this repository is most prone to: a label key added to one language but
not the other, a `${lbl_*}` reference with no definition, a `!secret` key that
is missing from the seedable example, or a real secrets file slipping into git.

Runs on a stock Python 3 (no third-party modules), so it works both in CI and
from a plain checkout.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LABEL_REF = re.compile(r"\$\{(lbl_[A-Za-z0-9_]+)\}")
SECRET_REF = re.compile(r"!secret\s+([A-Za-z0-9_]+)")
UNQUOTED_LABEL_NAME = re.compile(r"^\s*name:\s*\$\{lbl_")
TOP_LEVEL_KEY = re.compile(r"^([A-Za-z0-9_]+):")
INDENTED_KEY = re.compile(r"^  ([A-Za-z0-9_]+):")


@dataclass(frozen=True)
class Problem:
    level: str  # "error" or "warning"
    path: Path
    line: int
    message: str


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def parse_substitutions(path: Path) -> dict[str, int]:
    """Return the keys of the top-level `substitutions:` block and their lines.

    A hand-rolled parser keeps the script dependency-free; the repository
    mandates a flat, 2-space-indented substitutions block, so this is enough.
    """
    keys: dict[str, int] = {}
    inside = False
    for number, line in enumerate(read_lines(path), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("substitutions:"):
            inside = True
            continue
        if inside:
            if not line.startswith(" "):
                break
            match = INDENTED_KEY.match(line)
            if match:
                keys[match.group(1)] = number
    return keys


def check_labels(problems: list[Problem]) -> None:
    languages = sorted(p.name for p in (ROOT / "labels").iterdir() if p.is_dir())
    devices = sorted(p.parent.name for p in ROOT.glob("packages/*/logic.yaml"))

    for device in devices:
        logic = ROOT / "packages" / device / "logic.yaml"
        referenced: dict[str, int] = {}
        for number, line in enumerate(read_lines(logic), start=1):
            for key in LABEL_REF.findall(line):
                referenced.setdefault(key, number)

        defined: dict[str, dict[str, int]] = {}
        for language in languages:
            pack = ROOT / "labels" / language / f"{device}.yaml"
            if not pack.is_file():
                problems.append(
                    Problem("error", pack, 1, f"missing label pack for '{device}'")
                )
                continue
            defined[language] = parse_substitutions(pack)

        for language, keys in defined.items():
            pack = ROOT / "labels" / language / f"{device}.yaml"
            for key, number in sorted(referenced.items(), key=lambda kv: kv[1]):
                if key not in keys:
                    problems.append(
                        Problem(
                            "error",
                            logic,
                            number,
                            f"${{{key}}} is not defined in {rel(pack)}",
                        )
                    )
            for key, number in sorted(keys.items(), key=lambda kv: kv[1]):
                if key not in referenced:
                    problems.append(
                        Problem(
                            "warning",
                            pack,
                            number,
                            f"{key} is never referenced in {rel(logic)}",
                        )
                    )

        # Key sets must be identical across languages, even for keys the logic
        # does not reference (yet) — a one-sided key is a translation gap.
        for language, keys in defined.items():
            for other, other_keys in defined.items():
                if language == other:
                    continue
                pack = ROOT / "labels" / language / f"{device}.yaml"
                other_pack = ROOT / "labels" / other / f"{device}.yaml"
                for key, number in sorted(keys.items(), key=lambda kv: kv[1]):
                    if key not in other_keys:
                        problems.append(
                            Problem(
                                "error",
                                pack,
                                number,
                                f"{key} has no counterpart in {rel(other_pack)}",
                            )
                        )

    for pack in sorted(ROOT.glob("labels/*/*.yaml")):
        if pack.stem not in devices:
            problems.append(
                Problem(
                    "error",
                    pack,
                    1,
                    f"no packages/{pack.stem}/logic.yaml for this label pack",
                )
            )


def check_secrets(problems: list[Problem]) -> None:
    example = ROOT / "secrets.yaml.example"
    documented = {
        match.group(1)
        for line in read_lines(example)
        if (match := TOP_LEVEL_KEY.match(line))
    }

    for path in sorted(ROOT.glob("**/*.yaml")):
        if path.name == "secrets.yaml" or ".git" in path.parts:
            continue
        for number, line in enumerate(read_lines(path), start=1):
            # A commented-out `!secret` is a copy-paste template rather than a
            # live reference, so a stale key there is worth a nudge, not a fail.
            level = "warning" if line.lstrip().startswith("#") else "error"
            for key in SECRET_REF.findall(line):
                if key not in documented:
                    problems.append(
                        Problem(
                            level,
                            path,
                            number,
                            f"!secret {key} is missing from secrets.yaml.example",
                        )
                    )

    tracked = subprocess.run(
        ["git", "ls-files", "*secrets.yaml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for name in tracked.stdout.split():
        problems.append(
            Problem("error", ROOT / name, 1, "a real secrets file must not be tracked")
        )


def check_quoting(problems: list[Problem]) -> None:
    for path in sorted(ROOT.glob("**/*.yaml")):
        if ".git" in path.parts:
            continue
        for number, line in enumerate(read_lines(path), start=1):
            if UNQUOTED_LABEL_NAME.match(line):
                problems.append(
                    Problem(
                        "error",
                        path,
                        number,
                        'substituted name must be quoted: name: "${...}"',
                    )
                )


def report(problems: list[Problem]) -> int:
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    errors = [p for p in problems if p.level == "error"]
    warnings = [p for p in problems if p.level == "warning"]

    for problem in warnings + errors:
        print(f"{problem.level.upper():7} {rel(problem.path)}:{problem.line}: {problem.message}")
        if in_actions:
            print(
                f"::{problem.level} file={rel(problem.path)},"
                f"line={problem.line}::{problem.message}"
            )

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


def main() -> int:
    problems: list[Problem] = []
    check_labels(problems)
    check_secrets(problems)
    check_quoting(problems)
    return report(problems)


if __name__ == "__main__":
    sys.exit(main())
