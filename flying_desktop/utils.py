import asyncio
import platform
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial
from pathlib import Path
from typing import Union, Awaitable

import aiofiles

from .providers import Photo


class ChangeWallpaperDispatch:
    functions = {}

    @classmethod
    def register(cls, name):
        return partial(cls.functions.__setitem__, name.lower())

    @classmethod
    def change_wallpaper(cls, path):
        return cls.functions[platform.system().lower()](path)


change_wallpaper = ChangeWallpaperDispatch.change_wallpaper


@ChangeWallpaperDispatch.register("windows")
def change_windows(path: Path):
    import win32con
    import win32gui

    win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, str(path), 0)


@ChangeWallpaperDispatch.register("linux")
def change_linux(path: Path):
    from gi.repository import Gio

    gsettings = Gio.Settings.new("org.gnome.desktop.background")
    gsettings.set_string("picture-uri", path.as_uri())


# @ChangeWallpaperDispatch.register("darwin")

PathLike = Union[str, Path]


async def save_photo(photo: Photo, directory: PathLike, name: PathLike):
    destination = Path(directory, name)
    async with aiofiles.open(destination, "wb") as f:
        await f.write(photo.data)
    path_with_suffix = destination.with_suffix(f".{photo.suffix}")
    with suppress(FileNotFoundError):
        await delegate(path_with_suffix.unlink)
    await delegate(destination.rename, path_with_suffix)
    return path_with_suffix


executor = ThreadPoolExecutor()


def delegate(func, *args) -> Awaitable:
    loop = asyncio.get_event_loop()
    result: Awaitable = loop.run_in_executor(executor, func, *args)
    return result
