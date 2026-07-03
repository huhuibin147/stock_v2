"""供应链挖掘服务"""

from app.core.database import get_db


async def get_research_list(page: int = 1, page_size: int = 20, target_type: str = None, status: str = None):
    """获取研究任务列表"""
    db = await get_db()
    try:
        # 构建查询条件
        conditions = []
        params = []
        if target_type:
            conditions.append("target_type = ?")
            params.append(target_type)
        if status:
            conditions.append("status = ?")
            params.append(status)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查询总数
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM supply_chain_research WHERE {where_clause}",
            params
        )
        total = (await cursor.fetchone())[0]

        # 查询列表
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT id, target_type, target_name, target_code, status, result_summary,
                       created_at, updated_at
                FROM supply_chain_research
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        )
        rows = await cursor.fetchall()

        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "target_type": row[1],
                "target_name": row[2],
                "target_code": row[3],
                "status": row[4],
                "result_summary": row[5],
                "created_at": row[6],
                "updated_at": row[7],
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


async def get_research_detail(research_id: int):
    """获取研究详情（含关联公司）"""
    db = await get_db()
    try:
        # 查询研究任务
        cursor = await db.execute(
            """SELECT id, target_type, target_name, target_code, status, result_summary,
                      search_sources, created_at, updated_at
               FROM supply_chain_research
               WHERE id = ?""",
            (research_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        import json
        search_sources = []
        if row[6]:
            try:
                search_sources = json.loads(row[6])
            except:
                pass

        research = {
            "id": row[0],
            "target_type": row[1],
            "target_name": row[2],
            "target_code": row[3],
            "status": row[4],
            "result_summary": row[5],
            "search_sources": search_sources,
            "created_at": row[7],
            "updated_at": row[8],
            "relations": [],
        }

        # 查询关联公司
        cursor = await db.execute(
            """SELECT id, company_name, company_code, relation_type, relation_desc,
                      product_service, cooperation_detail, business_volume, start_time,
                      confidence, source, source_url, news_title, news_date
               FROM supply_chain_relations
               WHERE research_id = ?
               ORDER BY confidence DESC, company_name""",
            (research_id,)
        )
        relations = await cursor.fetchall()

        for rel in relations:
            research["relations"].append({
                "id": rel[0],
                "company_name": rel[1],
                "company_code": rel[2],
                "relation_type": rel[3],
                "relation_desc": rel[4],
                "product_service": rel[5],
                "cooperation_detail": rel[6],
                "business_volume": rel[7],
                "start_time": rel[8],
                "confidence": rel[9],
                "source": rel[10],
                "source_url": rel[11],
                "news_title": rel[12],
                "news_date": rel[13],
            })

        return research
    finally:
        await db.close()


async def create_research(target_type: str, target_name: str, target_code: str = None):
    """创建研究任务"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO supply_chain_research (target_type, target_name, target_code)
               VALUES (?, ?, ?)""",
            (target_type, target_name, target_code)
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_research(research_id: int, **kwargs):
    """更新研究任务"""
    db = await get_db()
    try:
        # 构建更新语句
        set_parts = []
        params = []
        for key, value in kwargs.items():
            if key in ("target_type", "target_name", "target_code", "status", "result_summary", "search_sources"):
                set_parts.append(f"{key} = ?")
                params.append(value)

        if not set_parts:
            return False

        set_parts.append("updated_at = datetime('now')")
        params.append(research_id)

        await db.execute(
            f"""UPDATE supply_chain_research
                SET {', '.join(set_parts)}
                WHERE id = ?""",
            params
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def delete_research(research_id: int):
    """删除研究任务"""
    db = await get_db()
    try:
        # 先删除关联关系
        await db.execute(
            "DELETE FROM supply_chain_relations WHERE research_id = ?",
            (research_id,)
        )
        # 删除研究任务
        await db.execute(
            "DELETE FROM supply_chain_research WHERE id = ?",
            (research_id,)
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def save_relations(research_id: int, relations: list):
    """保存供应链关系"""
    db = await get_db()
    try:
        # 先删除旧关系
        await db.execute(
            "DELETE FROM supply_chain_relations WHERE research_id = ?",
            (research_id,)
        )

        # 插入新关系
        for rel in relations:
            await db.execute(
                """INSERT INTO supply_chain_relations
                   (research_id, company_name, company_code, relation_type, relation_desc,
                    product_service, cooperation_detail, business_volume, start_time,
                    confidence, source, source_url, news_title, news_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    research_id,
                    rel.get("company_name"),
                    rel.get("company_code"),
                    rel.get("relation_type"),
                    rel.get("relation_desc"),
                    rel.get("product_service"),
                    rel.get("cooperation_detail"),
                    rel.get("business_volume"),
                    rel.get("start_time"),
                    rel.get("confidence"),
                    rel.get("source"),
                    rel.get("source_url"),
                    rel.get("news_title"),
                    rel.get("news_date"),
                )
            )

        await db.commit()
        return True
    finally:
        await db.close()


async def get_relation_detail(relation_id: int):
    """获取单条供应链关系详情"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT r.id, r.research_id, r.company_name, r.company_code, r.relation_type,
                      r.relation_desc, r.product_service, r.cooperation_detail, r.business_volume,
                      r.start_time, r.confidence, r.source, r.source_url, r.news_title, r.news_date,
                      s.target_type, s.target_name, s.target_code
               FROM supply_chain_relations r
               JOIN supply_chain_research s ON r.research_id = s.id
               WHERE r.id = ?""",
            (relation_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "research_id": row[1],
            "company_name": row[2],
            "company_code": row[3],
            "relation_type": row[4],
            "relation_desc": row[5],
            "product_service": row[6],
            "cooperation_detail": row[7],
            "business_volume": row[8],
            "start_time": row[9],
            "confidence": row[10],
            "source": row[11],
            "source_url": row[12],
            "news_title": row[13],
            "news_date": row[14],
            "research": {
                "target_type": row[15],
                "target_name": row[16],
                "target_code": row[17],
            },
        }
    finally:
        await db.close()


async def update_relation(relation_id: int, **kwargs):
    """更新供应链关系"""
    db = await get_db()
    try:
        set_parts = []
        params = []
        allowed_fields = [
            "company_name", "company_code", "relation_type", "relation_desc",
            "product_service", "cooperation_detail", "business_volume", "start_time",
            "confidence", "source", "source_url", "news_title", "news_date"
        ]
        for key, value in kwargs.items():
            if key in allowed_fields:
                set_parts.append(f"{key} = ?")
                params.append(value)

        if not set_parts:
            return False

        params.append(relation_id)
        await db.execute(
            f"""UPDATE supply_chain_relations
                SET {', '.join(set_parts)}
                WHERE id = ?""",
            params
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def delete_relation(relation_id: int):
    """删除单条供应链关系"""
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM supply_chain_relations WHERE id = ?",
            (relation_id,)
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def add_relation(research_id: int, relation: dict):
    """新增单条供应链关系"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO supply_chain_relations
               (research_id, company_name, company_code, relation_type, relation_desc,
                product_service, cooperation_detail, business_volume, start_time,
                confidence, source, source_url, news_title, news_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                research_id,
                relation.get("company_name"),
                relation.get("company_code"),
                relation.get("relation_type", "upstream"),
                relation.get("relation_desc"),
                relation.get("product_service"),
                relation.get("cooperation_detail"),
                relation.get("business_volume"),
                relation.get("start_time"),
                relation.get("confidence"),
                relation.get("source"),
                relation.get("source_url"),
                relation.get("news_title"),
                relation.get("news_date"),
            )
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_notes(research_id: int):
    """获取研究任务的所有笔记"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, research_id, content, created_at, updated_at
               FROM supply_chain_notes
               WHERE research_id = ?
               ORDER BY created_at DESC""",
            (research_id,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "research_id": row[1],
                "content": row[2],
                "created_at": row[3],
                "updated_at": row[4],
            }
            for row in rows
        ]
    finally:
        await db.close()


async def add_note(research_id: int, content: str):
    """新增笔记"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO supply_chain_notes (research_id, content)
               VALUES (?, ?)""",
            (research_id, content)
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_note(note_id: int, content: str):
    """更新笔记"""
    db = await get_db()
    try:
        await db.execute(
            """UPDATE supply_chain_notes
               SET content = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (content, note_id)
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def delete_note(note_id: int):
    """删除笔记"""
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM supply_chain_notes WHERE id = ?",
            (note_id,)
        )
        await db.commit()
        return True
    finally:
        await db.close()


async def get_recent_research(limit: int = 5):
    """获取最近的研究任务（首页用）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, target_type, target_name, target_code, status, created_at
               FROM supply_chain_research
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,)
        )
        rows = await cursor.fetchall()

        items = []
        for row in rows:
            items.append({
                "id": row[0],
                "target_type": row[1],
                "target_name": row[2],
                "target_code": row[3],
                "status": row[4],
                "created_at": row[5],
            })

        return items
    finally:
        await db.close()


async def get_research_stats():
    """获取研究统计数据"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM supply_chain_research")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM supply_chain_research WHERE status = 'completed'"
        )
        completed = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM supply_chain_relations"
        )
        relations = (await cursor.fetchone())[0]

        return {
            "total": total,
            "completed": completed,
            "relations": relations,
        }
    finally:
        await db.close()
