import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build


class SettingsTests(unittest.TestCase):
    def test_current_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'settings.json').write_text(json.dumps({'game_path': '/game'}))
            with patch.object(build, 'DATA_ROOT', root):
                self.assertEqual(build.read_settings(), {'game_path': '/game'})

    def test_external_retoc_setting_is_migrated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'settings.json').write_text(json.dumps({
                'retoc_path': '/old/retoc',
                'game_path': '/game',
            }))
            with patch.object(build, 'DATA_ROOT', root):
                self.assertEqual(build.read_settings(), {'game_path': '/game'})


if __name__ == '__main__':
    unittest.main()
