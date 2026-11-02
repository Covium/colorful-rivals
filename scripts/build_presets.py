"""Rebuild all ready-to-install presets using the same verified builder as the app."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from palettes import PRESETS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'presets')
    args = parser.parse_args()
    for name, colors in PRESETS.items():
        with tempfile.TemporaryDirectory(prefix='colorful-preset-') as temp:
            data = Path(temp)
            config = data / 'preset.json'
            config.write_text(json.dumps({'colors': colors}), encoding='utf-8')
            subprocess.run([sys.executable, str(ROOT / 'build.py'), '--config', str(config)],
                           env={**os.environ, 'COLORFUL_RIVALS_DATA_DIR': str(data),
                                'PYTHONIOENCODING': 'utf-8'}, check=True)
            built, = (data / 'builds').iterdir()
            destination = args.output / name
            destination.mkdir(parents=True, exist_ok=True)
            for suffix in ('.pak', '.ucas', '.utoc'):
                shutil.copy2(built / ('RivalColors_Config_P' + suffix), destination)
            print(f'Preset ready: {name}', flush=True)


if __name__ == '__main__':
    main()
