"""多个页面共用的输入控件和简洁标题组件。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget


class KeyCapture(QLineEdit):
    key_changed = Signal(str)

    def __init__(self, value: str = "") -> None:
        super().__init__(value)
        # 输入框只接收真实按键，清除操作交给右侧内置清除按钮。
        self.setReadOnly(True)
        self.setClearButtonEnabled(True)
        self.setPlaceholderText("点击后按快捷键")
        self.setToolTip("点击输入框后按下按键或组合键；点击右侧图标清除")
        self.setMinimumWidth(116)
        self.textChanged.connect(self.key_changed.emit)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # 单独按修饰键时等待下一个键，避免保存 Ctrl 等不完整组合。
        modifiers = event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.KeyboardModifier.ShiftModifier
            | Qt.KeyboardModifier.MetaModifier
        )
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            return
        if event.key() == Qt.Key.Key_unknown:
            return
        sequence = QKeySequence(int(modifiers.value) | event.key())
        self.setText(sequence.toString(QKeySequence.SequenceFormat.PortableText))
        event.accept()


def section_heading(title: str, detail: str) -> QWidget:
    # 标题与辅助信息组成固定的页面开头，减少各页面重复布局。
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(5)
    heading = QLabel(title)
    heading.setObjectName("sectionTitle")
    description = QLabel(detail)
    description.setObjectName("mutedText")
    description.setWordWrap(True)
    layout.addWidget(heading)
    layout.addWidget(description)
    return container
