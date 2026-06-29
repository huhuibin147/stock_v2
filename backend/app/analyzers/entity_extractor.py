import re
import json
from dataclasses import dataclass, field

import structlog

from app.core.database import get_db

logger = structlog.get_logger()


@dataclass
class Entity:
    type: str  # stock / concept
    code: str = ""
    name: str = ""

    @property
    def key(self) -> str:
        return f"{self.type}:{self.code or self.name}"


class EntityExtractor:
    """轻量实体提取器：正则+词典匹配，不依赖大模型"""

    def __init__(self):
        self._code_to_name: dict[str, str] = {}
        self._name_to_code: dict[str, str] = {}
        self._name_sorted: list[tuple[str, str]] = []  # (name, code) 按名称长度降序
        self._concepts: list[str] = []
        self._loaded = False

    async def load(self):
        """从数据库加载股票和概念词典"""
        db = await get_db()
        try:
            # 股票词典
            cursor = await db.execute("SELECT code, name FROM stocks WHERE is_active = 1")
            rows = await cursor.fetchall()
            self._code_to_name = {r[0]: r[1] for r in rows}
            self._name_to_code = {r[1]: r[0] for r in rows}
            self._name_sorted = sorted(self._name_to_code.items(), key=lambda x: -len(x[0]))

            # 概念词典
            cursor = await db.execute("SELECT name FROM concepts")
            rows = await cursor.fetchall()
            self._concepts = [r[0] for r in rows]

            self._loaded = True
            logger.info("entity_extractor_loaded", stocks=len(self._code_to_name), concepts=len(self._concepts))
        finally:
            await db.close()

    async def extract(self, text: str) -> list[Entity]:
        if not self._loaded:
            await self.load()

        seen: set[str] = set()
        entities: list[Entity] = []

        # 1. 正则匹配6位股票代码
        for code in re.findall(r"[036]\d{5}", text):
            if code in self._code_to_name and code not in seen:
                seen.add(code)
                entities.append(Entity(type="stock", code=code, name=self._code_to_name[code]))

        # 2. 股票名称匹配（长名优先，避免短名误匹配）
        for name, code in self._name_sorted:
            if len(name) < 2:
                continue
            if name in text and code not in seen:
                seen.add(code)
                entities.append(Entity(type="stock", code=code, name=name))

        # 3. 概念词典匹配
        for concept in self._concepts:
            if len(concept) < 2:
                continue
            if concept in text and f"concept:{concept}" not in seen:
                seen.add(f"concept:{concept}")
                entities.append(Entity(type="concept", name=concept))

        return entities
