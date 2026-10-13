"""Local appearance preferences only; no credentials or terminal data."""
import json
import math
import os
from pathlib import Path
import tempfile

DEFAULT_OPACITY = 82


def settings_path():
    configured = os.environ.get('XDG_CONFIG_HOME')
    base = Path(configured) if configured and Path(configured).is_absolute() else Path.home()/'.config'
    return base/'floatty/settings.json'


def opacity_value(value):
    if type(value) not in (int, float) or not 55 <= value <= 100 or not math.isfinite(value):
        return float(DEFAULT_OPACITY)
    return float(value)


class OpacitySettings:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else settings_path()

    def load(self):
        try:
            with self.path.open(encoding='utf-8') as source:
                content = source.read(4097)
            if len(content) > 4096:
                return float(DEFAULT_OPACITY)
            data = json.loads(content)
            return opacity_value(data.get('opacity')) if isinstance(data, dict) else float(DEFAULT_OPACITY)
        except (OSError, ValueError, UnicodeError):
            return float(DEFAULT_OPACITY)

    def save(self, opacity):
        value = opacity_value(opacity)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = None
        try:
            descriptor, name = tempfile.mkstemp(prefix='.settings-', suffix='.tmp', dir=self.path.parent)
            temporary = Path(name)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as target:
                json.dump({'opacity': int(value) if value.is_integer() else value}, target, indent=2, allow_nan=False)
                target.write('\n')
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
