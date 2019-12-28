import asyncio
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
from flying_desktop.utils import save_photo, delegate, change_wallpaper, async_callback


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
        self.change_button = self.add_button(
            "Hit me",
            self.change_wallpaper
        )
        #
        self.label = tk.Label(self, text="Download not started")
        self.label.pack()
        self.width = self.add_width_filter()
        #
        #     width_group = self.add_group(QVBoxLayout, width_label, self.width)
        #     self.layout.addWidget(width_group, 1, 1)
        #
        # self.providers_dialog = ProvidersDialog(parent, self.update_photo_status)
        self.providers_dialog = ProvidersDialog(self, self.update_photo_status)
        self.providers_dialog.hide()
        self.login_button = tk.Button(
            self,
            text="Connect",
            # command=lambda: parent.wait_window(self.providers_dialog.top)
            command=self.providers_dialog.show,
        )
        self.login_button.pack()

    def add_width_filter(self):
        """
        Add photo width filter spinbox to window
        :return: push button and label
        """
        #     width_label = QLabel("Minimum picture width", self)
        width = WidthFilter(self, self.update_photo_status)
        width.pack()
        return width

    #     return width, width_label
    #
    # def add_group(self, layout: Type[QLayout], *widgets: QWidget) -> QGridLayout:
    #     """
    #     Add a new group to window
    #     :param layout: type of layout for group
    #     :param widgets: widgets to add to group
    #     :return: added group
    #     """
    #     group = QGroupBox(self)
    #     group_layout = layout(group)
    #     for widget in widgets:
    #         group_layout.addWidget(widget)
    #     self.layout.addWidget(group)
    #     return group

    def add_button(
        self,
        text: str,
        on_click: Callable = None,
    ) -> tk.Button:
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
        self.label["text"] = f"{len(self.meta_photos)} photos fetched\n{len(self.select())} matching photos"

    async def get_photo_and_change(
        self,
            bar: Progressbar,
        bucket: FilledBucket,
        meta_photo: dict,
        retry: int = 3,
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
            # await change_wallpaper(photo_path)
        except BadResponse as e:
            if not retry:
                raise
            traceback.print_exc()
            print(f"Bad response: {e.response}")
            return await self.get_photo_and_change(bar, bucket, meta_photo, retry - 1)
        finally:
            # self.change_button.setEnabled(True)
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
                # self.login_button.setStyleSheet(background)
                self.login_button.configure(old_values)
            return
        # size = self.size()
        filtered_photos = self.select()
        if not filtered_photos:
            # noinspection PyCallByClass
            print("no matching photos")
            # QMessageBox.warning(self, APP_NAME, "No matching photos")
            return

        # bar = QProgressDialog("Downloading photo...", "cancel", 0, 0, self)

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
            # bar.canceled.connect(coro.cancel)
            # self.layout.addWidget(bar, 3, 0, 1, 2)
            await coro
        except asyncio.CancelledError:
            pass
        finally:
            # self.resize(size)
            cancel()
