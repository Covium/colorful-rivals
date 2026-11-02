import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "scripts" / "release_notes.py"


class ReleaseNotesTests(unittest.TestCase):
    def test_first_release_tag_range_and_manual_override(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)

            def git(*args):
                subprocess.run(
                    [
                        "git",
                        "-c",
                        "user.name=Test",
                        "-c",
                        "user.email=test@example.invalid",
                        *args,
                    ],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                )

            def notes(manual=""):
                output = repo / "notes.md"
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--output", str(output)],
                    cwd=repo,
                    env={**os.environ, "RELEASE_CHANGELOG": manual},
                    check=False,
                    text=True,
                    capture_output=True,
                )
                return result, output.read_text(
                    encoding="utf-8"
                ) if result.returncode == 0 else ""

            git("init")
            git("commit", "--allow-empty", "-m", "feat: initial colors")
            result, text = notes()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(text, "- feat: initial colors\n")
            git("tag", "v1.0.0")
            git("commit", "--allow-empty", "-m", "feat: add six presets")
            git("commit", "--allow-empty", "-m", "fix: speed up selector")
            result, text = notes()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                text, "- feat: add six presets\n- fix: speed up selector\n"
            )
            git("tag", "v1.1.0")
            result, _ = notes()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("No changes found", result.stderr)
            result, text = notes("New colors.\nFaster selector.")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(text, "New colors.\nFaster selector.\n")


if __name__ == "__main__":
    unittest.main()
