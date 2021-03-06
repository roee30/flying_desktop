"""
General utilities
"""
import asyncio
import logging
import platform
import traceback
from asyncio import Future, Handle, Protocol, Transport
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from functools import partial, wraps
from pathlib import Path
from socket import socket
from typing import Union, AsyncGenerator, Any, TypeVar

import aiofiles
import attr
import pprintpp as pprintpp

from flying_desktop.providers import Photo


@attr.s(auto_attribs=True)
class LoopError:
    message: str
    exception: Exception = None
    future: Future = None
    handle: Handle = None
    protocol: Protocol = None
    transport: Transport = None
    socket: socket = None
    asyncgen: AsyncGenerator = None
    source_traceback: Any = None

    def handler(self):
        logging.error(
            pprintpp.pformat(
                {key: value for key, value in attr.asdict(self).items() if value}
            )
        )


loop = asyncio.new_event_loop()
loop.set_debug(True)
loop.set_exception_handler(lambda _, context: LoopError(**context).handler())
log = logging.getLogger(__name__)

BUTTON_1 = "<Button-1>"


def error_handler(future: Future):
    """
    Send errors in coroutines to log
    """
    exc = future.exception()
    if exc:
        log.error(
            "error in thread: %s: traceback:\n%s",
            exc,
            "".join(traceback.format_tb(exc.__traceback__)),
        )


def async_callback(func):
    """
    Make a coroutine suitable to use with widget callbacks
    """
    @wraps(func)
    def new_func(*args, **kwargs):
        future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
        future.add_done_callback(error_handler)

    return new_func


class ChangeWallpaperDispatch:
    """
    Run different wallpaper change functions for different platforms
    """
    functions = {}

    @classmethod
    def register(cls, name):
        """
        Register a function for platform
        """
        return partial(cls.functions.__setitem__, name.lower())

    @classmethod
    def change_wallpaper(cls, path):
        """
        Invoke function for platform
        """
        return cls.functions[platform.system().lower()](path)


change_wallpaper = ChangeWallpaperDispatch.change_wallpaper


@ChangeWallpaperDispatch.register("windows")
def change_windows(path: Path):
    import win32con
    import win32gui

    val = win32gui.SystemParametersInfo(
        win32con.SPI_SETDESKWALLPAPER,
        str(path),
        win32con.SPIF_SENDCHANGE | win32con.SPIF_UPDATEINIFILE,
    )
    if val is not None:
        log.warning("change wallpaper returned: %s", val)


@ChangeWallpaperDispatch.register("linux")
def change_linux(path: Path):
    from gi.repository import Gio

    gsettings = Gio.Settings.new("org.gnome.desktop.background")
    gsettings.set_string("picture-uri", path.as_uri())


# @ChangeWallpaperDispatch.register("darwin")

PathLike = Union[str, Path]


async def save_photo(photo: Photo, directory: PathLike, name: PathLike):
    """
    Download photo to path
    :param photo: photo meta data
    :param directory: target directory
    :param name: target base name
    """
    destination = Path(directory, name)
    async with aiofiles.open(destination, "wb") as f:
        await f.write(photo.data)
    path_with_suffix = destination.with_suffix(f".{photo.suffix}")
    with suppress(FileNotFoundError):
        await delegate(path_with_suffix.unlink)
    await delegate(destination.rename, path_with_suffix)
    return path_with_suffix


executor = ThreadPoolExecutor()


def delegate(func, *args) -> Future:
    """
    Run coroutine in executor
    """
    return loop.run_in_executor(executor, func, *args)


T = TypeVar("T")


def pack(widget: T) -> T:
    """
    Pack and return widget
    """
    widget.pack()
    return widget
