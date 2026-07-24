"""策略基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Signal:
    """交易信号"""
    code: str
    name: str
    reason: str
    score: float  # 信号强度 0-100
    indicators: dict  # 相关指标


class BaseStrategy(ABC):
    """策略基类"""

    name: str = ""
    display_name: str = ""
    description: str = ""

    @abstractmethod
    async def scan(self, limit: int = 20) -> list[Signal]:
        """扫描全市场，返回符合条件的股票信号"""
        pass
