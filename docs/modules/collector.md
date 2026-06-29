# 采集模块设计

## 模块职责

多源数据采集、**重要度过滤**、去重、标准化，**只保留有价值的资讯，丢弃噪音**。

## 设计原则：只存重要的

原始资讯量极大（各源合计日均数千条），但真正有分析价值的不到20%。采用**漏斗式过滤**：

```
原始采集(全量) → 去重 → 重要度过滤(丢弃噪音) → 分析处理 → 只存整合后的结果
                     ↑                                    ↑
                  布隆过滤器                           摘要+结构化数据
                  标题相似度                           不存原始全文
```

**核心策略：**
1. 采集时全量抓取（需要全量数据做去重和判断），但**内存中过滤**，不落盘
2. 只有通过重要度过滤的资讯才写入数据库
3. 存储时**不保留原始全文**，只保留标题 + AI摘要 + 结构化分析结果
4. 过期数据定期归档清理（默认保留90天）

## 数据源清单

### 第一优先级（核心）
| 来源 | 类型 | 采集方式 | 频率 |
|------|------|----------|------|
| 东方财富 | 新闻+快讯 | API/网页 | 5分钟 |
| 巨潮资讯 | 公告 | API | 10分钟 |
| 雪球 | 讨论+热帖 | API | 10分钟 |

### 第二优先级（补充）
| 来源 | 类型 | 采集方式 | 频率 |
|------|------|----------|------|
| 同花顺 | 新闻 | 网页 | 10分钟 |
| 新浪财经 | 新闻 | API | 10分钟 |
| 证券时报 | 新闻 | RSS/网页 | 15分钟 |

### 第三优先级（基础数据）
| 来源 | 类型 | 采集方式 | 频率 |
|------|------|----------|------|
| AKShare | 股票列表/概念板块/行情 | Python库调用（免费） | 每日/每周 |
| 东方财富 | 行情/资金流 | API爬取 | 按需 |

## 采集器架构

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RawNews:
    """采集器输出的标准化原始资讯（内存临时对象，不直接落盘）"""
    source: str              # 来源标识
    source_id: str           # 来源原始ID
    title: str               # 标题
    content: str | None      # 正文（仅用于分析，不入库）
    url: str                 # 原始链接
    published_at: datetime   # 发布时间
    category: str            # news/announcement/social/policy
    extra: dict              # 来源特有字段


class BaseCollector(ABC):
    """采集器基类"""

    source: str
    base_url: str
    rate_limit: float = 1.0  # 请求间隔(秒)

    async def collect(self, max_pages: int = 5) -> list[RawNews]:
        """采集入口：全量采集 → 去重 → 重要度过滤 → 只返回有价值的条目"""
        raw_items = []
        for page in range(1, max_pages + 1):
            items = await self.fetch_list(page)
            if not items:
                break
            raw_items.extend(items)
            await asyncio.sleep(self.rate_limit)

        # 去重（内存中）
        deduped = await self._deduplicate(raw_items)

        # 重要度过滤（核心：大量丢弃噪音）
        important = await self._filter_important(deduped)

        return important

    async def _filter_important(self, items: list[RawNews]) -> list[RawNews]:
        """重要度过滤：丢弃无分析价值的资讯"""
        filtered = []
        for item in items:
            score = self._calc_importance(item)
            if score >= IMPORTANCE_THRESHOLD:
                item.extra["importance_score"] = score
                filtered.append(item)
        return filtered

    def _calc_importance(self, item: RawNews) -> float:
        """计算重要度分数 0~1，低于阈值(0.5)直接丢弃"""
        score = 0.0
        title = item.title or ""

        # 涉及上市公司（标题含6位股票代码或已知公司名称）+0.3
        if re.search(r'[036]\d{5}', title) or self._match_stock_name(title):
            score += 0.3

        # 涉及重大事件关键词 +0.3
        EVENT_KEYWORDS = {"并购", "重组", "收购", "业绩", "预增", "预减", "亏损",
                          "增持", "减持", "回购", "涨停", "跌停", "处罚", "退市",
                          "合同", "中标", "专利", "股权激励", "分红"}
        if any(kw in title for kw in EVENT_KEYWORDS):
            score += 0.3

        # 来源权重：公告 > 新闻 > 社交
        source_weight = {"announcement": 0.2, "policy": 0.2, "news": 0.1, "social": 0.05}
        score += source_weight.get(item.category, 0.05)

        # 标题过短降权
        if len(title) < 10:
            score -= 0.1

        return min(max(score, 0.0), 1.0)

    @abstractmethod
    async def fetch_list(self, page: int) -> list[RawNews]:
        """获取资讯列表页"""

    @abstractmethod
    async def fetch_detail(self, source_id: str) -> RawNews:
        """获取资讯详情"""

    async def _request(self, url: str, **kwargs) -> httpx.Response:
        """带限频和重试的请求方法"""
        ...
```

## 重要度过滤规则

### 必存（直接保留）
- 上市公司公告（巨潮资讯来源，category=announcement）
- 涉及明确股票代码/名称的资讯
- 包含重大事件关键词：并购、重组、业绩预增/预减、增持、减持、回购、涨停、跌停、处罚、退市

### 加权保留（综合打分）
- 政策类资讯（央行、证监会、发改委发文）
- 行业重大变动（产能、价格、技术突破）
- 多股票关联（影响面广）

### 直接丢弃
- 无明确标的的泛泛而谈
- 纯广告/推广内容
- 重复/相似资讯（标题编辑距离 > 0.9）
- 过短内容（标题 < 10字且无股票实体）
- 社交媒体水贴/情绪宣泄

### 过滤效果预估
```
原始采集: ~5000条/天
去重后:   ~3000条/天
重要度过滤后: ~500~800条/天  ← 只有这部分入库
存储压缩率: ~85%
```

## 去重策略

1. **DB唯一约束**: `news(source, source_id)` UNIQUE索引，插入时自动去重
2. **内存集合**: 启动时加载已有source_id到内存set，O(1)判断
3. **标题相似度**: 编辑距离 > 0.9 视为重复（内存中处理）

## 调度机制

APScheduler 进程内调度，无需单独worker：

```python
# app/scheduler.py
scheduler = AsyncIOScheduler()
scheduler.add_job(collect_eastmoney, "interval", minutes=5)
scheduler.add_job(collect_cninfo, "interval", minutes=10)
scheduler.add_job(cleanup_expired, "cron", hour=3)  # 凌晨3点清理过期数据
```

## 反爬策略

- 随机User-Agent轮换
- 请求间隔随机化（1~3秒）
- 代理IP池（可选）
- Cookie自动维护
- 失败重试（指数退避，最多3次）

## 错误处理

- 采集失败: 记录日志，跳过当前页，继续下一页
- 连续失败5次: 告警通知，暂停该源采集
- 数据异常: 校验字段完整性，缺失关键字段丢弃
