"""
Run the Flying Desktop application.
"""
import asyncio
import sys
import threading
import tkinter as tk

from .log import logging_setup
logging_setup()


from .utils import loop
from flying_desktop.app.main_window import AppWindow


def loop_worker(loop_: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop_)
    loop_.run_forever()


def main():
    loop_thread = threading.Thread(target=loop_worker, args=(loop,), daemon=True)
    loop_thread.start()
    root = tk.Tk()
    app = AppWindow(loop, root)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    sys.exit(main())
