import json
from configparser import ConfigParser
from pathlib import Path

from appdirs import user_cache_dir

from flying_desktop import APP_NAME

version = "0.1.0"
PATH = Path(user_cache_dir(appname=APP_NAME, version=version), "cache.ini")
JSON_MARKER = ".json-19fc50b8fac149f790aa25ecf42d78ab"


class Settings:

    def __init__(self):
        self._settings = ConfigParser()
        PATH.parent.mkdir(parents=True, exist_ok=True)
        self._settings.read(PATH)

    def _make_key(self, key):
        section, key = key.split("/")
        if section not in self._settings:
            self._settings.add_section(section)
        return section, key

    def _json_key(self, key):
        return self._make_key(key + JSON_MARKER)

    def get(self, item, default=None):
        value = self._settings.get(*self._make_key(item), fallback=default)
        if self._settings.getboolean(*self._json_key(item), fallback=False):
            value = json.loads(value)
        return value

    __getitem__ = get

    def set(self, key, value):
        is_string = isinstance(value, str)
        self._settings.set(*self._json_key(key), json.dumps(is_string))
        if not is_string:
            value = json.dumps(value)
        self._settings.set(*self._make_key(key), value)
        with PATH.open("w") as f:
            self._settings.write(f)

    __setitem__ = set

    def remove(self, key):
        return self._settings.remove_option(*self._make_key(key))


SETTINGS = Settings()
