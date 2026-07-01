import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def import_stocks():
    """从AKShare导入A股股票列表（使用新浪源，不依赖东方财富）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_stocks_start")

    try:
        # 基础列表：code + name（新浪源，5500+条）
        df = ak.stock_info_a_code_name()
        if df is None or df.empty:
            logger.warning("akshare_returned_empty")
            return

        # 上交所补充信息（上市日期等）
        sh_extra = {}
        try:
            df_sh = ak.stock_info_sh_name_code()
            for _, r in df_sh.iterrows():
                code = str(r.get("证券代码", "")).strip()
                sh_extra[code] = {
                    "full_name": str(r.get("证券全称", "")).strip(),
                    "list_date": str(r.get("上市日期", "")).strip(),
                }
        except Exception as e:
            logger.warning("sh_info_failed", error=str(e))

        # 深交所补充信息
        sz_extra = {}
        try:
            df_sz = ak.stock_info_sz_name_code()
            for _, r in df_sz.iterrows():
                code = str(r.get("A股代码", "")).strip()
                sz_extra[code] = {
                    "list_date": str(r.get("A股上市日期", "")).strip(),
                }
        except Exception as e:
            logger.warning("sz_info_failed", error=str(e))

        db = await get_db()
        try:
            count = 0
            for _, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                name = str(row.get("name", "")).strip()
                if not code or not name:
                    continue

                # 判断市场
                if code.startswith("6"):
                    market = "SH"
                elif code.startswith(("0", "3")):
                    market = "SZ"
                elif code.startswith(("4", "8", "9")):
                    market = "BJ"
                else:
                    market = "OTHER"

                # 补充信息
                extra = sh_extra.get(code) or sz_extra.get(code) or {}
                list_date = extra.get("list_date", "")

                await db.execute(
                    """INSERT OR REPLACE INTO stocks (code, name, market, list_date, is_active)
                       VALUES (?, ?, ?, ?, 1)""",
                    (code, name, market, list_date or None),
                )
                count += 1

            await db.commit()
            logger.info("import_stocks_done", count=count)
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_stocks_failed", error=str(e))


# ── 以下接口依赖东方财富，当前环境不可用 ──
# 如需启用，在可访问东方财富的网络环境下运行


async def import_concepts():
    """从AKShare导入概念板块（依赖东方财富，当前不可用）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_concepts_start")

    try:
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            logger.warning("akshare_concepts_empty")
            return

        db = await get_db()
        try:
            count = 0
            for _, row in df.iterrows():
                name = str(row.get("板块名称", "")).strip()
                if not name:
                    continue

                await db.execute(
                    "INSERT OR IGNORE INTO concepts (name, category) VALUES (?, ?)",
                    (name, "concept"),
                )
                count += 1

            await db.commit()
            logger.info("import_concepts_done", count=count)
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_concepts_failed", error=str(e))


async def import_concept_stocks():
    """从AKShare导入概念成分股（依赖东方财富，当前不可用）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_concept_stocks_start")

    db = await get_db()
    try:
        cursor = await db.execute("SELECT id, name FROM concepts")
        concepts = await cursor.fetchall()

        total = 0
        for concept_id, concept_name in concepts:
            try:
                df = ak.stock_board_concept_cons_em(symbol=concept_name)
                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    code = str(row.get("代码", "")).strip()
                    if not code:
                        continue

                    cursor2 = await db.execute("SELECT concepts FROM stocks WHERE code = ?", (code,))
                    stock_row = await cursor2.fetchone()
                    if stock_row:
                        existing = []
                        if stock_row[0]:
                            try:
                                existing = json.loads(stock_row[0])
                            except (json.JSONDecodeError, TypeError):
                                existing = []
                        if concept_name not in existing:
                            existing.append(concept_name)
                            await db.execute(
                                "UPDATE stocks SET concepts = ?, updated_at = datetime('now') WHERE code = ?",
                                (json.dumps(existing, ensure_ascii=False), code),
                            )
                            total += 1

            except Exception as e:
                logger.warning("import_concept_failed", concept=concept_name, error=str(e))
                continue

        await db.commit()
        logger.info("import_concept_stocks_done", updated=total)

    except Exception as e:
        logger.error("import_concept_stocks_failed", error=str(e))
    finally:
        await db.close()


async def import_stock_profiles():
    """从巨潮资讯导入公司概况（core_business + industry）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_stock_profiles_start")

    db = await get_db()
    try:
        # 查询尚未采集公司详情的股票
        cursor = await db.execute(
            """SELECT s.code, s.name FROM stocks s
               LEFT JOIN stock_profiles sp ON sp.code = s.code
               WHERE s.is_active = 1 AND sp.code IS NULL
               ORDER BY s.code"""
        )
        stocks = await cursor.fetchall()
        if not stocks:
            logger.info("import_stock_profiles_nothing_to_update")
            return

        import asyncio
        import time

        updated = 0
        failed = 0
        batch_size = 50

        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            for code, name in batch:
                try:
                    loop = asyncio.get_event_loop()
                    df = await loop.run_in_executor(
                        None, lambda c=code: ak.stock_profile_cninfo(symbol=c)
                    )
                    if df is None or df.empty:
                        continue

                    row = df.iloc[0]
                    main_business = str(row.get("主营业务", "")).strip()
                    intro = str(row.get("机构简介", "")).strip()
                    industry = str(row.get("所属行业", "")).strip()

                    def safe_str(val):
                        s = str(val).strip()
                        return s if s and s != "nan" else None

                    # 保存详细公司信息
                    await db.execute(
                        """INSERT OR REPLACE INTO stock_profiles
                           (code, company_name, english_name, legal_rep, reg_capital,
                            found_date, list_date, website, email, phone,
                            reg_address, office_address, business_scope, introduction, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                        (
                            code,
                            safe_str(row.get("公司名称")),
                            safe_str(row.get("英文名称")),
                            safe_str(row.get("法人代表")),
                            safe_str(row.get("注册资金")),
                            safe_str(row.get("成立日期")),
                            safe_str(row.get("上市日期")),
                            safe_str(row.get("官方网站")),
                            safe_str(row.get("电子邮箱")),
                            safe_str(row.get("联系电话")),
                            safe_str(row.get("注册地址")),
                            safe_str(row.get("办公地址")),
                            safe_str(row.get("经营范围")),
                            safe_str(row.get("机构简介")),
                        ),
                    )

                    # core_business: 优先用主营业务，备选机构简介（截取前200字）
                    core_business = ""
                    if main_business and main_business != "nan":
                        core_business = main_business[:200]
                    elif intro and intro != "nan":
                        core_business = intro[:200]

                    # 更新 stocks 表
                    updates = []
                    params = []
                    if core_business:
                        updates.append("core_business = ?")
                        params.append(core_business)
                    if industry and industry != "nan":
                        updates.append("industry = ?")
                        params.append(industry)

                    if updates:
                        updates.append("updated_at = datetime('now')")
                        params.append(code)
                        await db.execute(
                            f"UPDATE stocks SET {', '.join(updates)} WHERE code = ?",
                            params,
                        )
                    updated += 1

                except Exception as e:
                    failed += 1
                    logger.debug("import_profile_failed", code=code, error=str(e))

            # 每批提交一次
            await db.commit()
            logger.info("import_stock_profiles_batch", batch=i // batch_size + 1,
                         updated=updated, failed=failed, total=len(stocks))

            # 批间延迟，避免被限流
            if i + batch_size < len(stocks):
                time.sleep(2)

        logger.info("import_stock_profiles_done", updated=updated, failed=failed, total=len(stocks))

    except Exception as e:
        logger.error("import_stock_profiles_failed", error=str(e))
    finally:
        await db.close()
