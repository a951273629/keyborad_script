"""按键助手 UI 原型的启动入口。"""

import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from styles import APP_STYLE


def main() -> int:
    # 主窗口内部管理扫描与按键定时器，Qt 事件循环保持它们持续运行。
    app = QApplication(sys.argv)
    app.setApplicationName("天龙小蜜按键助手")
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
