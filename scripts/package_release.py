"""Create platform, all-platform, and preset release archives."""
import argparse
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = {
    'windows-x86_64': 'Windows x86_64',
    'linux-x86_64': 'Linux x86_64',
    'linux-aarch64': 'Linux ARM64',
    'macos-x86_64': 'macOS Intel',
    'macos-aarch64': 'macOS Apple Silicon',
}


def add_tree(archive, source, prefix=''):
    source = Path(source)
    for path in sorted(source.rglob('*')):
        if path.is_file():
            archive.write(path, str(Path(prefix) / path.relative_to(source)))


def extract_zip(source, destination):
    with zipfile.ZipFile(source) as archive:
        for item in archive.infolist():
            target = destination / item.filename
            resolved = target.resolve()
            if not resolved.is_relative_to(destination.resolve()):
                raise ValueError(f'Unsafe archive member: {item.filename}')
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
            mode = item.external_attr >> 16
            if mode:
                target.chmod(stat.S_IMODE(mode))


def supporting_files(destination):
    shutil.copy2(ROOT / 'README.md', destination / 'README.md')
    shutil.copy2(ROOT / 'LICENSE', destination / 'LICENSE')
    shutil.copy2(ROOT / 'THIRD_PARTY_NOTICES.md', destination / 'THIRD_PARTY_NOTICES.md')
    shutil.copytree(ROOT / 'licenses', destination / 'licenses')


def platform_archive(platform, payload, output, version):
    with tempfile.TemporaryDirectory(prefix='colorful-rivals-package-') as temp:
        staging = Path(temp) / 'contents'
        staging.mkdir()
        target = staging / payload.name
        if payload.is_dir():
            shutil.copytree(payload, target)
        else:
            shutil.copy2(payload, target)
        supporting_files(staging)
        destination = output / f'Colorful-Rivals-{platform}-{version}.zip'
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            add_tree(archive, staging)
    print(destination)


def combined_archive(input_dir, output, version):
    with tempfile.TemporaryDirectory(prefix='colorful-rivals-combined-') as temp:
        staging = Path(temp) / 'Colorful Rivals'
        staging.mkdir()
        for platform, label in PLATFORMS.items():
            source = input_dir / f'Colorful-Rivals-{platform}-{version}.zip'
            if not source.is_file():
                raise FileNotFoundError(source)
            extract_zip(source, staging / label)
        supporting_files(staging)
        destination = output / f'Colorful-Rivals-All-Platforms-{version}.zip'
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            add_tree(archive, staging.parent)
    print(destination)


def presets_archive(output, version):
    destination = output / f'Colorful-Rivals-Vibrant-Preset-{version}.zip'
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        add_tree(archive, ROOT / 'presets')
    print(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--platform', choices=PLATFORMS)
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--combine', type=Path)
    parser.add_argument('--presets', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    selected = sum((bool(args.platform), bool(args.combine), args.presets))
    if selected != 1 or bool(args.platform) != bool(args.payload):
        parser.error('Choose exactly one of --platform/--payload, --combine, or --presets.')
    if args.platform:
        platform_archive(args.platform, args.payload.resolve(), args.output, args.version)
    elif args.combine:
        combined_archive(args.combine.resolve(), args.output, args.version)
    else:
        presets_archive(args.output, args.version)


if __name__ == '__main__':
    main()
