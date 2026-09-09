"""Run the hidden integrity check in a packaged application."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path, required=True)
    args = parser.parse_args()
    payload = args.payload.resolve()
    if payload.suffix == '.app':
        executable = payload / 'Contents' / 'MacOS' / payload.stem
    else:
        executable = payload
    if not executable.is_file():
        raise FileNotFoundError(executable)
    result = subprocess.run([str(executable), '--self-test'], timeout=60)
    if result.returncode:
        raise SystemExit(f'Packaged application self-test failed with exit code {result.returncode}.')
    print(f'Packaged application verified: {payload}')


if __name__ == '__main__':
    main()
