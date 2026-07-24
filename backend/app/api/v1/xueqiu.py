"""雪球热度排行榜API"""

from fastapi import APIRouter
from app.core.response import ok
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/xueqiu", tags=["xueqiu"])


def _parse_rank_content(content: str) -> list[dict]:
    """解析排行榜内容，提取结构化数据"""
    import re
    results = []
    if not content:
        return results

    lines = content.strip().split("\n")
    for line in lines:
        # 跳过标题行
        if line.startswith("雪球") or not line.strip():
            continue

        # 解析格式: "1. 比亚迪(002594) 讨论:10.3万 价格:96.17"
        match = re.match(r'(\d+)\.\s+(.+?)\((\d+)\)\s+\w+:(.+?)\s+价格:(.+)', line)
        if match:
            rank = int(match.group(1))
            name = match.group(2).strip()
            code = match.group(3)
            count_str = match.group(4).strip()
            price_str = match.group(5).strip()

            # 解析热度值
            if count_str == '-':
                count = 0
            elif '万' in count_str:
                count = int(float(count_str.replace('万', '')) * 10000)
            else:
                count = int(count_str) if count_str.isdigit() else 0

            # 解析价格
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                price = None

            results.append({
                "rank": rank,
                "code": code,
                "name": name,
                "count": count,
                "price": price,
            })

    return results


@router.get("/ranking")
async def get_ranking():
    """获取雪球热度排行榜"""
    db = await get_db()
    try:
        # 获取最新的三条雪球数据（讨论、交易、关注）
        cursor = await db.execute(
            """SELECT source, title, content, published_at
               FROM news
               WHERE source IN ('xueqiu', 'xueqiu_deal', 'xueqiu_follow')
               AND id IN (
                   SELECT MAX(id) FROM news
                   WHERE source IN ('xueqiu', 'xueqiu_deal', 'xueqiu_follow')
                   GROUP BY source
               )"""
        )
        rows = await cursor.fetchall()

        result = {
            "update_time": None,
            "tweet_rank": [],
            "deal_rank": [],
            "follow_rank": [],
        }

        for row in rows:
            source, title, content, published_at = row

            # 解析排行榜数据
            rank_data = _parse_rank_content(content)

            if source == "xueqiu":
                result["tweet_rank"] = rank_data
                result["update_time"] = published_at
            elif source == "xueqiu_deal":
                result["deal_rank"] = rank_data
            elif source == "xueqiu_follow":
                result["follow_rank"] = rank_data

        # 格式化更新时间
        if result["update_time"]:
            result["update_time"] = result["update_time"].replace("T", " ")[:16]

        return ok(result)
    finally:
        await db.close()
