"""Build TXR rival colors from a verified, immutable local asset template."""
import argparse
import colorsys
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import sys
from paths import resolve_game, resolve_retoc, find_games
from datetime import datetime
from pathlib import Path

RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)).resolve()
if getattr(sys, 'frozen', False):
    executable = Path(sys.executable).resolve()
    if sys.platform == 'darwin' and executable.parent.name == 'MacOS':
        executable_directory = executable.parents[3]
    else:
        executable_directory = executable.parent
    default_data_root = executable_directory / 'Colorful Rivals Data'
else:
    default_data_root = RESOURCE_ROOT
DATA_ROOT = Path(os.environ.get('COLORFUL_RIVALS_DATA_DIR', default_data_root)).resolve()
# Kept for source-tree tests and third-party scripts written for earlier builds.
ROOT = RESOURCE_ROOT
NAME = 'RivalColors_Config_P'
KEYS = {'player', 'none', 'incomplete', 'complete', 'encount'}
# Unknown_None and atlas column 1 appear unused in gameplay. Keep their mapping
# in the template, but do not expose or alter them until their purpose is known.
STATE_KEYS = {'unknown_rumer': 'player', 'unknown_none': None}
KINDS = ['player', None] + ['none', 'incomplete', 'complete', 'encount'] * 3


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb(value):
    if not isinstance(value, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise ValueError(f'Expected #RRGGBB or null, got {value!r}')
    return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))


def linear(value):
    def channel(v):
        v /= 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return tuple(channel(v) for v in rgb(value))


def read_config(path):
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(config, dict) or set(config) != {'colors'}:
        raise ValueError('Configuration must contain colors only.')
    if not isinstance(config['colors'], dict) or set(config['colors']) != KEYS:
        raise ValueError('Keep all five color keys; use null to retain an original color.')
    for value in config['colors'].values():
        if value is not None:
            rgb(value)
    return config


def verify_template():
    spec = json.loads((RESOURCE_ROOT / 'asset-map.json').read_text())
    for relative, expected in spec['hashes'].items():
        if digest(RESOURCE_ROOT / 'template' / relative) != expected:
            raise ValueError(f'Original template changed: {relative}. Restore the original template.')
    return spec


def decode565(value):
    return ((value >> 11) * 255 / 31, ((value >> 5) & 63) * 255 / 63,
            (value & 31) * 255 / 31)


def encode565(color):
    return (round(color[0] * 31 / 255) << 11) | (round(color[1] * 63 / 255) << 5) | round(color[2] * 31 / 255)


def is_marker(color, kind):
    # Select the original marker color, not the red background of the lower row.
    r, g, b = color
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v <= .08:
        return False
    if s <= .25:
        return False
    if kind == 'encount':
        return (h > .97 or h < .01) and b > r * .15 and b > g * .7
    bounds = {'player': (.045, .10), 'none': (.53, .67),
              'incomplete': (.10, .20), 'complete': (.32, .48)}
    lo, hi = bounds[kind]
    return lo <= h <= hi


def patch_texture(original, texture, config):
    result = bytearray(original)
    width, height, start = texture['width'], texture['height'], texture['offset']
    counts = [0] * 14
    for by in range(height // 4):
        for bx in range(width // 4):
            col = bx * 4 // (width // 14)
            key = KINDS[col]
            value = config['colors'].get(key) if key is not None else None
            if value is None:
                continue
            target = rgb(value)
            block = start + (by * (width // 4) + bx) * 16
            for endpoint in (block + 8, block + 10):
                old = struct.unpack_from('<H', original, endpoint)[0]
                color = decode565(old)
                if not is_marker(color, KINDS[col]):
                    continue
                brightness = max(color) / 255
                new = encode565(tuple(v * brightness for v in target))
                struct.pack_into('<H', result, endpoint, new)
                counts[col] += old != new
    # BC3 alpha bytes and color-selection indices remain exactly as authored.
    for block in range(start, start + texture['size'], 16):
        if result[block:block+8] != original[block:block+8] or result[block+12:block+16] != original[block+12:block+16]:
            raise ValueError('Texture alpha or indices changed unexpectedly.')
    return bytes(result), counts


def make_chunks(config, spec, destination):
    shutil.copytree(RESOURCE_ROOT / 'template', destination)
    chunks = destination / 'chunks'
    for state, style in spec['styles'].items():
        key = STATE_KEYS.get(state, state)
        value = config['colors'].get(key) if key is not None else None
        if value is None:
            continue
        path = chunks / style['chunk']
        data = bytearray(path.read_bytes())
        struct.pack_into('<3f', data, style['offset'], *linear(value))
        path.write_bytes(data)
    widget = chunks / spec['widget']['chunk']
    data = bytearray(widget.read_bytes())
    for track in spec['widget']['tracks']:
        key = STATE_KEYS.get(track['state'], track['state'])
        value = config['colors'].get(key) if key is not None else None
        if value is not None:
            channels = linear(value)
            for offset, channel in track['offsets']:
                struct.pack_into('<f', data, offset, channels[channel])
    widget.write_bytes(data)
    report = {}
    for texture in spec['textures']:
        path = chunks / texture['chunk']
        patched, counts = patch_texture(path.read_bytes(), texture, config)
        path.write_bytes(patched)
        report[texture['name']] = {'changed_endpoints_by_column': counts}
    return report


def run(retoc, *args):
    subprocess.run([str(retoc), *map(str, args)], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)


def install(files, target):
    target = target.resolve()
    target.parent.resolve(strict=True)
    if target.name.lower() != '~mods' or target.parent.name.lower() != 'paks' or target.parent.parent.name.lower() != 'content':
        raise ValueError('Installation target must be the game Content/Paks/~mods directory.')
    target.mkdir(exist_ok=True)
    old = [p for p in target.parent.rglob('RivalColors*')
           if p.is_file() and p.suffix.lower() in {'.pak', '.ucas', '.utoc'}]
    if any(p.is_symlink() or not p.resolve().is_relative_to(target.parent) for p in old):
        raise ValueError('A previous mod resolves outside the intended Paks directory.')
    backup = DATA_ROOT / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    saved = []
    written = []
    # Copy and verify every backup before touching the installed files.
    for path in old:
        dest = backup / path.relative_to(target.parent)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        if digest(path) != digest(dest):
            raise ValueError('Backup verification failed.')
        saved.append((path, dest))
    try:
        for path, _ in saved:
            path.unlink()
        for path in files:
            dest = target / path.name
            written.append(dest)
            shutil.copy2(path, dest)
            if digest(path) != digest(dest):
                raise ValueError('Installed file verification failed.')
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        for path, source in saved:
            shutil.copy2(source, path)
        raise
    print(f'Installed in {target}')
    if saved:
        print(f'Previous RivalColors files backed up in {backup}')


def read_settings():
    path = DATA_ROOT / 'settings.json'
    if not path.exists():
        return {'game_path': None}
    settings = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(settings, dict):
        raise ValueError('settings.json must contain a JSON object.')
    # Silently migrate settings written by the older external-retoc version.
    if set(settings) == {'retoc_path', 'game_path'}:
        settings = {'game_path': settings['game_path']}
    if set(settings) != {'game_path'}:
        raise ValueError('settings.json must contain game_path only.')
    if any(value is not None and not isinstance(value, str) for value in settings.values()):
        raise ValueError('Paths must be strings or null.')
    return settings


def ensure_data_files():
    """Create writable configuration files beside the zip application."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ('colors.json', 'settings.json'):
        destination = DATA_ROOT / name
        if not destination.exists():
            shutil.copy2(RESOURCE_ROOT / name, destination)


def main():
    ensure_data_files()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DATA_ROOT / 'colors.json')
    parser.add_argument('--game', help='TXR installation folder; detected when omitted')
    parser.add_argument('--install', nargs='?', const='auto', metavar='PATH',
                        help='Install after building; optional game or ~mods folder')
    parser.add_argument('--detect', action='store_true', help='List detected installations and exit')
    args = parser.parse_args()
    if args.detect:
        games = find_games()
        print('\n'.join(map(str, games)) if games else 'No TXR installation detected.')
        return
    config = read_config(args.config)
    spec = verify_template()
    settings = read_settings()
    retoc = resolve_retoc(RESOURCE_ROOT)
    target = None
    if args.install:
        game = args.install if args.install != 'auto' else args.game or settings['game_path']
        target = resolve_game(game)
    builds = DATA_ROOT / 'builds'
    builds.mkdir(exist_ok=True)
    output = builds / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    with tempfile.TemporaryDirectory(prefix='rival-colors-') as temp:
        temp = Path(temp)
        raw = temp / 'raw'
        report = make_chunks(config, spec, raw)
        run(retoc, 'pack-raw', raw, temp / f'{NAME}.utoc')
        run(retoc, 'verify', temp / f'{NAME}.utoc')
        run(retoc, 'unpack-raw', temp / f'{NAME}.utoc', temp / 'verified')
        expected = json.loads((raw / 'manifest.json').read_text())['chunk_paths']
        actual = json.loads((temp / 'verified' / 'manifest.json').read_text())['chunk_paths']
        if expected != actual:
            raise ValueError('Packaged asset paths changed.')
        for chunk in expected:
            if digest(raw / 'chunks' / chunk) != digest(temp / 'verified' / 'chunks' / chunk):
                raise ValueError(f'Packaged asset differs: {chunk}')
        output.mkdir()
        for suffix in ('.ucas', '.utoc'):
            shutil.copy2(temp / f'{NAME}{suffix}', output)
        shutil.copy2(RESOURCE_ROOT / 'empty.pak', output / f'{NAME}.pak')
        (output / 'colors.json').write_text(json.dumps(config, indent=2) + '\n')
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    files = [output / f'{NAME}{suffix}' for suffix in ('.pak', '.ucas', '.utoc')]
    print(f'Build verified: {output}')
    if target is not None:
        install(files, target)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'ERROR: {exc}')
