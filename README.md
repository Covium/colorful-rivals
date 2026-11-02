# Colorful Rivals

Tokyo Xtreme Racer uses similar yellow and green colors for rivals you have raced and rivals you have defeated. Those states can be difficult to distinguish, especially with red-green color blindness. Colorful Rivals lets you choose colors that are easier to tell apart.

It changes rival map markers and in-world names, with ready-made presets and a configurator for creating your own palette.

## Features

Customize all five states:

- **Player** — your own marker.
- **Not raced yet** — rivals you have not raced.
- **Raced, not won** — rivals whose previous races ended in a loss or draw.
- **Defeated** — rivals you have beaten.
- **Currently racing** — the opponent in your active race.

The configurator lets you use your system's color picker or enter a `#RRGGBB` value. Leave a field empty to keep the game's original color for that state. It can find the game in your Steam libraries and back up previously installed palettes before replacing them.

## Ready-made presets

The presets archive contains six palettes:

| Preset | Intended use |
| --- | --- |
| Vibrant | Brighter versions of the game's familiar colors |
| Blue & Gold | Protanomaly and deuteranomaly |
| Blue & Gold — Stronger separation | Protanopia and deuteranopia |
| Coral & Cyan | Tritanomaly |
| Coral & Cyan — Stronger separation | Tritanopia |
| Grayscale | Experimental palette for monochromacy |

Use these as starting points and choose what works for your vision and display. Grayscale depends on brightness alone, so darker markers can be harder to see against dark scenery.

### Installation

1. Close the game and extract the presets archive.
2. Choose one preset folder.
3. Copy its `.pak`, `.ucas`, and `.utoc` files into:

   ```text
   <GAME_LOCATION>/TokyoXtremeRacer/Content/Paks/~mods
   ```

Create `~mods` if it does not exist. Remove older `RivalColors*` files first, and keep the three new files together. Install only one palette at a time.

To switch presets, close the game and replace the three files with those from the other folder.

To uninstall, close the game and remove `RivalColors_Config_P.pak`, `RivalColors_Config_P.ucas`, and `RivalColors_Config_P.utoc` from `~mods`.

## Custom colors

Download the configurator for your operating system and CPU architecture: Windows x64, Linux x64 or ARM64, or macOS Intel or Apple Silicon. No additional software is required; Python, Tkinter, and retoc are included.

1. Extract the archive and open **Colorful Rivals**.
2. Choose a preset or set your own colors.
3. Select your TXR installation folder if it was not found automatically.
4. Close the game and press **Build and install**.

Alternatively, **Build only** creates the files for manual installation under `Colorful Rivals Data/builds`. **Save settings** remembers your colors and game location without building.

The application stores settings, builds, and installation backups in `Colorful Rivals Data` beside the executable or macOS app. Existing `RivalColors*` files are backed up before installation; other mod filenames are left alone.

The applications are unsigned, so Windows SmartScreen or macOS Gatekeeper may show a prompt. On Linux, if your archive tool removes executable permissions, run `chmod +x colorful-rivals`.

## How it works

Each build starts from the original marker textures and UI assets, applies your selected colors, and packages the result as an Unreal Engine mod using retoc. Texture transparency, animation timing, and asset references are preserved. The builder verifies the packaged assets before installation.

The game loads the replacement assets from `~mods` when it starts. Mods that replace the same marker textures, widgets, or text styles may conflict, and future game updates may require a refreshed asset template.

## Building from source

Requires Python 3.12 and a native build environment for the target operating system. To prepare a Windows build:

```powershell
python -m pip install -r requirements-build.txt
python scripts/fetch_retoc.py --platform windows-x86_64 --output vendor/retoc
python scripts/fetch_runtime_licenses.py
$env:RETOC_BINARY = "$PWD/vendor/retoc/retoc.exe"
$env:COLORFUL_RIVALS_APP_NAME = "Colorful Rivals"
pyinstaller --noconfirm --clean "Colorful Rivals.spec"
```

For other platforms, use the matching `linux-x86_64`, `linux-aarch64`, `macos-x86_64`, or `macos-aarch64` tool download and build natively on that system. Set `RETOC_BINARY` to the downloaded executable's path.

Run the tests with `python -m unittest discover -p "test*.py"`. To regenerate the ready-made palettes after editing `palettes.py`, run `python scripts/build_presets.py` with retoc available.

## Credits and license

Built with [retoc](https://github.com/trumank/retoc). FModel, RE-UE4SS, UAssetGUI/UAssetAPI, and Pillow helped locate, inspect, and modify the game assets. Thanks to their authors and contributors; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full credits and licenses.

Colorful Rivals is distributed under the [MIT License](LICENSE). Tokyo Xtreme Racer and its game assets belong to their respective rights holders.
