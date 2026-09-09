"""Download and verify license texts for components embedded by PyInstaller."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'licenses')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / 'runtime-licenses-lock.json').read_text(encoding='utf-8'))
    for name, item in lock.items():
        request = urllib.request.Request(item['url'], headers={'User-Agent': 'Colorful-Rivals-release-builder'})
        with urllib.request.urlopen(request) as response:
            content = response.read()
        actual = hashlib.sha256(content).hexdigest()
        if actual != item['sha256']:
            raise ValueError(f'License checksum mismatch for {name}: expected {item["sha256"]}, got {actual}')
        destination = args.output / name
        destination.write_bytes(content)
        print(destination.resolve())


if __name__ == '__main__':
    main()
