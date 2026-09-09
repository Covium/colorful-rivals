# Colorful Rivals for Tokyo Xtreme Racer

Colorful Rivals replaces Tokyo Xtreme Racer's rival-marker palette in the world, on the minimap, and on the full map. It supports five gameplay states:

- **Player** — your own marker.
- **Not raced yet** — an opponent you have not raced.
- **Raced, not won** — an opponent whose previous races ended in a draw or defeat.
- **Defeated** — an opponent you have beaten.
- **Currently racing** — the opponent in your active race.

The game's white `Unknown_None` marker and its second atlas column do not appear to be used. Their assets remain in the template for future investigation, but the configurator preserves them byte-for-byte and does not expose them as a setting.

## Downloads

GitHub releases provide these downloads:

1. **Colorful-Rivals-Vibrant-Preset** contains a ready-made mod. It does not contain or run a program.
2. Five platform-specific archives contain the configurator for Windows x64, Linux x64, Linux ARM64, macOS Intel, and macOS Apple Silicon. These archives are intended to be listed separately on Nexus Mods so users can download only the build they need.
3. **Colorful-Rivals-All-Platforms** is a convenience archive containing every configurator build in separate folders.

The compiled configurator includes Python, its graphical interface, the asset template, and the correct [retoc](https://github.com/trumank/retoc) 0.1.5 executable for its platform. Users do not need to install Python, Tkinter, retoc, a command-line shell, or any other dependency.

The executables are currently unsigned. Windows SmartScreen or macOS Gatekeeper may therefore ask you to confirm that you want to run a downloaded build. Release archives include the source repository's documentation and third-party license texts so the build can be audited.

## Ready-made vibrant preset

The included preset uses a more saturated version of the game's familiar orange, blue, yellow, green, and red scheme:

- Player: `#FF6D00`
- Not raced yet: `#2979FF`
- Raced, not won: `#FFD600`
- Defeated: `#00C853`
- Currently racing: `#FF1744`

Close the game and place all three `RivalColors_Config_P` files (`.pak`, `.ucas`, and `.utoc`) in:

```text
TokyoXtremeRacer/TokyoXtremeRacer/Content/Paks/~mods
```

Create `~mods` if it does not exist. Remove older `RivalColors*` files before launching the game, and keep the three new files together.

## Custom colors

Extract the archive for your platform and open the application:

- Windows: `Colorful Rivals.exe`
- Linux: `colorful-rivals`
- macOS: `Colorful Rivals.app`

Linux normally retains the executable permission when extracted. If your archive program removes it, run `chmod +x colorful-rivals` once.

The configurator attempts to locate Tokyo Xtreme Racer in your Steam libraries. If it cannot find the game, select its installation folder. Choose a color for each state, close the game, and select **Build and install**. Restart the game afterwards.

**Build only** creates the package without changing the game. **Original** leaves that state's exact original data in place. **Save settings** records the colors and game location without building.

The application creates `Colorful Rivals Data` beside the executable or macOS app. It stores the selected colors, game location, generated builds, and installation backups. Deleting this directory resets the settings without damaging the application.

Each build creates a timestamped directory under `Colorful Rivals Data/builds` containing `RivalColors_Config_P.pak`, `.ucas`, and `.utoc`, plus a configuration snapshot and report. Installation backs up existing `RivalColors*` files from the game's Paks tree into `Colorful Rivals Data/backups` before replacing them. Other mod filenames are untouched. If installation fails, the previous files are restored.

Every build starts from a hash-checked original asset template and verifies container integrity, package paths, and every packaged asset's bytes. Texture transparency, the red atlas backing area, animation timing, visibility, and asset references are preserved.

The template is tied to the tested version of the game. A future game update may require refreshed assets. Mods replacing the same widgets, text styles, or marker textures can conflict.

## Building from source

The readable Python files are the source of the compiled application. End users do not need Python; maintainers need Python 3.12 to run tests or create executables.

Run the tests:

```sh
python -m unittest discover -p "test*.py"
```

Install the pinned build tool, fetch the pinned retoc executable for your platform, collect the runtime licenses, and build:

```sh
python -m pip install -r requirements-build.txt
python scripts/fetch_retoc.py --platform windows-x86_64 --output vendor/retoc
python scripts/fetch_runtime_licenses.py
```

On Windows PowerShell:

```powershell
$env:RETOC_BINARY = "$PWD/vendor/retoc/retoc.exe"
$env:COLORFUL_RIVALS_APP_NAME = "Colorful Rivals"
pyinstaller --noconfirm --clean "Colorful Rivals.spec"
```

Use `linux-x86_64`, `linux-aarch64`, `macos-x86_64`, or `macos-aarch64` instead when building natively on those platforms. PyInstaller creates native applications, so each target must be built on that target operating system and architecture.

`retoc-lock.json` pins every official retoc 0.1.5 release asset and its published SHA-256. `scripts/fetch_retoc.py` refuses an archive whose hash differs. A Git submodule is not used because submodules pin source commits rather than release executables.

## Manual GitHub releases

The **Build release** workflow runs only through GitHub's **Run workflow** button. Enter a version without a leading `v` and choose one mode:

- **artifacts-only** builds and tests every platform and uploads one review bundle to the workflow run. It creates no tag and no GitHub release. This is the default.
- **draft** creates an unpublished draft GitHub release.
- **prerelease** creates a visible prerelease.
- **release** creates a normal public release.

Every successful run produces:

- five platform archives: Windows x64, Linux x64, Linux ARM64, macOS Intel, and macOS Apple Silicon;
- `Colorful-Rivals-All-Platforms`, with those applications arranged in platform folders as a convenience download;
- `Colorful-Rivals-Vibrant-Preset`, containing the ready-made `.pak`, `.ucas`, and `.utoc` files for the primary Nexus Mods download.

## Credits and licenses

Colorful Rivals embeds retoc under its MIT License and includes all required runtime license texts in release archives. FModel, UE4SS, UAssetGUI/UAssetAPI, and Pillow were used while locating, inspecting, modifying, and checking the game assets. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for authors, links, licenses, and the complete tool credits.

Colorful Rivals is distributed under the [MIT License](LICENSE).

Tokyo Xtreme Racer and its game assets belong to their respective rights holders. Colorful Rivals is an unofficial community mod and is not affiliated with or endorsed by Genki.
