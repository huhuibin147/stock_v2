# 开发规范

## 总则

1. **文档先行**: 任何模块开发前，必须先完成设计文档（docs/modules/xxx.md）
2. **文档同步**: 代码变更必须同步更新相关文档
3. **单一真相**: 文档是设计的唯一真相来源，代码实现文档描述的内容

---

## Python 后端规范

### 代码风格
- 遵循 PEP 8
- 使用 type hints（所有函数签名必须有类型标注）
- 使用 Pydantic 做数据校验
- 字符串统一用双引号 `"`

### 命名规范
```
模块名:     snake_case (collector_eastmoney.py)
类名:       PascalCase (EastMoneyCollector)
函数名:     snake_case (fetch_news_list)
常量:       UPPER_SNAKE_CASE (MAX_RETRY_COUNT)
私有属性:   _leading_underscore (_session)
```

### 项目结构
```
app/
├── api/
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── news.py          # 资讯相关接口
│   │   ├── stocks.py        # 股票相关接口
│   │   ├── analysis.py      # 分析相关接口
│   │   └── graph.py         # 图谱相关接口
│   └── deps.py              # 依赖注入
├── core/
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── security.py          # 认证安全
│   └── logging.py           # 日志配置
├── models/
│   ├── news.py              # 资讯ORM模型
│   ├── stock.py             # 股票ORM模型
│   └── event.py             # 事件ORM模型
├── schemas/
│   ├── news.py              # Pydantic请求/响应模型
│   ├── stock.py
│   └── common.py            # 通用schema
├── services/
│   ├── news_service.py      # 资讯业务逻辑
│   └── stock_service.py     # 股票业务逻辑
├── collectors/
│   ├── base.py              # 采集器基类
│   ├── eastmoney.py         # 东方财富采集
│   ├── cninfo.py            # 巨潮资讯采集
│   └── xueqiu.py            # 雪球采集
├── analyzers/
│   ├── entity_extractor.py  # 实体提取
│   ├── sentiment.py         # 情感分析
│   └── event_detector.py    # 事件检测
├── ai/
│   ├── summarizer.py        # 摘要生成
│   ├── qa.py                # 智能问答
│   └── prompts.py           # Prompt模板
└── main.py
```

### API设计规范
- RESTful风格
- 版本前缀: `/api/v1/`
- 分页参数: `page`(从1开始), `page_size`(默认20, 最大100)
- 响应格式:
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```
- 错误响应:
```json
{
  "code": 40001,
  "message": "参数错误: stock_code不能为空",
  "data": null
}
```

### 数据库规范
- 表名: 复数形式 `news`, `stocks`, `events`
- 主键: `id BIGSERIAL`
- 时间字段: `created_at`, `updated_at`，使用 `TIMESTAMPTZ`
- 软删除: `deleted_at TIMESTAMPTZ`
- JSONB字段用于半结构化数据，避免频繁JOIN

### 采集器规范
```python
class BaseCollector(ABC):
    """采集器基类"""

    @abstractmethod
    async def fetch_list(self, page: int = 1) -> list[RawNews]:
        """获取资讯列表"""

    @abstractmethod
    async def fetch_detail(self, source_id: str) -> RawNews:
        """获取资讯详情"""

    async def collect(self, max_pages: int = 5) -> list[RawNews]:
        """采集入口，含去重和限频"""
```

- 所有采集器继承 `BaseCollector`
- 必须实现限频逻辑（`asyncio.sleep`）
- 必须处理反爬（随机UA、代理、Cookie）
- 采集结果统一为 `RawNews` 格式

### 测试规范
- 测试目录: `tests/`
- 文件命名: `test_<module>.py`
- 使用 pytest + pytest-asyncio
- 采集器测试使用 `respx` / `pytest-httpx` mock外部请求
- 覆盖率目标: 核心逻辑 > 80%

---

## TypeScript 前端规范

### 代码风格
- 使用 ESLint + Prettier
- 严格模式 `"strict": true` in tsconfig
- 函数组件 + Hooks，不使用class组件
- 状态管理: Zustand

### 命名规范
```
组件文件:   PascalCase (NewsList.tsx)
工具函数:   camelCase (formatDate.ts)
类型定义:   PascalCase (NewsItem, StockInfo)
常量:       UPPER_SNAKE_CASE (API_BASE_URL)
CSS类名:    kebab-case (news-card, stock-detail)
```

### 组件结构
```
src/
├── components/           # 通用组件
│   ├── NewsCard/
│   │   ├── index.tsx
│   │   ├── styles.module.css
│   │   └── types.ts
│   └── StockTag/
├── pages/                # 页面组件
│   ├── Home/
│   ├── NewsFeed/
│   ├── StockDetail/
│   ├── Analysis/
│   └── Graph/
├── services/             # API调用
│   ├── api.ts            # axios实例
│   ├── news.ts
│   └── stock.ts
├── stores/               # Zustand状态
│   ├── newsStore.ts
│   └── stockStore.ts
├── hooks/                # 自定义Hooks
│   ├── useNews.ts
│   └── usePagination.ts
├── types/                # 类型定义
│   └── index.ts
├── utils/                # 工具函数
│   ├── format.ts
│   └── request.ts
└── App.tsx
```

### API调用规范
```typescript
// services/api.ts
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
});

// 请求拦截：自动携带token
// 响应拦截：统一错误处理
```

### 图谱可视化规范
- 常规图表（K线、柱状图、饼图）: ECharts
- 关联图谱（产业链、概念网络）: D3.js force-directed graph
- 图谱节点颜色:
  - 红色系: 利好/正面
  - 绿色系: 利空/负面（A股惯例）
  - 蓝色系: 中性
  - 灰色系: 待分析

---

## Git规范

### 分支策略
```
main          ← 生产分支
├── develop   ← 开发分支
│   ├── feature/xxx   ← 功能分支
│   ├── fix/xxx       ← 修复分支
│   └── refactor/xxx  ← 重构分支
```

### Commit规范
```
<type>(<scope>): <subject>

类型:
  feat:     新功能
  fix:      修复
  docs:     文档
  style:    格式调整
  refactor: 重构
  test:     测试
  chore:    构建/工具

示例:
  feat(collector): 新增东方财富采集器
  fix(analyzer): 修复实体识别空指针
  docs(api): 更新资讯接口文档
```

### PR规范
- 标题: 同commit规范
- 描述: 包含变更说明、测试情况、关联issue
- 必须通过CI检查
- 至少1人Code Review

---

## 环境管理

### 环境变量（.env）
```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/stock_v2
REDIS_URL=redis://localhost:6379/0
ES_URL=http://localhost:9200

# AI
ANTHROPIC_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx

# 采集
REQUEST_TIMEOUT=30
MAX_CONCURRENT=5
COLLECT_INTERVAL=300  # 采集间隔(秒)
```

### 配置管理
- 使用 `pydantic-settings` 管理配置
- 敏感信息只通过环境变量注入
- 不同环境使用 `.env`, `.env.local`, `.env.production`

---

## 日志规范

```python
import structlog

logger = structlog.get_logger()

# 结构化日志
logger.info("news_collected", source="eastmoney", count=50, duration=3.2)
logger.error("fetch_failed", source="cninfo", url="...", error=str(e))
```

- 使用 structlog 做结构化日志
- 必须记录: 采集结果、分析结果、AI调用、错误异常
- 日志级别: DEBUG(开发), INFO(生产), WARNING, ERROR
