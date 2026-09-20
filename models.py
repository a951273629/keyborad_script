"""界面原型使用的内存数据与启动前校验。"""

from dataclasses import dataclass, field

from config_loader import CONFIG, GameWindowSettings


@dataclass
class KeyRule:
    # 每条按键规则可以单独停用，停用后仍保留输入内容。
    enabled: bool = True
    key: str = ""
    interval: float = CONFIG.key_rule.default_interval


@dataclass
class SupplyRule:
    # 血和气使用相同的数据结构，但各自保存阈值与快捷键。
    enabled: bool = True
    threshold: int = CONFIG.supply.default_threshold
    key: str = ""


@dataclass
class SupplyConfig:
    enabled: bool = False
    health: SupplyRule = field(
        default_factory=lambda: SupplyRule(key=CONFIG.supply.default_health_key)
    )
    energy: SupplyRule = field(
        default_factory=lambda: SupplyRule(key=CONFIG.supply.default_energy_key)
    )


@dataclass
class ReturnConfig:
    enabled: bool = False
    map_name: str = ""
    x: int | None = None
    y: int | None = None


@dataclass
class WindowConfig:
    # 配置属于固定槽位，不属于某个会变化的真实窗口句柄。
    id: str
    enabled: bool = True
    rules: list[KeyRule] = field(default_factory=list)
    supply: SupplyConfig = field(default_factory=SupplyConfig)
    return_point: ReturnConfig = field(default_factory=ReturnConfig)


def make_window_config(settings: GameWindowSettings) -> WindowConfig:
    # TOML 中的只读配置需要复制为页面可以编辑的内存模型。
    window = WindowConfig(settings.identifier, settings.enabled)
    window.rules = [KeyRule(rule.enabled, rule.key, rule.interval) for rule in settings.rules]
    window.supply.enabled = settings.supply_enabled
    window.supply.health = SupplyRule(
        settings.health_enabled, settings.health_threshold, settings.health_key
    )
    window.supply.energy = SupplyRule(
        settings.energy_enabled, settings.energy_threshold, settings.energy_key
    )
    window.return_point = ReturnConfig(
        settings.return_enabled, settings.map_name, settings.x, settings.y
    )
    return window


def initial_windows() -> list[WindowConfig]:
    # 数组位置就是窗口配置槽的位置，加载时保持 TOML 顺序。
    return [make_window_config(item) for item in CONFIG.game_windows]


def new_window_config(index: int, existing_ids: set[str] | None = None) -> WindowConfig:
    # 新发现的真实窗口超过现有槽位时使用业务默认值扩展配置。
    used = existing_ids or set()
    candidate = index
    while f"game-{candidate}" in used:
        candidate += 1
    return WindowConfig(f"game-{candidate}", enabled=False)


def validate_window(window: WindowConfig, display_name: str) -> str | None:
    # 只检查启用的功能；关闭的配置可以暂时不完整。
    active = False
    for index, rule in enumerate(window.rules, start=1):
        if not rule.enabled:
            continue
        limits = CONFIG.key_rule
        if not rule.key or not limits.min_interval <= rule.interval <= limits.max_interval:
            return f"{display_name}：第 {index} 条按键规则不完整"
        active = True
    if window.supply.enabled:
        for name, rule in (("补血", window.supply.health), ("补气", window.supply.energy)):
            if not rule.enabled:
                continue
            limits = CONFIG.supply
            if not rule.key or not limits.min_threshold <= rule.threshold <= limits.max_threshold:
                return f"{display_name}：{name}阈值或快捷键不完整"
            active = True
    if window.return_point.enabled:
        point = window.return_point
        if not point.map_name.strip() or point.x is None or point.y is None:
            return f"{display_name}：请填写挂机点地图和 X/Y 坐标"
        limits = CONFIG.return_point
        if not limits.min_coordinate <= point.x <= limits.max_coordinate:
            return f"{display_name}：挂机点坐标超出范围"
        if not limits.min_coordinate <= point.y <= limits.max_coordinate:
            return f"{display_name}：挂机点坐标超出范围"
        active = True
    if not active:
        return f"{display_name}：至少启用一项有效功能"
    return None


def validate_start(bindings: list[tuple[str, WindowConfig]]) -> str | None:
    # 启动只验证已绑定且启用的配置槽。
    enabled_bindings = [(name, config) for name, config in bindings if config.enabled]
    if not enabled_bindings:
        return "请先发现并启用至少一个目标窗口"
    for name, config in enabled_bindings:
        error = validate_window(config, name)
        if error:
            return error
    return None
