"""供应链挖掘API"""

from fastapi import APIRouter, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from app.core.response import ok, fail
from app.services import supply_chain_service

router = APIRouter(prefix="/api/v1/supply-chain", tags=["supply-chain"])


class ResearchCreate(BaseModel):
    target_type: str  # 'company' 或 'industry'
    target_name: str
    target_code: Optional[str] = None


class ResearchUpdate(BaseModel):
    target_type: Optional[str] = None
    target_name: Optional[str] = None
    target_code: Optional[str] = None
    status: Optional[str] = None
    result_summary: Optional[str] = None


@router.get("")
async def list_research(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    target_type: str = Query(None),
    status: str = Query(None),
):
    """获取研究任务列表"""
    data = await supply_chain_service.get_research_list(page, page_size, target_type, status)
    return ok(data)


@router.get("/recent")
async def recent_research(limit: int = Query(5, ge=1, le=20)):
    """获取最近的研究任务"""
    data = await supply_chain_service.get_recent_research(limit)
    return ok(data)


@router.get("/stats")
async def research_stats():
    """获取研究统计数据"""
    data = await supply_chain_service.get_research_stats()
    return ok(data)


@router.get("/{research_id}")
async def get_research(research_id: int):
    """获取研究详情"""
    data = await supply_chain_service.get_research_detail(research_id)
    if not data:
        return fail(404, "研究任务不存在")
    return ok(data)


@router.post("")
async def create_research(body: ResearchCreate, background_tasks: BackgroundTasks):
    """创建研究任务并自动启动分析"""
    research_id = await supply_chain_service.create_research(
        body.target_type, body.target_name, body.target_code
    )

    # 自动启动分析任务
    research = {
        "id": research_id,
        "target_type": body.target_type,
        "target_name": body.target_name,
        "target_code": body.target_code,
    }
    await supply_chain_service.update_research(research_id, status="processing")
    background_tasks.add_task(_run_ai_research, research_id, research)

    return ok({"id": research_id, "message": "研究任务已创建，正在自动分析中"})


@router.put("/{research_id}")
async def update_research(research_id: int, body: ResearchUpdate):
    """更新研究任务"""
    # 检查是否存在
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    update_data = body.dict(exclude_none=True)
    if update_data:
        await supply_chain_service.update_research(research_id, **update_data)

    return ok({"message": "更新成功"})


@router.delete("/{research_id}")
async def delete_research(research_id: int):
    """删除研究任务"""
    # 检查是否存在
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    await supply_chain_service.delete_research(research_id)
    return ok({"message": "删除成功"})


@router.post("/{research_id}/run")
async def run_research(research_id: int, background_tasks: BackgroundTasks):
    """执行AI挖掘"""
    # 检查是否存在
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    # 更新状态为处理中
    await supply_chain_service.update_research(research_id, status="processing")

    # 后台执行挖掘任务
    background_tasks.add_task(_run_ai_research, research_id, existing)

    return ok({"message": "挖掘任务已启动，请稍后查看结果"})


async def _run_ai_research(research_id: int, research: dict):
    """后台执行AI挖掘"""
    try:
        from app.ai.supply_chain_analyzer import analyze_supply_chain
        from app.core.database import get_db
        import json

        # 调用AI分析
        result = await analyze_supply_chain(
            target_type=research["target_type"],
            target_name=research["target_name"],
            target_code=research.get("target_code"),
        )

        # 匹配股票代码
        relations = result.get("relations", [])
        if relations:
            db = await get_db()
            try:
                for rel in relations:
                    if not rel.get("company_code") and rel.get("company_name"):
                        # 通过公司名称匹配股票代码
                        cursor = await db.execute(
                            "SELECT code FROM stocks WHERE name LIKE ? LIMIT 1",
                            (f"%{rel['company_name']}%",)
                        )
                        row = await cursor.fetchone()
                        if row:
                            rel["company_code"] = row[0]
            finally:
                await db.close()

        # 保存搜索来源
        search_sources = result.get("sources", [])

        # 保存结果
        await supply_chain_service.save_relations(research_id, relations)
        await supply_chain_service.update_research(
            research_id,
            status="completed",
            result_summary=result.get("summary", ""),
            search_sources=json.dumps(search_sources, ensure_ascii=False) if search_sources else None,
        )

        from app.services import admin_service
        await admin_service.log_action(
            "supply_chain_research",
            f"供应链挖掘完成: {research['target_name']}, 发现{len(relations)}条关系",
            "success"
        )

    except Exception as e:
        await supply_chain_service.update_research(research_id, status="failed")
        from app.services import admin_service
        await admin_service.log_action(
            "supply_chain_research",
            f"供应链挖掘失败: {research['target_name']} - {str(e)}",
            "failed"
        )


@router.get("/relation/{relation_id}")
async def get_relation(relation_id: int):
    """获取单条供应链关系详情"""
    data = await supply_chain_service.get_relation_detail(relation_id)
    if not data:
        return fail(404, "关系不存在")
    return ok(data)


class RelationCreate(BaseModel):
    company_name: str
    company_code: Optional[str] = None
    relation_type: str = "upstream"
    relation_desc: Optional[str] = None
    product_service: Optional[str] = None
    cooperation_detail: Optional[str] = None
    business_volume: Optional[str] = None
    start_time: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    news_title: Optional[str] = None
    news_date: Optional[str] = None


class RelationUpdate(BaseModel):
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    relation_type: Optional[str] = None
    relation_desc: Optional[str] = None
    product_service: Optional[str] = None
    cooperation_detail: Optional[str] = None
    business_volume: Optional[str] = None
    start_time: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    news_title: Optional[str] = None
    news_date: Optional[str] = None


@router.post("/{research_id}/relations")
async def add_relation(research_id: int, body: RelationCreate):
    """新增供应链关系"""
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    relation_id = await supply_chain_service.add_relation(research_id, body.dict(exclude_none=True))
    return ok({"id": relation_id, "message": "新增成功"})


@router.put("/relation/{relation_id}")
async def update_relation(relation_id: int, body: RelationUpdate):
    """更新供应链关系"""
    existing = await supply_chain_service.get_relation_detail(relation_id)
    if not existing:
        return fail(404, "关系不存在")

    update_data = body.dict(exclude_none=True)
    if update_data:
        await supply_chain_service.update_relation(relation_id, **update_data)

    return ok({"message": "更新成功"})


@router.delete("/relation/{relation_id}")
async def delete_relation(relation_id: int):
    """删除供应链关系"""
    existing = await supply_chain_service.get_relation_detail(relation_id)
    if not existing:
        return fail(404, "关系不存在")

    await supply_chain_service.delete_relation(relation_id)
    return ok({"message": "删除成功"})


# 笔记相关API
class NoteCreate(BaseModel):
    content: str


class NoteUpdate(BaseModel):
    content: str


@router.get("/{research_id}/notes")
async def get_notes(research_id: int):
    """获取研究任务的所有笔记"""
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    data = await supply_chain_service.get_notes(research_id)
    return ok(data)


@router.post("/{research_id}/notes")
async def add_note(research_id: int, body: NoteCreate):
    """新增笔记"""
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    note_id = await supply_chain_service.add_note(research_id, body.content)
    return ok({"id": note_id, "message": "笔记已添加"})


@router.put("/note/{note_id}")
async def update_note(note_id: int, body: NoteUpdate):
    """更新笔记"""
    await supply_chain_service.update_note(note_id, body.content)
    return ok({"message": "笔记已更新"})


@router.delete("/note/{note_id}")
async def delete_note(note_id: int):
    """删除笔记"""
    await supply_chain_service.delete_note(note_id)
    return ok({"message": "笔记已删除"})


class SupplementRequest(BaseModel):
    content: str
    note: Optional[str] = None


@router.post("/{research_id}/supplement")
async def supplement_research(research_id: int, body: SupplementRequest, background_tasks: BackgroundTasks):
    """补充采集"""
    # 检查是否存在
    existing = await supply_chain_service.get_research_detail(research_id)
    if not existing:
        return fail(404, "研究任务不存在")

    # 更新状态为处理中
    await supply_chain_service.update_research(research_id, status="processing")

    # 后台执行补充分析
    background_tasks.add_task(_run_supplement_research, research_id, existing, body.content, body.note)

    return ok({"message": "补充采集已启动，正在分析中..."})


async def _run_supplement_research(research_id: int, research: dict, content: str, note: str = None):
    """后台执行补充采集"""
    try:
        from app.ai.supply_chain_analyzer import analyze_with_supplement
        from app.core.database import get_db
        import json

        # 获取已有关系
        existing_relations = research.get("relations", [])

        # 调用AI进行补充分析
        result = await analyze_with_supplement(
            target_type=research["target_type"],
            target_name=research["target_name"],
            existing_relations=existing_relations,
            supplement_content=content,
            supplement_note=note,
        )

        # 合并新旧关系
        new_relations = result.get("relations", [])

        # 匹配股票代码
        if new_relations:
            db = await get_db()
            try:
                for rel in new_relations:
                    if not rel.get("company_code") and rel.get("company_name"):
                        cursor = await db.execute(
                            "SELECT code FROM stocks WHERE name LIKE ? LIMIT 1",
                            (f"%{rel['company_name']}%",)
                        )
                        row = await cursor.fetchone()
                        if row:
                            rel["company_code"] = row[0]
            finally:
                await db.close()

        # 合并关系（去重）
        all_relations = existing_relations.copy()
        existing_names = {r.get("company_name") for r in existing_relations}
        for rel in new_relations:
            if rel.get("company_name") not in existing_names:
                all_relations.append(rel)
                existing_names.add(rel.get("company_name"))

        # 更新搜索来源
        existing_sources = []
        if research.get("search_sources"):
            try:
                existing_sources = json.loads(research["search_sources"]) if isinstance(research["search_sources"], str) else research["search_sources"]
            except:
                pass

        # 添加新来源
        if content.startswith("http"):
            existing_sources.append({
                "title": note or "用户补充链接",
                "url": content,
                "source": "user_supplement"
            })

        # 保存结果
        await supply_chain_service.save_relations(research_id, all_relations)

        # 生成新的摘要
        summary = research.get("result_summary", "")
        if result.get("summary"):
            summary += f"\n\n【补充采集】{result['summary']}"

        await supply_chain_service.update_research(
            research_id,
            status="completed",
            result_summary=summary,
            search_sources=json.dumps(existing_sources, ensure_ascii=False),
        )

        from app.services import admin_service
        await admin_service.log_action(
            "supply_chain_supplement",
            f"补充采集完成: {research['target_name']}, 新增{len(new_relations)}条关系",
            "success"
        )

    except Exception as e:
        await supply_chain_service.update_research(research_id, status="completed")
        from app.services import admin_service
        await admin_service.log_action(
            "supply_chain_supplement",
            f"补充采集失败: {research['target_name']} - {str(e)}",
            "failed"
        )
