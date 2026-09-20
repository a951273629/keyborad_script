"""真实窗口自动绑定、配置编辑和后台按键的主界面。"""

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QPushButton, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)

from config_loader import CONFIG
from config_repository import ConfigRepository
from key_engine import KeyEngine, validate_shortcut
from models import WindowConfig, initial_windows, new_window_config, validate_start
from pages import KeyPage, ReturnPage, SupplyPage
from window_backend import DiscoveredWindow, WindowDiscovery


class DraggableWindowList(QListWidget):
    order_changed = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.press_position = QPoint()
        self.source_row = -1
        self.left_pressed = False
        self.drag_armed = False
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.left_pressed = True
        self.drag_armed = False
        self.press_position = event.position().toPoint()
        pressed_item = self.itemAt(self.press_position)
        self.source_row = self.row(pressed_item) if pressed_item else -1
        QTimer.singleShot(CONFIG.game.drag_hold_ms, self.arm_drag)

    def arm_drag(self) -> None:
        if not self.left_pressed or self.source_row < 0:
            return
        self.drag_armed = True
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        # 交换在松开时一次完成，移动过程中不反复重建列表。
        if not self.left_pressed:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        target_item = self.itemAt(event.position().toPoint())
        target_row = self.row(target_item)
        should_swap = self.drag_armed and target_row >= 0 and target_row != self.source_row
        source_row = self.source_row
        self.left_pressed = False
        self.drag_armed = False
        self.source_row = -1
        self.viewport().unsetCursor()
        super().mouseReleaseEvent(event)
        if not should_swap:
            return
        handles = self.handle_order()
        handles[source_row], handles[target_row] = handles[target_row], handles[source_row]
        self.order_changed.emit(handles)

    def handle_order(self) -> list[int]:
        return [int(self.item(index).data(Qt.ItemDataRole.UserRole)) for index in range(self.count())]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("天龙小蜜按键助手")
        self.resize(1180, 760)
        self.setMinimumSize(960, 640)
        self.configs = initial_windows()
        self.discovered: list[DiscoveredWindow] = []
        self.selected_hwnd: int | None = None
        self.running = False
        self.refreshing_list = False
        self.discovery = WindowDiscovery(CONFIG.game.title_keywords)
        self.repository = ConfigRepository(self.configs)
        self.repository.save_failed.connect(lambda message: self.show_banner(message, True))
        self.engine = KeyEngine()
        self.engine.send_failed.connect(lambda message: self.show_banner(message, True))
        self.build_ui()
        self.scan_timer = QTimer(self)
        self.scan_timer.setInterval(CONFIG.game.scan_interval_ms)
        self.scan_timer.timeout.connect(self.scan_windows)
        self.scan_windows()
        self.scan_timer.start()

    def build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        vertical = QVBoxLayout(root)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(0)
        vertical.addWidget(self.make_toolbar())
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.make_sidebar())
        body.addWidget(self.make_content(), 1)
        vertical.addLayout(body, 1)

    def make_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topBar")
        bar.setFixedHeight(74)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(26, 0, 26, 0)
        title = QLabel("天龙小蜜按键助手")
        title.setObjectName("appTitle")
        layout.addWidget(title)
        # subtitle = QLabel("真实窗口绑定")
        # subtitle.setObjectName("mutedText")
        layout.addSpacing(13)
        # layout.addWidget(subtitle)
        layout.addStretch()
        self.status = QLabel("●  未启动")
        self.status.setObjectName("statusIdle")
        layout.addWidget(self.status)
        layout.addSpacing(18)
        self.run_button = QPushButton("启动")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self.toggle_running)
        layout.addWidget(self.run_button)
        return bar

    def make_sidebar(self) -> QFrame:
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(300)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(16, 23, 16, 18)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        title = QLabel("已绑定窗口")
        title.setObjectName("sidebarTitle")
        self.count = QLabel("0 个")
        self.count.setObjectName("mutedText")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.count)
        layout.addLayout(heading)
        # self.refresh_button = QPushButton("↻  立即扫描")
        # self.refresh_button.clicked.connect(self.scan_windows)
        # layout.addWidget(self.refresh_button)
        self.window_list = DraggableWindowList()
        self.window_list.itemSelectionChanged.connect(self.select_list_item)
        self.window_list.itemChanged.connect(self.change_window_enabled)
        self.window_list.order_changed.connect(self.reorder_windows)
        layout.addWidget(self.window_list, 1)
        keywords = "、".join(CONFIG.game.title_keywords)
        self.scan_hint = QLabel(f"自动查找标题包含“{keywords}”的窗口\n长按窗口后可拖动换位")
        self.scan_hint.setObjectName("mutedText")
        self.scan_hint.setWordWrap(True)
        layout.addWidget(self.scan_hint)
        return side

    def make_content(self) -> QFrame:
        content = QFrame()
        content.setObjectName("content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.banner = QLabel()
        self.banner.setContentsMargins(28, 8, 28, 0)
        self.banner.setVisible(False)
        layout.addWidget(self.banner)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.make_empty_page())
        self.stack.addWidget(self.make_editor())
        layout.addWidget(self.stack, 1)
        return content

    def make_empty_page(self) -> QWidget:
        empty = QWidget()
        layout = QVBoxLayout(empty)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("正在查找目标窗口")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        keywords = "、".join(CONFIG.game.title_keywords)
        description = QLabel(f"请启动标题包含“{keywords}”的窗口，列表会自动更新。")
        description.setObjectName("mutedText")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(description)
        return empty

    def make_editor(self) -> QWidget:
        editor = QWidget()
        layout = QVBoxLayout(editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(28, 22, 28, 15)
        self.editor_title = QLabel()
        self.editor_title.setObjectName("sidebarTitle")
        self.editor_state = QLabel()
        self.editor_state.setObjectName("mutedText")
        header.addWidget(self.editor_title)
        header.addStretch()
        header.addWidget(self.editor_state)
        layout.addLayout(header)
        self.tabs = QTabWidget()
        self.key_page = KeyPage()
        self.supply_page = SupplyPage()
        self.supply_page.connect_inputs()
        self.return_page = ReturnPage()
        for page in (self.key_page, self.supply_page, self.return_page):
            page.config_changed.connect(self.configuration_changed)
        self.tabs.addTab(self.key_page, "按键设置")
        self.tabs.addTab(self.supply_page, "自动补给")
        self.tabs.addTab(self.return_page, "死亡回点")
        layout.addWidget(self.tabs, 1)
        return editor

    def scan_windows(self) -> None:
        scanned = self.discovery.scan()
        scanned_by_handle = {window.hwnd: window for window in scanned}
        survivors = [scanned_by_handle[item.hwnd] for item in self.discovered if item.hwnd in scanned_by_handle]
        survivor_handles = {item.hwnd for item in survivors}
        added = [item for item in scanned if item.hwnd not in survivor_handles]
        updated = [*survivors, *added]
        old_state = [(item.hwnd, item.title) for item in self.discovered]
        new_state = [(item.hwnd, item.title) for item in updated]
        if new_state == old_state:
            return
        self.discovered = updated
        self.ensure_config_slots()
        if self.selected_hwnd not in {item.hwnd for item in self.discovered}:
            self.selected_hwnd = self.discovered[0].hwnd if self.discovered else None
        self.refresh_window_list()
        self.show_selection()
        self.sync_engine()

    def ensure_config_slots(self) -> None:
        changed = False
        while len(self.configs) < len(self.discovered):
            used_ids = {item.id for item in self.configs}
            self.configs.append(new_window_config(len(self.configs) + 1, used_ids))
            changed = True
        if changed:
            self.repository.request_save()

    def refresh_window_list(self) -> None:
        self.refreshing_list = True
        self.window_list.clear()
        self.count.setText(f"{len(self.discovered)} 个")
        for index, window in enumerate(self.discovered):
            config = self.configs[index]
            item = QListWidgetItem(f"{window.title}\n窗口 {index + 1} · 使用配置 {index + 1}")
            item.setData(Qt.ItemDataRole.UserRole, window.hwnd)
            item.setCheckState(Qt.CheckState.Checked if config.enabled else Qt.CheckState.Unchecked)
            flags = item.flags() | Qt.ItemFlag.ItemIsDragEnabled
            if not self.running:
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            else:
                flags &= ~Qt.ItemFlag.ItemIsUserCheckable
            item.setFlags(flags)
            item.setToolTip(f"句柄：{window.hwnd}\n长按后拖动可交换配置位置")
            self.window_list.addItem(item)
            if window.hwnd == self.selected_hwnd:
                item.setSelected(True)
        self.refreshing_list = False

    def select_list_item(self) -> None:
        items = self.window_list.selectedItems()
        if not items:
            return
        self.selected_hwnd = int(items[0].data(Qt.ItemDataRole.UserRole))
        self.show_selection()

    def current_binding(self) -> tuple[int, DiscoveredWindow, WindowConfig] | None:
        for index, window in enumerate(self.discovered):
            if window.hwnd == self.selected_hwnd:
                return index, window, self.configs[index]
        return None

    def show_selection(self) -> None:
        binding = self.current_binding()
        if binding is None:
            self.stack.setCurrentIndex(0)
            return
        index, window, config = binding
        self.stack.setCurrentIndex(1)
        self.editor_title.setText(f"{window.title} · 窗口 {index + 1}")
        self.editor_state.setText(f"使用配置 {index + 1} · {'已启用' if config.enabled else '已停用'}")
        editable = not self.running
        self.key_page.configure(config, editable)
        self.supply_page.configure(config, editable)
        self.return_page.configure(config, editable)

    def change_window_enabled(self, item: QListWidgetItem) -> None:
        if self.refreshing_list or self.running:
            return
        hwnd = int(item.data(Qt.ItemDataRole.UserRole))
        index = next((i for i, window in enumerate(self.discovered) if window.hwnd == hwnd), None)
        if index is None:
            return
        self.configs[index].enabled = item.checkState() == Qt.CheckState.Checked
        self.repository.request_save()
        self.show_selection()
        self.sync_engine()

    def reorder_windows(self, handles: list[int]) -> None:
        current = {window.hwnd: window for window in self.discovered}
        if set(handles) != set(current):
            return
        self.discovered = [current[handle] for handle in handles]
        self.refresh_window_list()
        self.show_selection()
        self.sync_engine()
        self.show_banner("窗口顺序已调整，固定配置已按新位置立即应用。", False)

    def configuration_changed(self) -> None:
        self.repository.request_save()
        self.sync_engine()

    def bindings(self) -> list[tuple[DiscoveredWindow, WindowConfig]]:
        return [(window, self.configs[index]) for index, window in enumerate(self.discovered)]

    def validate_shortcuts(self) -> str | None:
        for index, (window, config) in enumerate(self.bindings(), 1):
            if not config.enabled:
                continue
            for rule_index, rule in enumerate(config.rules, 1):
                if rule.enabled and not validate_shortcut(rule.key):
                    return f"窗口 {index}（{window.title}）第 {rule_index} 条快捷键无法识别"
        return None

    def toggle_running(self) -> None:
        if self.running:
            self.engine.stop()
            self.running = False
            self.update_running_ui()
            self.show_banner("后台按键已停止。", False)
            return
        named = [(f"窗口 {index + 1}（{window.title}）", config)
                 for index, (window, config) in enumerate(self.bindings())]
        error = validate_start(named) or self.validate_shortcuts()
        if error:
            self.show_banner(error, True)
            return
        self.running = True
        self.engine.start(self.bindings())
        self.update_running_ui()
        self.show_banner("后台按键运行中，不会主动切换前台窗口。", False)

    def sync_engine(self) -> None:
        if not self.running:
            return
        self.engine.update_bindings(self.bindings())

    def update_running_ui(self) -> None:
        self.status.setText("●  运行中" if self.running else "●  未启动")
        self.status.setObjectName("statusRunning" if self.running else "statusIdle")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.run_button.setText("停止" if self.running else "启动")
        self.run_button.setObjectName("stopButton" if self.running else "primaryButton")
        self.run_button.style().unpolish(self.run_button)
        self.run_button.style().polish(self.run_button)
        self.refresh_window_list()
        self.show_selection()

    def show_banner(self, message: str, error: bool) -> None:
        self.banner.setText(message)
        self.banner.setObjectName("errorBanner" if error else "successBanner")
        self.banner.style().unpolish(self.banner)
        self.banner.style().polish(self.banner)
        self.banner.setVisible(True)

    def closeEvent(self, event) -> None:
        # 退出前释放按键并立即写入尚在防抖等待中的配置。
        self.engine.stop()
        if self.repository.timer.isActive():
            self.repository.save_now()
        super().closeEvent(event)
