"""策略管理器"""

from app.strategies.base import BaseStrategy, Signal
from app.strategies.bottom_break import BottomBreakStrategy
from app.strategies.shrink_rise import ShrinkRiseStrategy
from app.strategies.value_roe import ValueROEStrategy
from app.strategies.strong_yang import StrongYangStrategy
from app.strategies.platform_break import PlatformBreakStrategy


class StrategyManager:
    """策略管理器"""

    def __init__(self):
        self._strategies: dict[str, BaseStrategy] = {}
        self._register_default()

    def _register_default(self):
        """注册默认策略"""
        self.register(BottomBreakStrategy())
        self.register(ShrinkRiseStrategy())
        self.register(ValueROEStrategy())
        self.register(StrongYangStrategy())
        self.register(PlatformBreakStrategy())

    def register(self, strategy: BaseStrategy):
        """注册策略"""
        self._strategies[strategy.name] = strategy

    def get_strategy(self, name: str) -> BaseStrategy | None:
        """获取策略"""
        return self._strategies.get(name)

    def list_strategies(self) -> list[dict]:
        """列出所有策略"""
        return [
            {
                "name": s.name,
                "display_name": s.display_name,
                "description": s.description,
            }
            for s in self._strategies.values()
        ]

    async def run_all(self, limit: int = 20) -> dict[str, list[Signal]]:
        """运行所有策略"""
        results = {}
        for name, strategy in self._strategies.items():
            try:
                signals = await strategy.scan(limit)
                results[name] = signals
            except Exception as e:
                results[name] = []
        return results

    async def run_strategy(self, name: str, limit: int = 20) -> list[Signal]:
        """运行指定策略"""
        strategy = self._strategies.get(name)
        if not strategy:
            return []
        return await strategy.scan(limit)


# 全局策略管理器实例
strategy_manager = StrategyManager()
