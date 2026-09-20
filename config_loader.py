"""读取脚本目录中的 TOML 配置，并把字段转换为只读对象。"""

from dataclasses import dataclass
from pathlib import Path
import tomllib


CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"


class ConfigError(ValueError):
    """配置文件缺失字段或包含非法值。"""


@dataclass(frozen=True)
class KeyRuleSettings:
    min_interval: float
    max_interval: float
    default_interval: float
    interval_step: float
    interval_decimals: int


@dataclass(frozen=True)
class SupplySettings:
    min_threshold: int
    max_threshold: int
    default_threshold: int
    default_health_key: str
    default_energy_key: str


@dataclass(frozen=True)
class ReturnPointSettings:
    min_coordinate: int
    max_coordinate: int


@dataclass(frozen=True)
class TestWindowSettings:
    title: str
    min_count: int
    max_count: int
    width: int
    height: int
    cascade_offset: int


@dataclass(frozen=True)
class GameSettings:
    title_keywords: tuple[str, ...]
    scan_interval_ms: int
    scheduler_interval_ms: int
    key_hold_ms: int
    save_debounce_ms: int
    drag_hold_ms: int


@dataclass(frozen=True)
class GameRuleSettings:
    enabled: bool
    key: str
    interval: float


@dataclass(frozen=True)
class GameWindowSettings:
    identifier: str
    enabled: bool
    supply_enabled: bool
    health_enabled: bool
    health_threshold: int
    health_key: str
    energy_enabled: bool
    energy_threshold: int
    energy_key: str
    return_enabled: bool
    map_name: str
    x: int | None
    y: int | None
    rules: tuple[GameRuleSettings, ...]


@dataclass(frozen=True)
class AppConfig:
    key_rule: KeyRuleSettings
    supply: SupplySettings
    return_point: ReturnPointSettings
    test_window: TestWindowSettings
    game: GameSettings
    game_windows: tuple[GameWindowSettings, ...]


def table(data: dict, key: str, path: str = "") -> dict:
    value = data.get(key)
    name = f"{path}.{key}" if path else key
    if not isinstance(value, dict):
        raise ConfigError(f"{name} 必须是配置表")
    return value


def value(data: dict, key: str, expected: type, path: str):
    result = data.get(key)
    if expected is float and isinstance(result, (int, float)) and not isinstance(result, bool):
        return float(result)
    if expected is int and isinstance(result, int) and not isinstance(result, bool):
        return result
    if isinstance(result, expected):
        return result
    raise ConfigError(f"{path}.{key} 必须是 {expected.__name__} 类型")


def optional_int(data: dict, key: str, path: str) -> int | None:
    if key not in data:
        return None
    return value(data, key, int, path)


def check_range(minimum: int | float, maximum: int | float, path: str) -> None:
    if minimum > maximum:
        raise ConfigError(f"{path} 的最小值不能大于最大值")


def parse_key_rule(data: dict) -> KeyRuleSettings:
    item = table(data, "key_rule")
    result = KeyRuleSettings(
        value(item, "min_interval", float, "key_rule"), value(item, "max_interval", float, "key_rule"),
        value(item, "default_interval", float, "key_rule"), value(item, "interval_step", float, "key_rule"),
        value(item, "interval_decimals", int, "key_rule"),
    )
    check_range(result.min_interval, result.max_interval, "key_rule")
    if result.min_interval <= 0 or result.interval_step <= 0:
        raise ConfigError("按键间隔最小值和步长必须大于 0")
    if not result.min_interval <= result.default_interval <= result.max_interval:
        raise ConfigError("key_rule.default_interval 超出范围")
    if not 0 <= result.interval_decimals <= 6:
        raise ConfigError("key_rule.interval_decimals 必须在 0 到 6 之间")
    return result


def parse_supply(data: dict) -> SupplySettings:
    item = table(data, "supply")
    result = SupplySettings(
        value(item, "min_threshold", int, "supply"), value(item, "max_threshold", int, "supply"),
        value(item, "default_threshold", int, "supply"), value(item, "default_health_key", str, "supply"),
        value(item, "default_energy_key", str, "supply"),
    )
    if not 1 <= result.min_threshold <= result.default_threshold <= result.max_threshold <= 100:
        raise ConfigError("supply 百分比必须按顺序位于 1 到 100 之间")
    return result


def parse_return_point(data: dict) -> ReturnPointSettings:
    item = table(data, "return_point")
    result = ReturnPointSettings(value(item, "min_coordinate", int, "return_point"),
                                 value(item, "max_coordinate", int, "return_point"))
    check_range(result.min_coordinate, result.max_coordinate, "return_point")
    if result.min_coordinate < 0:
        raise ConfigError("return_point.min_coordinate 不能小于 0")
    return result


def parse_test_window(data: dict) -> TestWindowSettings:
    item = table(data, "test_window")
    result = TestWindowSettings(
        value(item, "title", str, "test_window"), value(item, "min_count", int, "test_window"),
        value(item, "max_count", int, "test_window"), value(item, "width", int, "test_window"),
        value(item, "height", int, "test_window"), value(item, "cascade_offset", int, "test_window"),
    )
    check_range(result.min_count, result.max_count, "test_window")
    if not result.title.strip() or min(result.min_count, result.width, result.height, result.cascade_offset) <= 0:
        raise ConfigError("test_window 标题不能为空，数值必须大于 0")
    return result


def parse_game(data: dict) -> GameSettings:
    item = table(data, "game")
    keywords = item.get("title_keywords")
    if not isinstance(keywords, list) or not keywords or not all(isinstance(word, str) and word for word in keywords):
        raise ConfigError("game.title_keywords 必须是非空字符串数组")
    result = GameSettings(
        tuple(keywords), value(item, "scan_interval_ms", int, "game"),
        value(item, "scheduler_interval_ms", int, "game"), value(item, "key_hold_ms", int, "game"),
        value(item, "save_debounce_ms", int, "game"), value(item, "drag_hold_ms", int, "game"),
    )
    if min(result.scan_interval_ms, result.scheduler_interval_ms, result.key_hold_ms,
           result.save_debounce_ms, result.drag_hold_ms) <= 0:
        raise ConfigError("game 的时间参数必须大于 0")
    return result


def parse_rule(data: dict, path: str, limits: KeyRuleSettings) -> GameRuleSettings:
    if not isinstance(data, dict):
        raise ConfigError(f"{path} 必须是配置表")
    result = GameRuleSettings(value(data, "enabled", bool, path), value(data, "key", str, path),
                              value(data, "interval", float, path))
    if not limits.min_interval <= result.interval <= limits.max_interval:
        raise ConfigError(f"{path}.interval 超出范围")
    return result


def parse_window(data: dict, index: int, key_limits: KeyRuleSettings,
                 supply_limits: SupplySettings, point_limits: ReturnPointSettings) -> GameWindowSettings:
    path = f"game.windows[{index}]"
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise ConfigError(f"{path} 及 rules 必须是正确的配置表和数组")
    result = GameWindowSettings(
        value(data, "id", str, path), value(data, "enabled", bool, path),
        value(data, "supply_enabled", bool, path), value(data, "health_enabled", bool, path),
        value(data, "health_threshold", int, path), value(data, "health_key", str, path),
        value(data, "energy_enabled", bool, path), value(data, "energy_threshold", int, path),
        value(data, "energy_key", str, path), value(data, "return_enabled", bool, path),
        value(data, "map_name", str, path), optional_int(data, "x", path), optional_int(data, "y", path),
        tuple(parse_rule(rule, f"{path}.rules[{i}]", key_limits) for i, rule in enumerate(data["rules"], 1)),
    )
    if not result.identifier.strip():
        raise ConfigError(f"{path}.id 不能为空")
    for threshold in (result.health_threshold, result.energy_threshold):
        if not supply_limits.min_threshold <= threshold <= supply_limits.max_threshold:
            raise ConfigError(f"{path} 的补给阈值超出范围")
    for coordinate in (result.x, result.y):
        if coordinate is not None and not point_limits.min_coordinate <= coordinate <= point_limits.max_coordinate:
            raise ConfigError(f"{path} 的坐标超出范围")
    return result


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    try:
        with path.open("rb") as file:
            data = tomllib.load(file)
    except FileNotFoundError as error:
        raise ConfigError(f"找不到配置文件：{path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"TOML 语法错误：{error}") from error
    key_rule = parse_key_rule(data)
    supply = parse_supply(data)
    point = parse_return_point(data)
    game_table = table(data, "game")
    raw_windows = game_table.get("windows")
    if not isinstance(raw_windows, list) or not raw_windows:
        raise ConfigError("game.windows 必须是非空配置表数组")
    windows = tuple(parse_window(item, i, key_rule, supply, point) for i, item in enumerate(raw_windows, 1))
    if len({item.identifier for item in windows}) != len(windows):
        raise ConfigError("game.windows 的 id 不能重复")
    return AppConfig(key_rule, supply, point, parse_test_window(data), parse_game(data), windows)


def load_required_config() -> AppConfig:
    try:
        return load_config()
    except (ConfigError, OSError) as error:
        raise SystemExit(f"配置错误：{error}") from error


CONFIG = load_required_config()
