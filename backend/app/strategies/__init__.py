"""量化策略模块"""

from app.strategies.base import BaseStrategy, Signal
from app.strategies.bottom_break import BottomBreakStrategy
from app.strategies.shrink_rise import ShrinkRiseStrategy
from app.strategies.value_roe import ValueROEStrategy
from app.strategies.strong_yang import StrongYangStrategy
from app.strategies.platform_break import PlatformBreakStrategy
from app.strategies.manager import StrategyManager

__all__ = [
    "BaseStrategy",
    "Signal",
    "BottomBreakStrategy",
    "ShrinkRiseStrategy",
    "ValueROEStrategy",
    "StrongYangStrategy",
    "PlatformBreakStrategy",
    "StrategyManager",
]
