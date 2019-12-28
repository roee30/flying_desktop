import asyncio
from typing import Sequence, Dict

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGroupBox,
    QHBoxLayout,
    QCheckBox,
    QWidget,
)
from asyncqt import asyncSlot

from flying_desktop.app import Button
from flying_desktop.buckets import (
    BucketFactory,
    Google,
    Facebook,
    PhotoBucket,
    FilledBucket,
    EmptyBucket,
)


class ProviderGroup(QGroupBox):
    login_button: Button
    logut_button: Button
    check_box: QCheckBox

    def __init__(self, parent: QWidget, factory: BucketFactory):
        """
        Group of widgets for managing a single provider
        :param parent: parent widget
        :param factory: factory for empty buckets of the provider
        """
        super().__init__(parent)
        self.setTitle(factory.name)
        self.setToolTip(factory.description)

        self.layout = QHBoxLayout(self)
        self.login_button = Button("Log in")
        self.layout.addWidget(self.login_button)
        self.logout_button = Button("Log out")
        self.layout.addWidget(self.logout_button)
        self.logout_button.hide()

        self.check_box = QCheckBox(self)
        self.check_box.setCheckState(Qt.Checked)
        self.layout.addWidget(self.check_box)


class ProvidersDialog(QDialog):
    """
    Dialog for connecting to photos providers
    """

    BUCKETS: Sequence[BucketFactory] = [Google, Facebook]
    photos_changed = pyqtSignal()

    def __init__(self, parent: QWidget = None):
        """
        :param parent: parent widget
        """
        super(ProvidersDialog, self).__init__(parent, flags=Qt.WindowCloseButtonHint)
        self.setWindowTitle("Accounts")
        self.layout = QVBoxLayout(self)
        accept = Button("OK", self)
        accept.setDefault(True)
        self.buckets: Dict[str, PhotoBucket] = {
            bucket.name: self.add_provider(bucket) for bucket in self.BUCKETS
        }
        accept.clicked.connect(self.accept)
        self.layout.addWidget(accept, len(self.BUCKETS))

    def add_provider(self, factory: BucketFactory) -> EmptyBucket:
        """
        Add login and logout buttons for provider.
        :param factory: bucket factory instance for producing empty buckets
        :return: created empty bucket
        """
        provider = ProviderGroup(self, factory)
        self.layout.addWidget(provider)
        bucket = factory.new()

        def checked(state):
            self.buckets[factory.name].checked = bool(state)
            self.photos_changed.emit()

        provider.check_box.stateChanged.connect(checked)

        async def login(*_):
            self.buckets[factory.name] = filled_bucket = await bucket.fill()
            provider.login_button.hide()
            provider.logout_button.show()
            async for _ in filled_bucket.download():
                self.photos_changed.emit()
            self.photos_changed.emit()

        def logout(*_):
            filled_bucket: FilledBucket = self.buckets[factory.name]
            filled_bucket.empty()
            self.buckets[bucket.name] = factory.new(checked=filled_bucket.checked)
            provider.logout_button.hide()
            provider.login_button.show()
            self.photos_changed.emit()

        if bucket.has_credentials():
            asyncio.get_event_loop().create_task(login())

        provider.login_button.clicked.connect(asyncSlot()(login))
        provider.logout_button.clicked.connect(logout)

        return bucket
