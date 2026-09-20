"""使用 Win32 API 查找目标顶层窗口。"""

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import os


@dataclass(frozen=True)
class DiscoveredWindow:
    hwnd: int
    title: str


class WindowDiscovery:
    def __init__(self, keywords: tuple[str, ...]) -> None:
        self.keywords = tuple(word.casefold() for word in keywords)
        self.user32 = ctypes.windll.user32 if os.name == "nt" else None
        self.configure_api()

    def configure_api(self) -> None:
        # 明确声明参数宽度，避免 64 位系统中的 HWND 被按 32 位整数截断。
        if self.user32 is None:
            return
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL

    def scan(self) -> list[DiscoveredWindow]:
        if self.user32 is None:
            return []
        windows: list[DiscoveredWindow] = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def collect(hwnd: int, _parameter: int) -> bool:
            window = self.read_window(hwnd)
            if window is not None:
                windows.append(window)
            return True

        callback = callback_type(collect)
        self.user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.EnumWindows(callback, 0)
        return windows

    def read_window(self, hwnd: int) -> DiscoveredWindow | None:
        if not self.user32.IsWindowVisible(hwnd):
            return None
        length = self.user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return None
        buffer = ctypes.create_unicode_buffer(length + 1)
        self.user32.GetWindowTextW(hwnd, buffer, length + 1)
        title = buffer.value.strip()
        if not title or not any(word in title.casefold() for word in self.keywords):
            return None
        return DiscoveredWindow(int(hwnd), title)

    def is_alive(self, hwnd: int) -> bool:
        if self.user32 is None:
            return False
        return bool(self.user32.IsWindow(hwnd))
