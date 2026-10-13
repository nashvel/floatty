import importlib.util
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ProjectLayoutTests(unittest.TestCase):
    def test_launcher_resolves_source_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([str(ROOT / 'launch.sh'), '--help'], cwd=directory,
                                    capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--folder', result.stdout)
        self.assertIn('--reduced-motion', result.stdout)

    def test_site_validates_project_relative_assets_and_rejects_escape(self):
        builder = tool('build_site')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'image.svg').write_text('<svg/>')
            page = root/'index.html'
            page.write_text('<a href="#demo">Demo</a><div id="demo"><img src="image.svg"></div>')
            builder.validate(root)
            page.write_text('<a href="../private.txt">Escape</a>')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                builder.validate(root)
            page.write_text('<a href="#missing">Missing</a>')
            with self.assertRaisesRegex(ValueError, 'Missing anchor'):
                builder.validate(root)

    def test_release_excludes_runtime_files_and_normalizes_owner(self):
        release = tool('package_release')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for item in release.FILES:
                (root/item).write_text('0.1.0' if item == 'VERSION' else 'sample')
            for folder in release.DIRECTORIES:
                (root/folder).mkdir()
            (root/'src'/'island.py').write_text('print("app")')
            (root/'src'/'.env').write_text('not-for-release')
            (root/'src'/'credentials.json').write_text('{}')
            (root/'src'/'__pycache__').mkdir()
            (root/'src'/'__pycache__'/'island.pyc').write_bytes(b'cache')
            (root/'.git').mkdir()
            (root/'.git'/'config').write_text('local-only')
            with patch.object(release, 'ROOT', root):
                release.main()
            archive = root/'dist/releases/codex-island-0.1.0.tar.gz'
            with tarfile.open(archive) as bundle:
                names = bundle.getnames()
                self.assertIn('codex-island-0.1.0/src/island.py', names)
                self.assertFalse(any('.env' in n or 'credentials.json' in n or '__pycache__' in n or '/.git/' in n for n in names))
                self.assertEqual(bundle.getmember('codex-island-0.1.0/launch.sh').mode, 0o755)
                self.assertTrue(all(i.uid == i.gid == 0 and not i.uname and not i.gname for i in bundle.getmembers()))
            self.assertTrue(archive.with_suffix('.gz.sha256').exists())
