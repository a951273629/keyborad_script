"""把页面中的配置槽防抖保存回 config.toml。"""

import os
from pathlib import Path
import tempfile

from PySide6.QtCore import QObject, QTimer, Signal
import tomlkit

from config_loader import CONFIG, CONFIG_PATH
from models import WindowConfig


class ConfigRepository(QObject):
    save_failed = Signal(str)

    def __init__(self, windows: list[WindowConfig], path: Path = CONFIG_PATH) -> None:
        super().__init__()
        self.windows = windows
        self.path = path
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(CONFIG.game.save_debounce_ms)
        self.timer.timeout.connect(self.save_now)

    def request_save(self) -> None:
        # 连续编辑只在最后一次修改后写盘，避免每个按键都触发磁盘操作。
        self.timer.start()

    def save_now(self) -> None:
        self.timer.stop()
        try:
            document = tomlkit.parse(self.path.read_text(encoding="utf-8"))
            game = document.get("game")
            if game is None:
                raise ValueError("配置中缺少 [game] 表")
            game["windows"] = build_window_array(self.windows)
            atomic_write(self.path, tomlkit.dumps(document))
        except (OSError, ValueError, TypeError) as error:
            self.save_failed.emit(f"保存配置失败：{error}")


def build_window_array(windows: list[WindowConfig]):
    # 仅替换 game.windows，其他表、注释和顺序由 tomlkit 原样保留。
    items = tomlkit.aot()
    for window in windows:
        item = tomlkit.table()
        item.add("id", window.id)
        item.add("enabled", window.enabled)
        item.add("supply_enabled", window.supply.enabled)
        item.add("health_enabled", window.supply.health.enabled)
        item.add("health_threshold", window.supply.health.threshold)
        item.add("health_key", window.supply.health.key)
        item.add("energy_enabled", window.supply.energy.enabled)
        item.add("energy_threshold", window.supply.energy.threshold)
        item.add("energy_key", window.supply.energy.key)
        item.add("return_enabled", window.return_point.enabled)
        item.add("map_name", window.return_point.map_name)
        if window.return_point.x is not None:
            item.add("x", window.return_point.x)
        if window.return_point.y is not None:
            item.add("y", window.return_point.y)
        item.add("rules", build_rules(window))
        items.append(item)
    return items


def build_rules(window: WindowConfig):
    rules = tomlkit.array()
    rules.multiline(True)
    for rule in window.rules:
        item = tomlkit.inline_table()
        item.update({"enabled": rule.enabled, "key": rule.key, "interval": rule.interval})
        rules.append(item)
    return rules


def atomic_write(path: Path, content: str) -> None:
    # 临时文件与目标文件位于同一目录，os.replace 才能保证原子替换。
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise
