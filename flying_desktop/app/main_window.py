import asyncio
import logging
import os
import random
import tempfile
import tkinter as tk
import traceback
from typing import Sequence, Iterable, Tuple, Callable

from flying_desktop import PRETTY_NAME
from flying_desktop.app import WidthFilter, make_button, Progressbar
from flying_desktop.app.providers_dialog import ProvidersDialog
from flying_desktop.buckets import FilledBucket
from flying_desktop.providers import BadResponse
from flying_desktop.utils import save_photo, delegate, change_wallpaper, async_callback, LOG_FILE

log = logging.getLogger(__name__)


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
        parent.title(PRETTY_NAME)
        self.change_button = self.add_button("Hit me", self.change_wallpaper)
        #
        self.label = tk.Label(self, text="Download not started")
        self.label.pack()
        self.width = self.add_width_filter()
        self.providers_dialog = ProvidersDialog(self, self.update_photo_status)
        self.providers_dialog.hide()
        self.login_button = tk.Button(
            self, text="Connect", command=self.providers_dialog.show,
        )
        self.login_button.pack()
        self.log_button = tk.Label(self, text="Log file", fg="blue", cursor="hand2")
        self.log_button.bind("<Button-1>", lambda _: os.system(f"notepad {LOG_FILE}"))
        self.log_button.pack()

    def add_width_filter(self):
        """
        Add photo width filter spinbox to window
        :return: push button and label
        """
        width = WidthFilter(self, self.update_photo_status)
        width.pack()
        return width

    def add_button(self, text: str, on_click: Callable = None,) -> tk.Button:
        """
        Add new button to window
        :param text: button text
        :param on_click: click handler
        :return: added button
        """
        button = make_button(self, text, on_click)
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
        :return:
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
        if not self.meta_photos:
            keys = ("borderwidth", "highlightbackground", "highlightcolor")
            old_values = {key: self.login_button[key] for key in keys}
            try:
                self.login_button.configure(dict(zip(keys, (5, "green", "green"))))
                await asyncio.sleep(1)
            finally:
                self.login_button.configure(old_values)
            return
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
