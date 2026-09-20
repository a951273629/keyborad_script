"""按配置间隔向已绑定窗口发送后台 Win32 按键消息。"""

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os
import time

from PySide6.QtCore import QObject, QTimer, Signal

from config_loader import CONFIG
from models import WindowConfig
from window_backend import DiscoveredWindow


WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_NAMES = {
    "ESC": 0x1B, "ESCAPE": 0x1B, "TAB": 0x09, "ENTER": 0x0D, "RETURN": 0x0D,
    "SPACE": 0x20, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "CTRL": 0x11, "CONTROL": 0x11, "ALT": 0x12, "SHIFT": 0x10,
}
MODIFIER_ORDER = ("CTRL", "ALT", "SHIFT")


@dataclass
class PendingRelease:
    deadline: float
    hwnd: int
    keys: tuple[int, ...]
    system_key: bool


def key_to_vk(name: str) -> int | None:
    normalized = name.strip().upper()
    if normalized in VK_NAMES:
        return VK_NAMES[normalized]
    if normalized.startswith("F") and normalized[1:].isdigit():
        number = int(normalized[1:])
        return 0x6F + number if 1 <= number <= 24 else None
    if len(normalized) == 1 and normalized.isascii() and normalized.isalnum():
        return ord(normalized)
    return None


def parse_shortcut(shortcut: str) -> tuple[tuple[int, ...], bool] | None:
    parts = [part.strip().upper() for part in shortcut.split("+") if part.strip()]
    if not parts:
        return None
    main_name = parts[-1]
    modifiers = parts[:-1]
    if main_name in MODIFIER_ORDER or any(name not in MODIFIER_ORDER for name in modifiers):
        return None
    if len(set(modifiers)) != len(modifiers):
        return None
    main_key = key_to_vk(main_name)
    if main_key is None:
        return None
    ordered = [VK_NAMES[name] for name in MODIFIER_ORDER if name in modifiers]
    return tuple([*ordered, main_key]), "ALT" in modifiers


def validate_shortcut(shortcut: str) -> bool:
    return parse_shortcut(shortcut) is not None


class KeyEngine(QObject):
    send_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.user32 = ctypes.windll.user32 if os.name == "nt" else None
        self.configure_api()
        self.bindings: list[tuple[DiscoveredWindow, WindowConfig]] = []
        self.next_runs: dict[tuple[int, int], float] = {}
        self.pending: list[PendingRelease] = []
        self.failed_handles: set[int] = set()
        self.running = False
        self.timer = QTimer(self)
        self.timer.setInterval(CONFIG.game.scheduler_interval_ms)
        self.timer.timeout.connect(self.tick)

    def configure_api(self) -> None:
        # HWND 和消息参数在 64 位 Windows 上必须使用对应的 Win32 类型。
        if self.user32 is None:
            return
        self.user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.user32.PostMessageW.restype = wintypes.BOOL
        self.user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
        self.user32.MapVirtualKeyW.restype = wintypes.UINT

    def start(self, bindings: list[tuple[DiscoveredWindow, WindowConfig]]) -> None:
        self.stop()
        self.running = True
        self.update_bindings(bindings)
        self.timer.start()

    def stop(self) -> None:
        self.timer.stop()
        self.release_all()
        self.running = False
        self.bindings = []
        self.next_runs.clear()
        self.failed_handles.clear()

    def update_bindings(self, bindings: list[tuple[DiscoveredWindow, WindowConfig]]) -> None:
        # 排序或窗口变化时先释放旧组合键，再从当前时刻重新计算周期。
        self.release_all()
        self.bindings = list(bindings)
        self.next_runs.clear()
        now = time.monotonic()
        for discovered, config in self.bindings:
            for index, rule in enumerate(config.rules):
                self.next_runs[(discovered.hwnd, index)] = now + rule.interval

    def tick(self) -> None:
        if not self.running:
            return
        now = time.monotonic()
        self.release_due(now)
        for discovered, config in self.bindings:
            self.run_window(discovered, config, now)

    def run_window(self, discovered: DiscoveredWindow, config: WindowConfig, now: float) -> None:
        if not config.enabled or discovered.hwnd in self.failed_handles:
            return
        for index, rule in enumerate(config.rules):
            if not rule.enabled:
                continue
            schedule_key = (discovered.hwnd, index)
            if now < self.next_runs.get(schedule_key, now):
                continue
            self.next_runs[schedule_key] = now + rule.interval
            parsed = parse_shortcut(rule.key)
            if parsed is None:
                continue
            keys, system_key = parsed
            if not self.press(discovered, keys, system_key):
                return

    def press(self, window: DiscoveredWindow, keys: tuple[int, ...], system_key: bool) -> bool:
        if self.user32 is None:
            self.fail_window(window, "当前系统不支持 Win32 后台按键")
            return False
        for key in keys:
            if self.post(window.hwnd, key, True, system_key):
                continue
            self.release_keys(window.hwnd, tuple(reversed(keys)), system_key)
            self.fail_window(window, "PostMessageW 发送失败")
            return False
        deadline = time.monotonic() + CONFIG.game.key_hold_ms / 1000
        self.pending.append(PendingRelease(deadline, window.hwnd, tuple(reversed(keys)), system_key))
        return True

    def post(self, hwnd: int, key: int, down: bool, system_key: bool) -> bool:
        message = WM_SYSKEYDOWN if system_key and down else WM_SYSKEYUP if system_key else WM_KEYDOWN if down else WM_KEYUP
        scan_code = self.user32.MapVirtualKeyW(key, 0)
        parameter = 1 | (scan_code << 16)
        if system_key:
            # 系统按键消息通过第 29 位告诉目标窗口 Alt 正处于按下状态。
            parameter |= 1 << 29
        if not down:
            parameter |= (1 << 30) | (1 << 31)
        return bool(self.user32.PostMessageW(hwnd, message, key, parameter))

    def release_due(self, now: float) -> None:
        remaining: list[PendingRelease] = []
        for item in self.pending:
            if item.deadline > now:
                remaining.append(item)
                continue
            self.release_keys(item.hwnd, item.keys, item.system_key)
        self.pending = remaining

    def release_keys(self, hwnd: int, keys: tuple[int, ...], system_key: bool) -> None:
        if self.user32 is None:
            return
        for key in keys:
            self.post(hwnd, key, False, system_key)

    def release_all(self) -> None:
        for item in self.pending:
            self.release_keys(item.hwnd, item.keys, item.system_key)
        self.pending.clear()

    def fail_window(self, window: DiscoveredWindow, reason: str) -> None:
        self.failed_handles.add(window.hwnd)
        self.send_failed.emit(f"{window.title}（句柄 {window.hwnd}）：{reason}")
