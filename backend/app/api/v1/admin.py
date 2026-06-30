import asyncio

from fastapi import APIRouter, Query, BackgroundTasks

from app.core.response import ok, fail
from app.services import admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── 数据查看 ──

@router.get("/status")
async def status():
    data = await admin_service.get_system_status()
    return ok(data)


@router.get("/logs")
async def logs(limit: int = Query(50, ge=1, le=200)):
    data = await admin_service.get_logs(limit)
    return ok(data)


@router.get("/stocks")
async def stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query(""),
):
    data = await admin_service.get_stocks_page(page, page_size, q)
    return ok(data)


@router.get("/news")
async def news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    data = await admin_service.get_news_page(page, page_size)
    return ok(data)


@router.get("/concepts")
async def concepts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    data = await admin_service.get_concepts_page(page, page_size)
    return ok(data)


# ── 手动触发操作 ──

@router.post("/import/stocks")
async def import_stocks(background_tasks: BackgroundTasks):
    """触发股票数据导入"""
    background_tasks.add_task(_run_import_stocks)
    return ok({"message": "股票导入任务已触发，请稍后查看日志"})


@router.post("/import/concepts")
async def import_concepts(background_tasks: BackgroundTasks):
    """触发概念板块导入"""
    background_tasks.add_task(_run_import_concepts)
    return ok({"message": "概念导入任务已触发，请稍后查看日志"})


@router.post("/import/concept-stocks")
async def import_concept_stocks(background_tasks: BackgroundTasks):
    """触发概念成分股关联导入"""
    background_tasks.add_task(_run_import_concept_stocks)
    return ok({"message": "概念成分股关联任务已触发，请稍后查看日志"})


@router.post("/collect/eastmoney")
async def collect_eastmoney(background_tasks: BackgroundTasks):
    """触发东方财富资讯采集"""
    background_tasks.add_task(_run_collect_eastmoney)
    return ok({"message": "东方财富采集任务已触发，请稍后查看日志"})


@router.post("/collect/ths")
async def collect_ths(background_tasks: BackgroundTasks):
    """触发同花顺资讯采集"""
    background_tasks.add_task(_run_collect_ths)
    return ok({"message": "同花顺采集任务已触发，请稍后查看日志"})


@router.post("/collect/sina")
async def collect_sina(background_tasks: BackgroundTasks):
    """触发新浪财经资讯采集"""
    background_tasks.add_task(_run_collect_sina)
    return ok({"message": "新浪财经采集任务已触发，请稍后查看日志"})


@router.post("/collect/cninfo")
async def collect_cninfo(background_tasks: BackgroundTasks):
    """触发巨潮公告采集"""
    background_tasks.add_task(_run_collect_cninfo)
    return ok({"message": "巨潮公告采集任务已触发，请稍后查看日志"})


@router.post("/collect/all")
async def collect_all(background_tasks: BackgroundTasks):
    """触发全部采集"""
    background_tasks.add_task(_run_collect_all)
    return ok({"message": "全部采集任务已触发，请稍后查看日志"})


@router.post("/import/profiles")
async def import_profiles(background_tasks: BackgroundTasks):
    """触发公司概况导入（core_business + industry）"""
    background_tasks.add_task(_run_import_profiles)
    return ok({"message": "公司概况导入任务已触发，请稍后查看日志"})


@router.post("/cleanup/news")
async def cleanup_news(days: int = Query(90, ge=1, le=365)):
    """清理N天前的旧资讯，返回删除条数"""
    from app.core.database import get_db
    db = await get_db()
    try:
        # 统计待删除
        cursor = await db.execute(
            "SELECT COUNT(*) FROM news WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        count = (await cursor.fetchone())[0]

        # 删除关联
        await db.execute(
            f"DELETE FROM news_stocks WHERE news_id IN (SELECT id FROM news WHERE created_at < datetime('now', ?))",
            (f"-{days} days",),
        )
        # 删除资讯
        await db.execute(
            "DELETE FROM news WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        await db.commit()
        await admin_service.log_action("cleanup_news", f"清理{days}天前资讯: 删除{count}条", "success")
        return ok({"deleted": count, "days": days})
    finally:
        await db.close()


@router.post("/import/valuation")
async def import_valuation(background_tasks: BackgroundTasks):
    """触发全市场估值数据更新"""
    background_tasks.add_task(_run_import_valuation)
    return ok({"message": "估值数据更新任务已触发"})


@router.post("/import/financials")
async def import_financials(background_tasks: BackgroundTasks, limit: int = Query(100, ge=1, le=500)):
    """触发财务数据采集"""
    background_tasks.add_task(_run_import_financials, limit)
    return ok({"message": f"财务数据采集任务已触发（最多{limit}只）"})


@router.post("/map/chains")
async def map_chains(background_tasks: BackgroundTasks):
    """触发产业链映射"""
    background_tasks.add_task(_run_map_chains)
    return ok({"message": "产业链映射任务已触发"})


# ── 后台任务 ──

async def _run_import_stocks():
    try:
        await admin_service.log_action("import_stocks", "开始导入", "running")
        from app.tasks.import_stocks import import_stocks
        await import_stocks()
        await admin_service.log_action("import_stocks", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_stocks", f"导入失败: {e}", "failed")


async def _run_import_concepts():
    try:
        await admin_service.log_action("import_concepts", "开始导入", "running")
        from app.tasks.import_stocks import import_concepts
        await import_concepts()
        await admin_service.log_action("import_concepts", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_concepts", f"导入失败: {e}", "failed")


async def _run_import_concept_stocks():
    try:
        await admin_service.log_action("import_concept_stocks", "开始导入", "running")
        from app.tasks.import_stocks import import_concept_stocks
        await import_concept_stocks()
        await admin_service.log_action("import_concept_stocks", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_concept_stocks", f"导入失败: {e}", "failed")


async def _run_collect_with(collector, action_name: str, max_pages: int = 3):
    """通用采集流程"""
    try:
        await admin_service.log_action(action_name, "开始采集", "running")

        from app.analyzers.entity_extractor import EntityExtractor
        from app.analyzers.sentiment import analyze_sentiment
        from app.analyzers.event_detector import detect_events
        from app.ai.summarizer import summarize
        from app.services.news_service import save_news

        extractor = EntityExtractor()
        raw_items = await collector.collect(max_pages=max_pages)
        saved = 0

        for item in raw_items:
            entities = await extractor.extract(item.title + " " + (item.content or ""))
            api_codes = item.extra.get("stock_codes", [])
            nlp_codes = [e.code for e in entities if e.type == "stock" and e.code]
            stock_codes = list(set(api_codes + nlp_codes))
            sentiment = analyze_sentiment(item.title)
            events = detect_events(item.title)
            ai_result = await summarize(item.title, item.content, item.source)

            news_data = {
                "source": item.source,
                "source_id": item.source_id,
                "title": item.title,
                "content": item.content or "",
                "summary": ai_result["summary"],
                "key_points": ai_result["key_points"],
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "category": item.category,
                "importance_score": item.extra.get("importance_score", 0.5),
                "sentiment": sentiment.label,
                "sentiment_score": sentiment.score,
                "entities": [{"type": e.type, "code": e.code, "name": e.name} for e in entities],
                "events": [{"type": ev.event_type, "subtype": ev.event_subtype, "impact": ev.impact} for ev in events],
                "tags": sentiment.keywords,
            }

            news_id = await save_news(news_data, stock_codes)
            if news_id:
                saved += 1

        await collector.close()
        detail = f"采集完成: 原始{len(raw_items)}条, 入库{saved}条"
        await admin_service.log_action(action_name, detail, "success")

    except Exception as e:
        await admin_service.log_action(action_name, f"采集失败: {e}", "failed")


async def _run_collect_eastmoney():
    from app.collectors.eastmoney import EastMoneyCollector
    await _run_collect_with(EastMoneyCollector(), "collect_eastmoney")


async def _run_collect_ths():
    from app.collectors.ths import THSCollector
    await _run_collect_with(THSCollector(), "collect_ths")


async def _run_collect_sina():
    from app.collectors.sina import SinaCollector
    await _run_collect_with(SinaCollector(), "collect_sina")


async def _run_collect_cninfo():
    from app.collectors.cninfo import CninfoCollector
    await _run_collect_with(CninfoCollector(), "collect_cninfo")


async def _run_collect_all():
    """全部源采集"""
    from app.collectors.eastmoney import EastMoneyCollector
    from app.collectors.ths import THSCollector
    from app.collectors.sina import SinaCollector
    from app.collectors.cninfo import CninfoCollector

    for name, cls in [
        ("collect_eastmoney", EastMoneyCollector),
        ("collect_ths", THSCollector),
        ("collect_sina", SinaCollector),
        ("collect_cninfo", CninfoCollector),
    ]:
        await _run_collect_with(cls(), name, max_pages=2)


async def _run_import_profiles():
    try:
        await admin_service.log_action("import_profiles", "开始导入公司概况", "running")
        from app.tasks.import_stocks import import_stock_profiles
        await import_stock_profiles()
        await admin_service.log_action("import_profiles", "导入完成", "success")
    except Exception as e:
        await admin_service.log_action("import_profiles", f"导入失败: {e}", "failed")


async def _run_import_valuation():
    try:
        await admin_service.log_action("import_valuation", "开始更新估值数据", "running")
        from app.tasks.import_fundamentals import import_valuation
        await import_valuation()
        await admin_service.log_action("import_valuation", "估值数据更新完成", "success")
    except Exception as e:
        await admin_service.log_action("import_valuation", f"更新失败: {e}", "failed")


async def _run_import_financials(limit: int = 100):
    try:
        await admin_service.log_action("import_financials", f"开始采集财务数据（{limit}只）", "running")
        from app.tasks.import_fundamentals import import_financials_batch
        await import_financials_batch(limit=limit)
        await admin_service.log_action("import_financials", "财务数据采集完成", "success")
    except Exception as e:
        await admin_service.log_action("import_financials", f"采集失败: {e}", "failed")


async def _run_map_chains():
    try:
        await admin_service.log_action("map_chains", "开始产业链映射", "running")
        from app.tasks.map_chains import map_stocks_to_chains
        await map_stocks_to_chains()
        await admin_service.log_action("map_chains", "产业链映射完成", "success")
    except Exception as e:
        await admin_service.log_action("map_chains", f"映射失败: {e}", "failed")
