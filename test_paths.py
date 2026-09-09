import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import paths


class SteamDiscoveryTests(unittest.TestCase):
    def game(self, library, folder='TokyoXtremeRacer'):
        game = library / 'steamapps/common' / folder
        paks = game / 'TokyoXtremeRacer/Content/Paks'
        paks.mkdir(parents=True)
        (paks / 'global.utoc').touch()
        (paks / 'pakchunk0-Windows.utoc').touch()
        return game

    def test_secondary_library_manifest_unicode_and_spaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            steam = root / 'Steam'
            library = root / 'Games with spaces' / 'Игры'
            game = self.game(library, 'Custom TXR folder')
            (steam / 'steamapps').mkdir(parents=True)
            vdf_path = str(library).replace('\\', '\\\\')
            (steam / 'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "1" { "path" "' + vdf_path + '" "apps" { "2634950" "100" } } }', encoding='utf-8')
            (library / 'steamapps/appmanifest_2634950.acf').write_text('"AppState" { "appid" "2634950" "installdir" "Custom TXR folder" }')
            self.assertEqual(paths.find_games([steam], env={}), [game.resolve()])
            target = paths.mod_directory(game)
            self.assertEqual(target.name, '~mods')
            self.assertFalse(target.exists())

    def test_old_vdf_and_missing_libraries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / 'library'
            game = self.game(library)
            (root / 'config').mkdir()
            (root / 'config/libraryfolders.vdf').write_text('"libraryfolders" { "1" "' + library.as_posix() + '" "2" "/does/not/exist" }')
            self.assertEqual(paths.find_games([root], env={}), [game.resolve()])

    def test_linux_standard_xdg_and_flatpak_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            for relative in ('.steam/steam', '.steam/root', '.local/share/Steam',
                             '.var/app/com.valvesoftware.Steam/.local/share/Steam'):
                with self.subTest(relative=relative):
                    roots = paths.steam_roots(env={}, home=home, platform='linux')
                    self.assertIn(home / relative, roots)
            roots = paths.steam_roots(env={'XDG_DATA_HOME': str(home / 'xdg')}, home=home, platform='linux')
            self.assertIn(home / 'xdg/Steam', roots)

    def test_environment_hint_and_duplicate_roots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = self.game(root)
            self.assertEqual(paths.find_games([root, root], env={'STEAM_COMPAT_INSTALL_PATH': str(game)}), [game.resolve()])
            hints = paths.steam_roots(env={'STEAM_COMPAT_CLIENT_INSTALL_PATH': str(root)}, home=root, platform='linux')
            self.assertIn(root, hints)

    def test_explicit_invalid_path_does_not_fall_back(self):
        with patch.object(paths, 'find_games') as find:
            with self.assertRaises(ValueError):
                paths.resolve_game('/does/not/exist')
            find.assert_not_called()

    def test_multiple_installs_require_selection(self):
        with patch.object(paths, 'find_games', return_value=[Path('/one'), Path('/two')]):
            with self.assertRaisesRegex(ValueError, 'More than one'):
                paths.resolve_game()

    def test_windows_escaped_paths_and_comments(self):
        parsed = paths.parse_vdf(r'// comment' + '\n' + r'"libraryfolders" { "1" { "path" "X:\\Games\\Steam" } }')
        self.assertEqual(parsed['libraryfolders']['1']['path'], r'X:\Games\Steam')

    def test_invalid_vdf_and_manifest_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'steamapps').mkdir()
            (root / 'steamapps/libraryfolders.vdf').write_text('"libraryfolders" {')
            (root / 'steamapps/appmanifest_2634950.acf').write_text('"AppState" { "appid" "2634950" "installdir" "../../outside" }')
            self.assertEqual(paths.find_games([root], env={}), [])

    def test_bundled_retoc_and_development_override(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            executable = root / ('retoc.exe' if os.name == 'nt' else 'retoc')
            executable.touch()
            executable.chmod(0o755)
            self.assertEqual(paths.resolve_retoc(root), executable.resolve())
            override = root / 'development-retoc'
            override.touch()
            override.chmod(0o755)
            with patch.dict(os.environ, {'COLORFUL_RIVALS_RETOC': str(override)}):
                self.assertEqual(paths.resolve_retoc(root), override.resolve())

    def test_missing_bundled_retoc_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, 'bundled retoc'):
                    paths.resolve_retoc(temp)


if __name__ == '__main__':
    unittest.main()
