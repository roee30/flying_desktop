import tkinter as tk
from typing import Sequence, Dict

from flying_desktop.buckets import (
    BucketFactory,
    Google,
    Facebook,
    PhotoBucket,
    FilledBucket,
    EmptyBucket,
)
from flying_desktop.utils import async_callback


class ProviderGroup(tk.LabelFrame):
    log_in_out_button: tk.Button
    logout_button: tk.Button
    check_box: tk.Checkbutton

    def __init__(self, parent: tk.BaseWidget, factory: BucketFactory):
        """
        Group of widgets for managing a single provider
        :param parent: parent widget
        :param factory: factory for empty buckets of the provider
        """
        super().__init__(parent, text=factory.name, padx=5, pady=5)
        # self.setToolTip(factory.description)

        self.log_in_out_button = tk.Button(self, text="Log in")
        self.log_in_out_button.grid(row=0, column=0)

        self.check_box_value = tk.BooleanVar()
        self.check_box = tk.Checkbutton(self, variable=self.check_box_value)
        self.check_box.select()
        self.check_box.grid(row=0, column=1)


class ProvidersDialog:
    """
    Dialog for connecting to photos providers
    """

    BUCKETS: Sequence[BucketFactory] = [Google, Facebook]

    def __init__(self, parent: tk.BaseWidget, callback):
        """
        :param parent: parent widget
        """
        self.callback = callback
        top = self.top = tk.Toplevel(parent)

        ok = tk.Button(top, text="OK", command=self.ok)
        ok.grid(row=len(self.BUCKETS), columnspan=2)
        ok["width"] = 20
        self.top.protocol("WM_DELETE_WINDOW", self.ok)

        self.top.title("Accounts")
        self.buckets: Dict[str, PhotoBucket] = {
            bucket.name: self.add_provider(i, bucket) for i, bucket in enumerate(self.BUCKETS)
        }

    def show(self):
        self.top.deiconify()

    def hide(self):
        self.top.withdraw()

    def ok(self):
        self.hide()
        self.callback()

    def add_provider(self, i, factory: BucketFactory) -> EmptyBucket:
        """
        Add login and logout buttons for provider.
        :param factory: bucket factory instance for producing empty buckets
        :return: created empty bucket
        """
        provider = ProviderGroup(self.top, factory)
        provider.grid(column=0, row=i, padx=5, pady=6)
        bucket = factory.new()

        def checked():
            self.buckets[factory.name].checked = provider.check_box_value.get()
            self.callback()

        provider.check_box["command"] = checked

        @async_callback
        async def login(*_):
            print("login")
            import threading;
            print(threading.current_thread().ident)
            self.buckets[factory.name] = filled_bucket = await bucket.fill()
            provider.log_in_out_button["text"] = "Log out"
            async for _ in filled_bucket.download():
                # self.photos_changed.emit()
                self.callback()
            provider.log_in_out_button["command"] = logout

        def logout(*_):
            print("logout")
            filled_bucket: FilledBucket = self.buckets[factory.name]
            filled_bucket.empty()
            self.buckets[bucket.name] = factory.new(checked=filled_bucket.checked)
            provider.log_in_out_button["text"] = "Log in"
            provider.log_in_out_button["command"] = login
            self.callback()

        if bucket.has_credentials():
            login()

        provider.log_in_out_button["command"] = login
        return bucket
