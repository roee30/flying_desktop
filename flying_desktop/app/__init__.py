"""
Various app widgets
"""
import tkinter as tk
from tkinter import Spinbox, IntVar
from tkinter import ttk

from typing import Callable


def make_button(parent: tk.BaseWidget, text: str, callback: Callable, **kw):
    """
    Create a new button
    :param parent: parent widget
    :param text: text to display
    :param callback: function to invoke on clicks
    :param kw: extra settings
    """
    button_ = tk.Button(parent, text=text, **kw)
    if callback:
        button_["command"] = callback
    return button_


class WidthFilter(Spinbox):
    """
    Spinbox for filtering images by width
    """

    def __init__(self, parent, command, default=1000):
        self.value = IntVar(None, value=default)
        super().__init__(
            parent,
            from_=0,
            to=1e5,
            textvariable=self.value,
            command=command,
            increment=100,
        )


class Progressbar(ttk.Progressbar):
    """
    Progress bar with a label and a cancel button
    """

    def __init__(self, parent: tk.Widget, text: str, cancel_callback: Callable):
        """
        :param parent: parent widget
        :param text: progress bar text
        :param cancel_callback: callback for cancelling operation
        """
        super(Progressbar, self).__init__(parent, mode="indeterminate")
        self.text = tk.Label(parent, text=text)
        self.cancel_button = make_button(parent, "cancel", cancel_callback)

    def pack(self):
        """
        Show widgets
        """
        self.text.pack()
        super(Progressbar, self).pack()
        self.cancel_button.pack()

    def pack_forget(self):
        """
        Hide widgets
        """
        self.text.pack_forget()
        super(Progressbar, self).pack_forget()
        self.cancel_button.pack_forget()
