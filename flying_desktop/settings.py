from PyQt5.QtCore import QSettings

from flying_desktop import APP_NAME


class Settings:
    def __init__(self):
        self._settings = QSettings(
            QSettings.IniFormat, QSettings.UserScope, APP_NAME, APP_NAME
        )

    def get(self, item, default=None, **kwargs):
        return self._settings.value(item, default, **kwargs)

    __getitem__ = get

    def set(self, key, value):
        self._settings.setValue(key, value)

    __setitem__ = set

    def remove(self, key):
        return self._settings.remove(key)


SETTINGS = Settings()
