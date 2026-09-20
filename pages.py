"""当前窗口的按键、自动补给和死亡回点三个配置页。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from config_loader import CONFIG
from models import KeyRule, WindowConfig
from widgets import KeyCapture, section_heading


def scroll_page() -> tuple[QWidget, QVBoxLayout]:
    # 页签的内容可滚动，最小窗口尺寸下不会挤压输入框。
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    area = QScrollArea()
    area.setWidgetResizable(True)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(28, 26, 28, 24)
    layout.setSpacing(22)
    area.setWidget(body)
    outer.addWidget(area)
    return page, layout


class KeyPage(QWidget):
    config_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.window: WindowConfig | None = None
        self.editable = True
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        page, self.body = scroll_page()
        layout.addWidget(page)
        header = QHBoxLayout()
        header.addWidget(section_heading("按键设置", "为当前窗口配置循环按键和执行间隔。"))
        header.addStretch()
        self.add_button = QPushButton("＋  添加按键")
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self.add_rule)
        header.addWidget(self.add_button)
        self.body.addLayout(header)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(0)
        self.body.addLayout(self.rows)
        self.body.addStretch()

    def configure(self, window: WindowConfig, editable: bool) -> None:
        # 切换窗口时重新生成行，输入事件始终写入当前窗口的数据。
        self.window = window
        self.editable = editable
        self.add_button.setEnabled(editable)
        self.rebuild_rows()

    def rebuild_rows(self) -> None:
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                # 先隐藏再延迟删除，避免快速切换窗口时旧行短暂残留。
                item.widget().hide()
                item.widget().deleteLater()
        self.rows.addWidget(self.make_header())
        if not self.window:
            return
        if not self.window.rules:
            empty = QLabel("还没有按键规则。点击右上角添加第一条规则。")
            empty.setObjectName("mutedText")
            empty.setContentsMargins(14, 22, 0, 22)
            self.rows.addWidget(empty)
        for rule in self.window.rules:
            self.rows.addWidget(self.make_row(rule))

    def make_header(self) -> QFrame:
        # 表头与数据行使用相同的四列比例，便于逐行扫描。
        frame = QFrame()
        frame.setObjectName("ruleHeader")
        grid = QGridLayout(frame)
        grid.setContentsMargins(16, 8, 16, 8)
        for column, (text, stretch) in enumerate((("启用", 1), ("按键", 3), ("间隔（秒）", 3), ("操作", 1))):
            grid.addWidget(QLabel(text), 0, column)
            grid.setColumnStretch(column, stretch)
        return frame

    def make_row(self, rule: KeyRule) -> QFrame:
        frame = QFrame()
        frame.setObjectName("ruleRow")
        grid = QGridLayout(frame)
        grid.setContentsMargins(16, 10, 16, 10)
        grid.setHorizontalSpacing(16)
        enabled = QCheckBox()
        enabled.setChecked(rule.enabled)
        enabled.setToolTip("启用这条按键规则")
        enabled.setEnabled(self.editable)
        enabled.toggled.connect(lambda value: self.change_rule(rule, "enabled", value))
        key = KeyCapture(rule.key)
        key.setEnabled(self.editable)
        key.key_changed.connect(lambda value: self.change_rule(rule, "key", value))
        interval = QDoubleSpinBox()
        interval.setRange(CONFIG.key_rule.min_interval, CONFIG.key_rule.max_interval)
        interval.setDecimals(CONFIG.key_rule.interval_decimals)
        interval.setSingleStep(CONFIG.key_rule.interval_step)
        interval.setValue(rule.interval)
        interval.setEnabled(self.editable)
        interval.valueChanged.connect(lambda value: self.change_rule(rule, "interval", value))
        remove = QPushButton("×")
        remove.setObjectName("iconButton")
        remove.setToolTip("删除这条按键规则")
        remove.setAccessibleName("删除按键规则")
        remove.setEnabled(self.editable)
        remove.clicked.connect(lambda: self.remove_rule(rule))
        for column, (widget, stretch) in enumerate(((enabled, 1), (key, 3), (interval, 3), (remove, 1))):
            grid.addWidget(widget, 0, column, Qt.AlignmentFlag.AlignLeft if column in (0, 3) else Qt.AlignmentFlag(0))
            grid.setColumnStretch(column, stretch)
        return frame

    def add_rule(self) -> None:
        if not self.window or not self.editable:
            return
        self.window.rules.append(KeyRule(key=""))
        self.rebuild_rows()
        self.config_changed.emit()

    def remove_rule(self, rule: KeyRule) -> None:
        if not self.window or not self.editable:
            return
        self.window.rules.remove(rule)
        self.rebuild_rows()
        self.config_changed.emit()

    def change_rule(self, rule: KeyRule, field: str, value: bool | float | str) -> None:
        if not self.window or not self.editable:
            return
        setattr(rule, field, value)
        self.config_changed.emit()


class SupplyPage(QWidget):
    config_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.window: WindowConfig | None = None
        self.editable = True
        self.loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        page, self.body = scroll_page()
        layout.addWidget(page)
        self.body.addWidget(section_heading("自动补给", "按当前窗口的血量和气量阈值设置对应快捷键。"))
        self.master = QCheckBox("启用自动补给")
        self.master.setObjectName("fieldLabel")
        self.master.toggled.connect(self.update_master)
        self.body.addWidget(self.master)
        self.health_controls = self.make_supply_row("血", "healthAccent", "补血")
        self.energy_controls = self.make_supply_row("气", "energyAccent", "补气")
        self.note = QLabel("当前为界面原型，尚未接入血量与气量识别。")
        self.note.setObjectName("hint")
        self.note.setWordWrap(True)
        self.body.addWidget(self.note)
        self.body.addStretch()

    def make_supply_row(self, name: str, accent: str, action: str) -> tuple[QCheckBox, QSpinBox, KeyCapture]:
        # 一行就是一句完整操作条件，减少参考图中的重复字段标签。
        frame = QFrame()
        frame.setObjectName("featureRow")
        row = QHBoxLayout(frame)
        row.setContentsMargins(4, 18, 4, 18)
        row.setSpacing(10)
        check = QCheckBox()
        check.setToolTip(f"单独启用{action}")
        label = QLabel(f"{name}量低于")
        label.setObjectName(accent)
        threshold = QSpinBox()
        threshold.setRange(CONFIG.supply.min_threshold, CONFIG.supply.max_threshold)
        threshold.setSuffix(" %")
        threshold.setFixedWidth(100)
        key = KeyCapture()
        key.setMaximumWidth(180)
        for widget in (check, label, threshold, QLabel("时，按下"), key, QLabel(action)):
            row.addWidget(widget)
        row.addStretch()
        self.body.addWidget(frame)
        return check, threshold, key

    def configure(self, window: WindowConfig, editable: bool) -> None:
        self.loading = True
        self.window = window
        self.editable = editable
        self.master.setChecked(window.supply.enabled)
        for name, controls in (("health", self.health_controls), ("energy", self.energy_controls)):
            rule = getattr(window.supply, name)
            check, threshold, key = controls
            check.setChecked(rule.enabled)
            threshold.setValue(rule.threshold)
            key.setText(rule.key)
        self.refresh_enabled()
        self.loading = False

    def update_master(self, value: bool) -> None:
        if not self.window or self.loading:
            return
        self.window.supply.enabled = value
        self.refresh_enabled()
        self.config_changed.emit()

    def refresh_enabled(self) -> None:
        if not self.window:
            return
        self.master.setEnabled(self.editable)
        for name, controls in (("health", self.health_controls), ("energy", self.energy_controls)):
            check, threshold, key = controls
            check.setEnabled(self.editable and self.window.supply.enabled)
            active = self.editable and self.window.supply.enabled and check.isChecked()
            threshold.setEnabled(active)
            key.setEnabled(active)

    def connect_inputs(self) -> None:
        # 信号只连接一次；切换窗口后由 self.window 指向当前配置。
        for name, controls in (("health", self.health_controls), ("energy", self.energy_controls)):
            check, threshold, key = controls
            check.toggled.connect(lambda value, field=name: self.change_rule(field, "enabled", value))
            threshold.valueChanged.connect(lambda value, field=name: self.change_rule(field, "threshold", value))
            key.key_changed.connect(lambda value, field=name: self.change_rule(field, "key", value))

    def change_rule(self, name: str, field: str, value: bool | int | str) -> None:
        if not self.window or self.loading:
            return
        setattr(getattr(self.window.supply, name), field, value)
        if field == "enabled":
            self.refresh_enabled()
        self.config_changed.emit()


class ReturnPage(QWidget):
    config_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.window: WindowConfig | None = None
        self.editable = True
        self.loading = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        page, self.body = scroll_page()
        layout.addWidget(page)
        self.body.addWidget(section_heading("死亡回点", "设置当前窗口死亡后要返回的挂机位置。"))
        self.master = QCheckBox("启用死亡自动回点")
        self.master.toggled.connect(self.update_master)
        self.body.addWidget(self.master)
        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.addWidget(QLabel("场景地图名称"), 0, 0, 1, 2)
        self.map_name = QLineEdit()
        self.map_name.setPlaceholderText("例如：洛阳城")
        self.map_name.setMaxLength(80)
        form.addWidget(self.map_name, 1, 0, 1, 2)
        form.addWidget(QLabel("X 坐标"), 2, 0)
        form.addWidget(QLabel("Y 坐标"), 2, 1)
        self.x = self.make_coordinate()
        self.y = self.make_coordinate()
        form.addWidget(self.x, 3, 0)
        form.addWidget(self.y, 3, 1)
        form.setColumnStretch(0, 1)
        form.setColumnStretch(1, 1)
        self.body.addLayout(form)
        self.preview = QLabel()
        self.preview.setObjectName("preview")
        self.body.addWidget(self.preview)
        self.validation = QLabel()
        self.validation.setObjectName("healthAccent")
        self.body.addWidget(self.validation)
        note = QLabel("当前为界面原型，尚未接入死亡检测、地图识别与自动寻路。")
        note.setObjectName("hint")
        note.setWordWrap(True)
        self.body.addWidget(note)
        self.body.addStretch()
        self.map_name.textChanged.connect(self.update_map)
        self.x.valueChanged.connect(lambda value: self.update_coordinate("x", value))
        self.y.valueChanged.connect(lambda value: self.update_coordinate("y", value))

    def make_coordinate(self) -> QSpinBox:
        # 最小坐标前一位是界面内部的“未设置”，不会写成真实坐标。
        field = QSpinBox()
        field.setRange(CONFIG.return_point.min_coordinate - 1, CONFIG.return_point.max_coordinate)
        field.setSpecialValueText("未设置")
        field.setValue(CONFIG.return_point.min_coordinate - 1)
        return field

    def configure(self, window: WindowConfig, editable: bool) -> None:
        self.loading = True
        self.window = window
        self.editable = editable
        point = window.return_point
        self.master.setChecked(point.enabled)
        self.map_name.setText(point.map_name)
        empty_value = CONFIG.return_point.min_coordinate - 1
        self.x.setValue(empty_value if point.x is None else point.x)
        self.y.setValue(empty_value if point.y is None else point.y)
        self.refresh_enabled()
        self.refresh_preview()
        self.loading = False

    def update_master(self, value: bool) -> None:
        if not self.window or self.loading:
            return
        self.window.return_point.enabled = value
        self.refresh_enabled()
        self.refresh_preview()
        self.config_changed.emit()

    def update_map(self, value: str) -> None:
        if not self.window or self.loading:
            return
        self.window.return_point.map_name = value
        self.refresh_preview()
        self.config_changed.emit()

    def update_coordinate(self, field: str, value: int) -> None:
        if not self.window or self.loading:
            return
        minimum = CONFIG.return_point.min_coordinate
        setattr(self.window.return_point, field, None if value < minimum else value)
        self.refresh_preview()
        self.config_changed.emit()

    def refresh_enabled(self) -> None:
        if not self.window:
            return
        self.master.setEnabled(self.editable)
        active = self.editable and self.window.return_point.enabled
        for widget in (self.map_name, self.x, self.y):
            widget.setEnabled(active)

    def refresh_preview(self) -> None:
        if not self.window:
            return
        point = self.window.return_point
        complete = bool(point.map_name.strip()) and point.x is not None and point.y is not None
        self.validation.setVisible(point.enabled and not complete)
        self.validation.setText("请填写地图名称和完整的 X/Y 坐标。")
        if not complete:
            self.preview.setText("目标挂机点：尚未设置完整")
            return
        self.preview.setText(f"目标挂机点：{point.map_name.strip()}（{point.x}, {point.y}）")
