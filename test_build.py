"""Focused checks for state isolation and preserving original binary data."""
import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest

import build


class ColorBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = build.verify_template()
        cls.original = {p.name: p.read_bytes() for p in (build.ROOT / 'template/chunks').iterdir()}
        cls.config = json.loads((build.ROOT / 'colors.json').read_text())
        cls.config['colors'] = dict.fromkeys(build.KEYS)

    def generate(self, config):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / 'raw'
            build.make_chunks(config, self.spec, raw)
            return {p.name: p.read_bytes() for p in (raw / 'chunks').iterdir()}

    def test_null_is_byte_identical(self):
        self.assertEqual(self.generate(self.config), self.original)

    def test_each_state_changes_only_its_fields_and_columns(self):
        for key in build.KEYS:
            with self.subTest(key=key):
                config = copy.deepcopy(self.config)
                config['colors'][key] = '#B52ACF'
                changed = self.generate(config)
                allowed = {chunk: set() for chunk in self.original}
                style_key = {'player': 'unknown_rumer'}.get(key, key)
                if style_key in self.spec['styles']:
                    style = self.spec['styles'][style_key]
                    allowed[style['chunk']].update(range(style['offset'], style['offset'] + 12))
                    actual = struct.unpack_from('<3f', changed[style['chunk']], style['offset'])
                    for a, b in zip(actual, build.linear('#B52ACF')):
                        self.assertAlmostEqual(a, b, places=7)
                for track in self.spec['widget']['tracks']:
                    if build.STATE_KEYS.get(track['state'], track['state']) == key:
                        for offset, channel in track['offsets']:
                            allowed[self.spec['widget']['chunk']].update(range(offset, offset + 4))
                            self.assertAlmostEqual(struct.unpack_from('<f', changed[self.spec['widget']['chunk']], offset)[0], build.linear('#B52ACF')[channel], places=7)
                for tex in self.spec['textures']:
                    for by in range(tex['height'] // 4):
                        for bx in range(tex['width'] // 4):
                            col = bx * 4 // (tex['width'] // 14)
                            if build.KINDS[col] == key:
                                offset = tex['offset'] + (by * (tex['width'] // 4) + bx) * 16 + 8
                                allowed[tex['chunk']].update(range(offset, offset + 4))
                total = 0
                for chunk, before in self.original.items():
                    after = changed[chunk]
                    self.assertEqual(len(before), len(after))
                    diffs = {i for i, (a, b) in enumerate(zip(before, after)) if a != b}
                    self.assertTrue(diffs <= allowed[chunk], (key, chunk))
                    total += len(diffs)
                self.assertGreater(total, 0)

    def test_unused_unknown_assets_remain_original(self):
        config = {'colors': {key: '#B52ACF' for key in build.KEYS}}
        changed = self.generate(config)
        style = self.spec['styles']['unknown_none']
        self.assertEqual(changed[style['chunk']], self.original[style['chunk']])
        widget_chunk = self.spec['widget']['chunk']
        for track in self.spec['widget']['tracks']:
            if track['state'] == 'unknown_none':
                for offset, _ in track['offsets']:
                    self.assertEqual(changed[widget_chunk][offset:offset + 4],
                                     self.original[widget_chunk][offset:offset + 4])

    def test_swapped_colors_do_not_cascade(self):
        config = copy.deepcopy(self.config)
        config['colors'].update(none='#FFE66E', incomplete='#378CFF')
        combined = self.generate(config)
        separate = []
        for key in ('none', 'incomplete'):
            one = copy.deepcopy(self.config)
            one['colors'][key] = config['colors'][key]
            separate.append(self.generate(one))
        for chunk, before in self.original.items():
            expected = bytes(b if b != a else c for a, b, c in zip(before, separate[0][chunk], separate[1][chunk]))
            self.assertEqual(combined[chunk], expected)
    def test_invalid_config_rejected(self):
        for invalid in ('red', '#123', '#12345678', 10, ''):
            with self.assertRaises(ValueError):
                build.rgb(invalid)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            config = copy.deepcopy(self.config)
            config['colors']['typo'] = '#123456'
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                build.read_config(path)


if __name__ == '__main__':
    unittest.main()
