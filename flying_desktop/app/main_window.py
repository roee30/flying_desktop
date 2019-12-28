import asyncio
import random
import tempfile
import traceback
from typing import Sequence, Iterable, Type, Tuple, Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QLayout,
    QGroupBox,
    QProgressDialog,
    QMessageBox,
)
from asyncqt import asyncSlot

from flying_desktop import PRETTY_NAME, APP_NAME
from flying_desktop.app import WidthFilter, Button
from flying_desktop.app.providers_dialog import ProvidersDialog
from flying_desktop.buckets import FilledBucket
from flying_desktop.providers import BadResponse
from flying_desktop.utils import save_photo, delegate, change_wallpaper


class AppWindow(QMainWindow):
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

    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop
        self.setMinimumSize(0, 0)

        self.setWindowTitle(PRETTY_NAME)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        self.layout = QGridLayout(central_widget)
        self.layout.setSizeConstraint(QGridLayout.SetFixedSize)

        self.change_button = self.add_button(
            "Hit me", "Select a random wallpaper", (0, 1), self.change_wallpaper
        )

        self.label = QLabel("Download not started", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label, 1, 0)

        self.width, width_label = self.add_width_filter()

        width_group = self.add_group(QVBoxLayout, width_label, self.width)
        self.layout.addWidget(width_group, 1, 1)

        self.providers_dialog = ProvidersDialog(self)
        self.providers_dialog.photos_changed.connect(self.update_photo_status)

        self.login_button = self.add_button(
            text="Connect",
            tool_tip="Manage sources for photos for your desktop",
            position=(0, 0),
            on_click=self.providers_dialog.show,
        )

    def add_width_filter(self) -> Tuple[Button, QLabel]:
        """
        Add photo width filter spinbox to window
        :return: push button and label
        """
        width_label = QLabel("Minimum picture width", self)
        width = WidthFilter(self)
        width.valueChanged.connect(self.update_photo_status)
        return width, width_label

    def add_group(self, layout: Type[QLayout], *widgets: QWidget) -> QGridLayout:
        """
        Add a new group to window
        :param layout: type of layout for group
        :param widgets: widgets to add to group
        :return: added group
        """
        group = QGroupBox(self)
        group_layout = layout(group)
        for widget in widgets:
            group_layout.addWidget(widget)
        self.layout.addWidget(group)
        return group

    def add_button(
        self,
        text: str,
        tool_tip: str,
        position: Tuple[int, int],
        on_click: Callable = None,
    ) -> Button:
        """
        Add new button to window
        :param text: button text
        :param tool_tip: button tooltip
        :param position: position of button in layout
        :param on_click: click handler
        :return: added button
        """
        button = Button(text, self)
        button.setToolTip(tool_tip)
        if on_click:
            button.clicked.connect(on_click)
        self.layout.addWidget(button, *position)
        return button

    def update_photo_status(self) -> None:
        """
        Display amount of photos for which metadata has been downloaded
        and amount currently selected by filter
        """
        self.label.setText(
            f"{len(self.meta_photos)} photos fetched\n{len(self.select())} matching photos"
        )

    async def get_photo_and_change(
        self,
        bar: QProgressDialog,
        bucket: FilledBucket,
        meta_photo: dict,
        retry: int = 3,
    ) -> None:
        """
        Change wallpapaer to photo represented by ``meta_photo`` metadata
        :param bar: progress dialog
        :param bucket: bucket of photos to which ``meta_photo`` belongs
        :param meta_photo: metadata of photo to set wallpaper to
        :param retry: amount of retries on failure
        :return:
        """
        try:
            self.change_button.setEnabled(False)
            meta_photo = await bucket.client.download_photo(meta_photo)
            photo_path = await save_photo(
                meta_photo, tempfile.gettempdir(), "wallpaper"
            )
            bar.setLabelText("Changing wallpaper...")
            await delegate(change_wallpaper, photo_path)
        except BadResponse as e:
            if not retry:
                raise
            traceback.print_exc()
            print(f"Bad response: {e.response}")
            return await self.get_photo_and_change(bar, bucket, meta_photo, retry - 1)
        finally:
            self.change_button.setEnabled(True)

    def select(self) -> Sequence[Tuple[FilledBucket, dict]]:
        """
        Return all meta photos for which filters apply
        """
        return [
            (bucket, photo)
            for bucket in self.active_buckets
            for photo in bucket.select(self.width.value())
        ]

    @asyncSlot()
    async def change_wallpaper(self):
        """
        Select a photo from filtered photos and set it as wallpaper
        """
        if not self.meta_photos:
            style_sheet = self.change_button.styleSheet()
            try:
                self.login_button.set_style(border="5px solid green")
                await asyncio.sleep(1)
            finally:
                self.login_button.setStyleSheet(style_sheet)
            return
        size = self.size()
        filtered_photos = self.select()
        if not filtered_photos:
            # noinspection PyCallByClass
            QMessageBox.warning(self, APP_NAME, "No matching photos")
            return
        bar = QProgressDialog("Downloading photo...", "cancel", 0, 0, self)
        coro = self.loop.create_task(
            self.get_photo_and_change(bar, *random.choice(filtered_photos))
        )
        try:
            bar.canceled.connect(coro.cancel)
            self.layout.addWidget(bar, 3, 0, 1, 2)
            await coro
        except asyncio.CancelledError:
            pass
        finally:
            self.resize(size)
            self.layout.removeWidget(bar)
            bar.canceled.disconnect()
            bar.hide()
