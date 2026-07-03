"""供应链信息采集器"""

import re
import json
from urllib.parse import quote

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()

# 搜索结果数据结构
SearchResult = dict


class SupplyChainCollector:
    """供应链信息采集器"""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=10,  # 减少超时时间
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
                follow_redirects=True,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search_supply_chain(self, company_name: str, company_code: str = None) -> list[SearchResult]:
        """搜索公司供应链信息"""
        results = []

        # 1. 搜索供应链相关新闻
        search_queries = [
            f"{company_name} 供应链",
            f"{company_name} 供应商",
            f"{company_name} 客户",
            f"{company_name} 研报",
            f"{company_name} 年报 供应商",
        ]

        for query in search_queries:
            search_results = await self._search_web(query)
            results.extend(search_results)

        # 2. 如果有股票代码，搜索东方财富公告和研报
        if company_code:
            announcement_results = await self._search_eastmoney_announcements(company_name, company_code)
            results.extend(announcement_results)

            research_results = await self._search_eastmoney_research(company_name, company_code)
            results.extend(research_results)

        # 3. 去重
        results = self._deduplicate(results)

        logger.info("supply_chain_search_completed", company=company_name, count=len(results))
        return results

    async def _search_web(self, query: str) -> list[SearchResult]:
        """搜索网页（使用多个源）"""
        results = []

        # 尝试必应搜索
        url = "https://www.bing.com/search"
        params = {"q": query, "count": 5}

        try:
            client = await self._get_client()
            response = await client.get(url, params=params, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9",
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 解析必应搜索结果
            for item in soup.select('.b_algo'):
                try:
                    title_elem = item.select_one('h2 a')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')

                    # 获取摘要
                    abstract_elem = item.select_one('.b_caption p')
                    abstract = abstract_elem.get_text(strip=True) if abstract_elem else ""

                    results.append({
                        "title": title,
                        "abstract": abstract,
                        "url": link,
                        "source": "bing",
                        "search_query": query,
                    })
                except Exception as e:
                    continue

        except Exception as e:
            logger.error("web_search_failed", query=query, error=str(e))

        return results[:3]  # 限制每个查询返回3条结果

    async def _search_eastmoney_announcements(self, company_name: str, company_code: str) -> list[SearchResult]:
        """搜索东方财富公告"""
        results = []

        # 东方财富公告搜索API
        url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        params = {
            "sr": "-1",
            "page_size": "10",
            "page_index": "1",
            "ann_type": "A",
            "stock_list": company_code,
            "f_node": "0",
            "s_node": "0",
        }

        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("success") and data.get("data", {}).get("list"):
                for item in data["data"]["list"]:
                    title = item.get("title", "")
                    # 过滤与供应链相关的公告
                    if self._is_supply_chain_related(title):
                        results.append({
                            "title": title,
                            "abstract": item.get("notice_content", "")[:200],
                            "url": f"https://data.eastmoney.com/notices/detail/{company_code}/{item.get('art_code', '')}.html",
                            "source": "eastmoney_ann",
                            "date": item.get("notice_date", ""),
                        })

        except Exception as e:
            logger.error("eastmoney_ann_search_failed", company=company_name, error=str(e))

        return results

    async def _search_eastmoney_research(self, company_name: str, company_code: str) -> list[SearchResult]:
        """搜索东方财富研报"""
        results = []

        # 东方财富研报搜索API
        url = "https://reportapi.eastmoney.com/report/list"
        params = {
            "industryCode": "*",
            "pageSize": "10",
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "",
            "endTime": "",
            "pageNo": "1",
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "code": company_code,
            "rcode": "",
            "p": "1",
            "pageNum": "1",
            "pageNumber": "1",
        }

        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            if data.get("data"):
                for item in data["data"]:
                    title = item.get("title", "")
                    # 过滤与供应链相关的研报
                    if self._is_supply_chain_related(title) or "供应链" in title or "产业链" in title:
                        results.append({
                            "title": title,
                            "abstract": item.get("content", "")[:200] if item.get("content") else "",
                            "url": f"https://data.eastmoney.com/report/zw/stock.jshtml?encodeUrl={item.get('encodeUrl', '')}",
                            "source": "eastmoney_research",
                            "date": item.get("publishDate", ""),
                            "org": item.get("orgSName", ""),  # 研报机构
                        })

        except Exception as e:
            logger.error("eastmoney_research_search_failed", company=company_name, error=str(e))

        return results

    def _is_relevant(self, title: str, abstract: str, keyword: str) -> bool:
        """判断搜索结果是否相关"""
        text = title + " " + abstract

        # 提取公司名称的核心部分（去掉"公司"、"集团"等后缀）
        company_core = keyword.split()[0]
        # 进一步提取，比如"长鑫存储" -> "长鑫"
        if len(company_core) > 2:
            company_core = company_core[:2]

        # 必须包含公司名称相关词
        if company_core not in text:
            return False

        # 供应链相关关键词
        supply_chain_keywords = [
            "供应链", "供应商", "客户", "采购", "销售", "合作",
            "上游", "下游", "配套", "配套商", "服务商",
            "原材料", "零部件", "设备", "终端", "应用",
            "厂商", "企业", "公司", "集团",
        ]

        return any(kw in text for kw in supply_chain_keywords)

    def _is_supply_chain_related(self, title: str) -> bool:
        """判断公告是否与供应链相关"""
        keywords = [
            "供应商", "客户", "采购", "销售", "合作", "合同",
            "订单", "中标", "配套", "供应链", "关联交易",
        ]
        return any(kw in title for kw in keywords)

    def _deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """去重"""
        seen = set()
        unique_results = []

        for result in results:
            # 使用标题作为去重键
            key = result.get("title", "")
            if key and key not in seen:
                seen.add(key)
                unique_results.append(result)

        return unique_results


class SupplyChainParser:
    """供应链信息解析器"""

    def extract_companies(self, search_results: list[SearchResult], target_name: str = "") -> list[dict]:
        """从搜索结果中提取公司信息"""
        companies = []

        # 目标公司核心词（用于排除自身）
        target_core = target_name[:2] if target_name else ""

        # 通用词汇黑名单
        blacklist = [
            "有限公司", "股份有限公司", "集团公司", "有限责任公司",
            "供应商", "采购商", "合作方", "客户方",
            "核心供应", "本土供应", "主要供应", "主要客户",
            "还是供应", "大核心", "家核心", "家本土",
        ]

        for result in search_results:
            title = result.get("title", "")
            abstract = result.get("abstract", "")
            text = title + " " + abstract

            # 提取公司名称（更严格的规则）
            # 匹配格式：XX公司、XX集团、XX科技、XX股份等
            # 要求前面必须是2-4个汉字的公司名
            company_patterns = [
                r'([一-龥]{2,4}(?:公司|集团|科技|股份|电子|机械|材料|能源|化工|医药|生物|半导|微电|集成|通信|智能|数据|网络))',
            ]

            for pattern in company_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # 过滤条件
                    if (len(match) >= 4 and  # 至少4个字（2字名+2字后缀）
                        match != target_name and
                        not match.startswith(target_core) and
                        match not in blacklist and
                        not any(bw in match for bw in blacklist)):
                        companies.append({
                            "name": match,
                            "source_title": title,
                            "source_url": result.get("url", ""),
                            "context": self._extract_context(text, match),
                        })

        # 去重并合并
        return self._merge_companies(companies)

    def _extract_context(self, text: str, company: str) -> str:
        """提取公司出现的上下文"""
        idx = text.find(company)
        if idx == -1:
            return ""

        start = max(0, idx - 50)
        end = min(len(text), idx + len(company) + 50)
        return text[start:end]

    def _merge_companies(self, companies: list[dict]) -> list[dict]:
        """合并重复的公司"""
        merged = {}

        for company in companies:
            name = company["name"]
            if name not in merged:
                merged[name] = {
                    "name": name,
                    "contexts": [],
                    "sources": set(),
                }
            merged[name]["contexts"].append(company.get("context", ""))
            if company.get("source_url"):
                merged[name]["sources"].add(company["source_url"])

        # 转换为列表
        result = []
        for name, info in merged.items():
            result.append({
                "name": info["name"],
                "contexts": info["contexts"][:3],  # 最多保留3个上下文
                "source_count": len(info["sources"]),
            })

        # 按出现次数排序
        result.sort(key=lambda x: x["source_count"], reverse=True)

        return result[:20]  # 最多返回20家公司


# 测试函数
async def test_supply_chain_collector():
    """测试供应链采集器"""
    collector = SupplyChainCollector()
    parser = SupplyChainParser()

    try:
        # 测试搜索长鑫存储
        results = await collector.search_supply_chain("长鑫存储", "CXMT")
        print(f"搜索结果数量: {len(results)}")

        for i, result in enumerate(results[:5]):
            print(f"\n--- 结果 {i+1} ---")
            print(f"标题: {result.get('title')}")
            print(f"摘要: {result.get('abstract', '')[:100]}...")
            print(f"来源: {result.get('source')}")

        # 解析公司
        companies = parser.extract_companies(results)
        print(f"\n提取的公司数量: {len(companies)}")

        for company in companies[:10]:
            print(f"- {company['name']} (出现{company['source_count']}次)")

    finally:
        await collector.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_supply_chain_collector())
