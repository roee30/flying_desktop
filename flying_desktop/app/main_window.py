import asyncio
import logging
import os
import random
import tempfile
import tkinter as tk
# noinspection PyPep8Naming
import tkinter.scrolledtext as ScrolledText
import traceback
from datetime import datetime
from typing import Sequence, Iterable, Tuple, Callable

from flying_desktop import PRETTY_NAME
from flying_desktop.app import WidthFilter, make_button, Progressbar
from flying_desktop.app.period import Period
from flying_desktop.app.providers_dialog import ProvidersDialog
from flying_desktop.buckets import FilledBucket
from flying_desktop.log import LOG_FILE, LOG_FORMAT, APP_NAME
from flying_desktop.providers import BadResponse
from flying_desktop.settings import SETTINGS
from flying_desktop.utils import (
    save_photo,
    delegate,
    change_wallpaper,
    async_callback,
)

log = logging.getLogger(__name__)


class TextHandler(logging.Handler):
    """
    This class allows you to log to a Tkinter Text or ScrolledText widget
    Adapted from Moshe Kaplan: https://gist.github.com/moshekaplan/c425f861de7bbf28ef06
    """

    def __init__(self, text):
        # run the regular Handler __init__
        super().__init__()
        # Store a reference to the Text it will log to
        self.text = text

    def emit(self, record):
        msg = self.format(record)

        def append():
            self.text.configure(state="normal")
            self.text.insert(tk.END, msg + "\n")
            self.text.configure(state="disabled")
            # Autoscroll to the bottom
            self.text.yview(tk.END)

        # This is necessary because we can't modify the Text from other threads
        self.text.after(0, append)


class AppWindow(tk.Frame):
    """
    Application main window
    """

    @property
    def meta_photos(self) -> Sequence[dict]:
        """
        Return photo metadata from all buckets
        """
        return [photo for bucket in self.active_buckets for photo in bucket.photos]

    @property
    def active_buckets(self) -> Iterable[FilledBucket]:
        """
        Return all logged in, checked buckets
        """
        return [
            bucket
            for bucket in self.providers_dialog.buckets.values()
            if isinstance(bucket, FilledBucket) and bucket.checked
        ]

    def __init__(self, loop: asyncio.AbstractEventLoop, parent: tk.Tk):
        super().__init__(parent)
        self.loop = loop
        self.parent = parent
        parent.title(PRETTY_NAME)
        self.change_button = self.add_button(
            "Hit me", self.change_wallpaper, bg="green", fg="white"
        )
        self.label = tk.Label(self, text="Download not started")
        self.label.pack()
        self.width = self.add_width_filter()
        self.providers_dialog = ProvidersDialog(self, self.update_photo_status)
        self.providers_dialog.hide()
        self.login_button = tk.Button(
            self, text="Connect", command=self.providers_dialog.show,
        )
        self.login_button.pack()
        self.next_change_handle = None
        self.period = Period(self, self.on_period_change)
        self.console = self.init_console()
        now = datetime.now()
        if self.change_at < now:
            self.change_wallpaper_and_schedule()
        self.change_at = now + self.period.get()
        self.next_change_handle = self.parent.after(
            int(self.period.get().total_seconds()) * 1000, self.change_wallpaper_and_schedule
        )

    def change_wallpaper_and_schedule(self):
        log.debug("change_wallpaper_and_schedule")
        self.change_button.invoke()
        self.next_change_handle = None
        self.on_period_change()

    def on_period_change(self):
        log.debug("on_period_change")
        if self.next_change_handle:
            self.parent.after_cancel(self.next_change_handle)
        self.change_at = datetime.now() + self.period.get()
        self.next_change_handle = self.parent.after(
            int(self.period.get().total_seconds()) * 1000, self.change_wallpaper_and_schedule
        )

    def init_console(self):
        log_button = tk.Label(self, text="Log file", fg="blue", cursor="hand2")
        log_button.bind("<Button-1>", lambda _: os.system(f"notepad {LOG_FILE}"))
        log_button.pack()
        console = ScrolledText.ScrolledText(self, state="disabled", padx=0, pady=0)
        console.configure(font="TkFixedFont")
        handler = TextHandler(console)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(LOG_FORMAT)
        logging.getLogger(APP_NAME).addHandler(handler)
        log.debug("hello")

        def show():
            console.pack()
            show_button["command"] = hide

        def hide():
            console.pack_forget()
            show_button["command"] = show

        show_button = tk.Button(self, text="Show console", fg="blue", command=show)
        show_button.pack()
        return console

    def add_width_filter(self):
        """
        Add photo width filter spinbox to window
        :return: push button and label
        """
        frame = tk.LabelFrame(self, text="Width", padx=5, pady=5)
        label = tk.Label(frame, text="Minimum width")
        label.pack()
        width = WidthFilter(frame, self.update_photo_status)
        width.pack()
        frame.pack()
        return width

    def add_button(self, text: str, on_click: Callable = None, **kw) -> tk.Button:
        """
        Add new button to window
        :param text: button text
        :param on_click: click handler
        :return: added button
        """
        button = make_button(self, text, on_click, **kw)
        button.pack()
        return button

    def update_photo_status(self) -> None:
        """
        Display amount of photos for which metadata has been downloaded
        and amount currently selected by filter
        """
        self.label[
            "text"
        ] = f"{len(self.meta_photos)} photos fetched\n{len(self.select())} matching photos"

    async def get_photo_and_change(
        self, bar: Progressbar, bucket: FilledBucket, meta_photo: dict, retry: int = 3,
    ) -> None:
        """
        Change wallpaper to photo represented by ``meta_photo`` metadata
        :param bar: progress dialog
        :param bucket: bucket of photos to which ``meta_photo`` belongs
        :param meta_photo: metadata of photo to set wallpaper to
        :param retry: amount of retries on failure
        """
        try:
            self.change_button["state"] = tk.DISABLED
            meta_photo = await bucket.client.download_photo(meta_photo)
            photo_path = await save_photo(
                meta_photo, tempfile.gettempdir(), "wallpaper"
            )
            bar.text["text"] = "Changing wallpaper"
            await delegate(change_wallpaper, photo_path)
        except BadResponse as e:
            if not retry:
                raise
            log.error("".join(traceback.format_exc()))
            log.error(f"Bad response: {e.response}")
            return await self.get_photo_and_change(bar, bucket, meta_photo, retry - 1)
        finally:
            self.change_button["state"] = tk.NORMAL

    @property
    def change_at(self):
        value = SETTINGS["period/change_at"]
        if value:
            return datetime.fromisoformat(value)
        return datetime.fromtimestamp(000000000)

    @change_at.setter
    def change_at(self, value: datetime):
        SETTINGS["period/change_at"] = value.isoformat()

    def select(self) -> Sequence[Tuple[FilledBucket, dict]]:
        """
        Return all meta photos for which filters apply
        """
        return [
            (bucket, photo)
            for bucket in self.active_buckets
            for photo in bucket.select(self.width.value.get())
        ]

    @async_callback
    async def change_wallpaper(self):
        """
        Select a photo from filtered photos and set it as wallpaper
        """
        log.debug("changing wallpaper")
        if not self.meta_photos:
            log.info("no meta photos")
            keys = ("borderwidth", "highlightbackground", "highlightcolor")
            old_values = {key: self.login_button[key] for key in keys}
            try:
                self.login_button.configure(dict(zip(keys, (5, "green", "green"))))
                await asyncio.sleep(1)
            finally:
                self.login_button.configure(old_values)
            return
        log.debug("meta photos found")
        filtered_photos = self.select()
        if not filtered_photos:
            log.warning("no matching photos")
            return

        def cancel():
            bar.pack_forget()
            if not coro.done():
                self.loop.call_soon_threadsafe(coro.cancel)

        bar = Progressbar(self, "Downloading photo...", cancel)
        bar.pack()
        bar.start(50)

        coro = self.loop.create_task(
            self.get_photo_and_change(bar, *random.choice(filtered_photos))
        )
        try:
            await coro
        except asyncio.CancelledError:
            pass
        finally:
            cancel()
