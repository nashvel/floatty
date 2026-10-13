import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from settings import DEFAULT_OPACITY, OpacitySettings, settings_path


class OpacitySettingsTests(unittest.TestCase):
    def test_config_directory_respects_absolute_xdg_path_only(self):
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': '/tmp/custom-config'}):
            self.assertEqual(settings_path(), Path('/tmp/custom-config/floatty/settings.json'))
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': 'relative'}), patch('settings.Path.home', return_value=Path('/home/example')):
            self.assertEqual(settings_path(), Path('/home/example/.config/floatty/settings.json'))

    def test_save_and_reload_only_appearance_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'floatty/settings.json'
            OpacitySettings(path).save(65)
            self.assertEqual(json.loads(path.read_text()), {'opacity': 65})
            self.assertEqual(OpacitySettings(path).load(), 65)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_missing_and_oversized_settings_use_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            store=OpacitySettings(path)
            self.assertEqual(store.load(), DEFAULT_OPACITY)
            for text in ('broken', '[]', 'null', '{"opacity":true}', '{"opacity":"65"}',
                         '{"opacity":54}', '{"opacity":101}', '{"opacity":NaN}',
                         '{"opacity":Infinity}', '{"opacity":'+('9'*400)+'}', ' '*4097):
                with self.subTest(content=text[:30]):
                    path.write_text(text)
                    self.assertEqual(store.load(), DEFAULT_OPACITY)
            path.write_bytes(b'\xff')
            self.assertEqual(store.load(), DEFAULT_OPACITY)

    def test_failed_atomic_replace_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            store=OpacitySettings(path)
            store.save(65)
            with patch('settings.os.replace', side_effect=OSError('Cannot save')):
                with self.assertRaises(OSError):
                    store.save(90)
            self.assertEqual(store.load(), 65)
            self.assertEqual(list(path.parent.iterdir()), [path])
