"""Download and verify the pinned retoc release binary for one platform."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RELEASE_BASE = 'https://github.com/trumank/retoc/releases/download'


def member_name(name):
    parts = PurePosixPath(name.replace('\\', '/')).parts
    if not parts or any(part in ('', '.', '..') for part in parts):
        return None
    return parts[-1]


def extract_binary(archive, wanted, destination):
    found = []
    if archive.name.endswith('.zip'):
        with zipfile.ZipFile(archive) as bundle:
            for item in bundle.infolist():
                if not item.is_dir() and member_name(item.filename) == wanted:
                    found.append((item.filename, bundle.read(item)))
    else:
        with tarfile.open(archive, 'r:xz') as bundle:
            for item in bundle.getmembers():
                if item.isfile() and member_name(item.name) == wanted:
                    stream = bundle.extractfile(item)
                    if stream is not None:
                        found.append((item.name, stream.read()))
    if len(found) != 1:
        names = ', '.join(name for name, _ in found) or 'none'
        raise ValueError(f'Expected one {wanted!r} in {archive.name}; found {names}.')
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / wanted
    output.write_bytes(found[0][1])
    output.chmod(0o755)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads((ROOT / 'retoc-lock.json').read_text(encoding='utf-8'))
    try:
        item = lock['platforms'][args.platform]
    except KeyError as exc:
        raise SystemExit(f'Unknown retoc platform: {args.platform}') from exc
    url = f"{RELEASE_BASE}/v{lock['version']}/{item['asset']}"
    with tempfile.TemporaryDirectory(prefix='colorful-rivals-retoc-') as temp:
        archive = Path(temp) / item['asset']
        request = urllib.request.Request(url, headers={'User-Agent': 'Colorful-Rivals-release-builder'})
        with urllib.request.urlopen(request) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != item['sha256']:
            raise ValueError(f"retoc checksum mismatch: expected {item['sha256']}, got {actual}")
        binary = extract_binary(archive, item['executable'], args.output)
    print(binary.resolve())


if __name__ == '__main__':
    main()
