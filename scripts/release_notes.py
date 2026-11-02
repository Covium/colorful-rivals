"""Generate release notes from commit subjects since the previous reachable tag."""

import argparse
import os
import subprocess
from pathlib import Path


def git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()


def generate_notes(target="HEAD"):
    target = git("rev-parse", "--verify", f"{target}^{{commit}}")
    tags = git("tag", "--merged", target)
    previous = git("describe", "--tags", "--abbrev=0", target) if tags else None
    revision = f"{previous}..{target}" if previous else target
    subjects = git(
        "log", "--reverse", "--no-merges", "--format=%s", revision
    ).splitlines()
    if not subjects:
        raise ValueError(
            "No changes found since the previous tag. Enter a manual changelog."
        )
    return "\n".join(f"- {subject}" for subject in subjects) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", default="HEAD")
    args = parser.parse_args()
    manual = os.environ.get("RELEASE_CHANGELOG", "")
    notes = manual.rstrip() + "\n" if manual.strip() else generate_notes(args.target)
    args.output.write_text(notes, encoding="utf-8")


if __name__ == "__main__":
    main()
