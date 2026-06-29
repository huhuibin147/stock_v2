# 分析模块设计

## 模块职责

对通过重要度过滤的资讯进行NLP处理，提取结构化信息。**分析结果即为最终存储内容**，原始全文不入库。

## 处理流水线

```
重要资讯(内存) → 预处理 → 实体识别 → 情感分析 → 事件检测 → 关联计算 → 整合结果入库
                                                                            ↓
                                                                    title + summary
                                                                    + entities + events
                                                                    + sentiment
                                                                    （不存原始content）
```

## 实体识别

### 实体类型
| 类型 | 示例 | 提取方式 |
|------|------|----------|
| STOCK | 贵州茅台(600519) | 正则匹配股票代码/名称 |
| INDUSTRY | 半导体、新能源 | 行业词典匹配 |
| CONCEPT | ChatGPT、HBM、CPO | 概念词典匹配 |
| PERSON | 黄仁勋、任正非 | 人名词典+NER |
| POLICY | 《新一代AI发展规划》 | 正则+规则 |
| COMPANY | 英伟达、台积电 | 公司词典匹配 |

### 实现方案
```python
class EntityExtractor:
    def __init__(self):
        self.stock_dict = load_stock_dict()     # 股票代码/名称映射
        self.concept_dict = load_concept_dict()  # 概念词典
        self.nlp = spacy.load("zh_core_web_trf") # 预训练NER

    async def extract(self, text: str) -> list[Entity]:
        entities = []
        # 1. 正则匹配股票代码 (6位数字)
        # 2. 词典匹配股票名称、概念、行业
        # 3. NER提取人名、机构名
        # 4. 去重合并，计算置信度
        return entities
```

## 情感分析

### 方案
1. **规则层**: 关键词匹配（利好/利空词汇表）
2. **模型层**: 预训练情感模型（BERT/ERNIE微调）
3. **LLM层**: Claude API复杂场景判断

### 输出
```python
@dataclass
class SentimentResult:
    label: int          # -1利空, 0中性, 1利好
    score: float        # 置信度 0~1
    keywords: list[str] # 触发关键词
    method: str         # rule/model/llm
```

### 分级策略
- 简单场景（含明确利好/利空词）→ 规则层
- 中等场景 → 模型层
- 复杂场景（反讽、隐含、多事件混合）→ LLM层

## 事件检测

### 事件分类体系
```
performance/
├── pre_increase    业绩预增
├── pre_decrease    业绩预减
├── loss            业绩亏损
└── turnaround      业绩扭亏

merger/
├── acquisition     收购
├── restructuring   重组
└── spin_off        分拆

equity/
├── buyback         回购
├── incentive       股权激励
├── top_up          增持
└── top_down        减持

policy/
├── subsidy         补贴
├── regulation      监管
└── industry_plan   产业规划

risk/
├── violation       违规
├── lawsuit         诉讼
├── rating_down     评级下调
└── penalty         处罚
```

### 检测方案
```python
class EventDetector:
    async def detect(self, text: str, entities: list) -> list[Event]:
        events = []
        # 1. 模板匹配: "公司预计XX年度净利润同比增长XX%" → pre_increase
        # 2. 关键词+实体组合: "增持" + 大股东实体 → top_up
        # 3. LLM辅助: 复杂公告的事件提取
        return events
```

## 关联计算

### 股票-资讯关联
- **直接提及**: 文中出现股票代码或名称
- **间接关联**: 提及同行业、同概念的其他股票
- **产业链传导**: 上下游公司的关联影响

### 关联度计算
```python
def calculate_relevance(news_entity: str, stock: Stock) -> float:
    # 直接提及: 1.0
    # 同概念: 0.7
    # 同行业: 0.5
    # 产业链上下游: 0.3
    pass
```

## 词典维护

| 词典 | 内容 | 更新频率 |
|------|------|----------|
| stock_dict.json | 股票代码↔名称映射 | 每日 |
| concept_dict.json | 概念术语及同义词 | 每周 |
| sentiment_positive.json | 正面情感词 | 每月 |
| sentiment_negative.json | 负面情感词 | 每月 |
| event_templates.json | 事件模板 | 每月 |
| industry_chain.json | 产业链关系 | 每月 |
