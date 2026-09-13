import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build
from palettes import ORIGINAL, PRESETS, effective_color, matching_preset


class PaletteTests(unittest.TestCase):
    def test_defaults_and_catalog(self):
        config = build.read_config(build.RESOURCE_ROOT / 'colors.json')
        self.assertEqual(config['colors'], next(iter(PRESETS.values())))
        self.assertEqual(len(PRESETS), 6)
        for palette in PRESETS.values():
            self.assertEqual(set(palette), set(build.KEYS))
            for color in palette.values():
                build.rgb(color)

    def test_matching_and_original_fallback(self):
        for name, palette in PRESETS.items():
            self.assertEqual(matching_preset({k: f' {v.lower()} ' for k, v in palette.items()}), name)
        self.assertEqual(matching_preset(dict.fromkeys(ORIGINAL, '')), 'Custom')
        self.assertEqual(effective_color('player', ''), ORIGINAL['player'])
        self.assertIsNone(effective_color('player', '#12'))


class PresetUITests(unittest.TestCase):
    def test_selection_edit_restore_clear_and_reload(self):
        import tkinter as tk
        from configure import App
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk display unavailable: {exc}')
        root.withdraw()
        try:
            with tempfile.TemporaryDirectory() as temp, patch.object(build, 'DATA_ROOT', Path(temp)), \
                    patch.object(root, 'after'), patch.object(App, 'detect'):
                app = App(root)
                self.assertEqual(app.preset.get(), next(iter(PRESETS)))
                for name, palette in PRESETS.items():
                    app.preset.set(name)
                    app.preset_selector.event_generate('<<ComboboxSelected>>')
                    self.assertEqual({k: v.get() for k, v in app.colors.items()}, palette)
                    for key, color in palette.items():
                        self.assertEqual(app.swatches[key].cget('background'), color)
                    app.colors['player'].set('#12')
                    self.assertEqual(app.preset.get(), 'Custom')
                    app.colors['player'].set(palette['player'].lower())
                    self.assertEqual(app.preset.get(), name)
                app.save()
                saved = json.loads((Path(temp) / 'colors.json').read_text())['colors']
                self.assertEqual(matching_preset(saved), name)
                for child in root.winfo_children():
                    child.destroy()
                app = App(root)
                self.assertEqual(app.preset.get(), name)
                app.preset.set('Custom')
                app.select_preset()
                self.assertTrue(all(v.get() == '' for v in app.colors.values()))
                for key, color in ORIGINAL.items():
                    self.assertEqual(app.swatches[key].cget('background'), color)
                self.assertEqual(app.preset.get(), 'Custom')
        finally:
            root.destroy()


if __name__ == '__main__':
    unittest.main()
