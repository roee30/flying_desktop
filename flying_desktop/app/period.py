"""
Widget for controlling wallpaper change period
"""
import logging
import tkinter as tk
from datetime import timedelta
from typing import Mapping

import attr
from flying_desktop.settings import SettingsProperty

from flying_desktop.utils import pack

log = logging.getLogger(__name__)


@attr.s(auto_attribs=True)
class PeriodOption:
    """
    A single time-duration unit option
    :param name: user-friendly name
    :param duration: program-friendly duration
    """
    name: str
    duration: timedelta


class Period:
    """
    Widget for controlling wallpaper change period.
    Contains a slider and a drop-down menu.
    """
    OPTIONS: Mapping[str, PeriodOption] = {
        option.name: option
        for option in [
            PeriodOption("seconds", timedelta(seconds=1)),
            PeriodOption("minutes", timedelta(seconds=60)),
            PeriodOption("hours", timedelta(hours=1)),
            PeriodOption("days", timedelta(days=1)),
        ]
    }

    base = SettingsProperty("period/base")
    multiple = SettingsProperty("period/multiple")

    def __init__(self, parent, command):
        """
        :param parent: parent widget
        :param command: callback for any child widget change
        """
        self.command = command
        self.frame = pack(tk.LabelFrame(parent, text="Change period", padx=5, pady=5))
        self.variable = tk.StringVar(self.frame)
        self.variable.set(self.base or self.OPTIONS["days"].name)
        self.menu = tk.OptionMenu(self.frame, self.variable, *self.OPTIONS, command=self.on_change)
        self.menu.grid(row=0, column=0)
        self.slider = tk.Scale(
            self.frame, from_=1, to=60, orient=tk.HORIZONTAL, command=self.on_change
        )
        self.slider.set(self.multiple)
        self.slider.grid(row=0, column=1)

    def on_change(self, _):
        """
        Save settings and invoke callback
        """
        self.base = self.variable.get()
        self.multiple = self.slider.get()
        self.command()

    def get(self) -> timedelta:
        """
        Return period of wallpaper switching according to user input
        """
        return self.OPTIONS[self.variable.get()].duration * self.slider.get()
