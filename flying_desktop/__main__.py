"""
Run the Flying Desktop application.
"""
import asyncio
import sys

from PyQt5.QtWidgets import QApplication
from asyncqt import QEventLoop

from flying_desktop.app.main_window import AppWindow


class EventLoop(QEventLoop):
    def _process_events(self, events):
        """
        Catch an exception sometimes thrown by ``asynct.QEventloop`` on Windows
        that seems to relate to cancelled futures
        """
        for event in events:
            try:
                super()._process_events([event])
            except asyncio.InvalidStateError:
                pass


def main():
    app = QApplication(sys.argv)
    loop = EventLoop(app)
    loop.set_debug(True)
    asyncio.set_event_loop(loop)

    with loop:
        window = AppWindow(loop)
        window.show()
        return loop.run_forever()


if __name__ == "__main__":
    sys.exit(main())
