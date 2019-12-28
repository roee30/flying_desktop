from PyQt5.QtWidgets import QPushButton, QSpinBox, QWidget


class Button(QPushButton):
    """
    Push button with ``set_style`` convenience method
    """

    def set_style(self, **attrs):
        """
        Set button CSS style
        :param attrs: key-value CSS pairs
        """
        if not attrs:
            return
        self.setStyleSheet(
            ";".join(
                f"{key.replace('_', '-')}: {value}" for key, value in attrs.items()
            )
        )


class WidthFilter(QSpinBox):
    """
    Spinbox for filtering images by width
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setSuffix(" pixels")
        self.setRange(0, 1e5)
        self.setValue(1000)
        self.setSingleStep(100)
        self.resize(10, 10)
