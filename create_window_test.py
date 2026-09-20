"""创建多个同名顶层窗口，供后续窗口枚举与绑定功能测试。"""

import argparse
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from config_loader import CONFIG


class TestWindow(QMainWindow):
    def __init__(self, index: int, total: int) -> None:
        super().__init__()
        # 系统标题不附加编号，确保窗口枚举可以测试同名窗口场景。
        self.setWindowTitle(CONFIG.test_window.title)
        self.resize(CONFIG.test_window.width, CONFIG.test_window.height)
        body = QWidget()
        layout = QVBoxLayout(body)
        self.label = QLabel(f"测试窗口 {index} / {total}")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 22px; font-weight: 600;")
        self.last_key = QLabel("最近收到的按键：无")
        self.last_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel(f"系统窗口标题：{CONFIG.test_window.title}")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #667377;")
        layout.addStretch()
        layout.addWidget(self.label)
        layout.addWidget(self.last_key)
        layout.addWidget(hint)
        layout.addStretch()
        self.setCentralWidget(body)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        # 显示收到的窗口消息，方便直接核对后台按键投递结果。
        shortcut = QKeySequence(event.keyCombination()).toString()
        self.last_key.setText(f"最近收到的按键：{shortcut}")
        super().keyPressEvent(event)


def validate_count(count: int) -> None:
    # 公共创建函数也执行范围检查，避免绕过命令行后创建异常数量。
    settings = CONFIG.test_window
    if settings.min_count <= count <= settings.max_count:
        return
    raise ValueError(f"窗口数量必须在 {settings.min_count} 到 {settings.max_count} 之间")


def position_window(window: TestWindow, index: int) -> None:
    # 窗口到达屏幕边缘后从可用区域起点回绕，保证标题栏仍可操作。
    screen = QApplication.primaryScreen()
    if not screen:
        return
    area = screen.availableGeometry()
    settings = CONFIG.test_window
    # 极小屏幕下收缩测试窗口，保证整个窗口仍留在可操作区域内。
    window.resize(min(settings.width, area.width()), min(settings.height, area.height()))
    x_range = max(1, area.width() - window.width() + 1)
    y_range = max(1, area.height() - window.height() + 1)
    x = area.left() + (index * settings.cascade_offset) % x_range
    y = area.top() + (index * settings.cascade_offset) % y_range
    window.move(x, y)


def create_test_windows(count: int) -> list[TestWindow]:
    # 返回窗口列表并由调用方持有，避免 Python 回收仍在显示的窗口。
    validate_count(count)
    if QApplication.instance() is None:
        raise RuntimeError("创建测试窗口前必须先创建 QApplication")
    windows: list[TestWindow] = []
    for index in range(count):
        window = TestWindow(index + 1, count)
        position_window(window, index)
        window.show()
        windows.append(window)
    return windows


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    settings = CONFIG.test_window
    parser = argparse.ArgumentParser(
        description=f"创建多个标题为 {settings.title!r} 的测试窗口。"
    )
    parser.add_argument("count", type=int, help="要创建的窗口数量")
    args = parser.parse_args(arguments)
    if not settings.min_count <= args.count <= settings.max_count:
        parser.error(f"count 必须在 {settings.min_count} 到 {settings.max_count} 之间")
    return args


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    # 参数已经由 argparse 处理，不再把 count 交给 Qt 二次解析。
    app = QApplication([sys.argv[0]])
    app.setQuitOnLastWindowClosed(True)
    # main 持有整个列表，逐个关闭窗口时不会影响其余测试窗口。
    windows = create_test_windows(args.count)
    return app.exec() if windows else 0


if __name__ == "__main__":
    sys.exit(main())
