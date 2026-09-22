"""按键助手 UI 原型的启动入口。"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from styles import APP_STYLE


def main() -> int:
    # 主窗口内部管理扫描与按键定时器，Qt 事件循环保持它们持续运行。
    app = QApplication(sys.argv)
    app.setApplicationName("天龙小蜜按键助手")
    # 让窗口标题栏和任务栏使用与 EXE 相同的图标。
    icon_path = Path(__file__).resolve().parent / "assets" / "app.ico"
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
