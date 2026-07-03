import { get, post, put, del } from "./request";
import type {
  SupplyChainResearch,
  SupplyChainRelationDetail,
  SupplyChainStats,
  SupplyChainNote,
} from "../types";

// 获取研究任务列表
export function getSupplyChainList(params: {
  page?: number;
  page_size?: number;
  target_type?: string;
  status?: string;
}) {
  return get<{
    items: SupplyChainResearch[];
    total: number;
    page: number;
    page_size: number;
  }>("api/v1/supply-chain", params);
}

// 获取最近的研究任务
export function getRecentResearch(limit: number = 5) {
  return get<SupplyChainResearch[]>("api/v1/supply-chain/recent", { limit });
}

// 获取研究统计数据
export function getSupplyChainStats() {
  return get<SupplyChainStats>("api/v1/supply-chain/stats");
}

// 获取研究详情
export function getSupplyChainDetail(id: number) {
  return get<SupplyChainResearch>(`/api/v1/supply-chain/${id}`);
}

// 创建研究任务
export function createSupplyChainResearch(data: {
  target_type: string;
  target_name: string;
  target_code?: string;
}) {
  return post<{ id: number; message: string }>("api/v1/supply-chain", data);
}

// 更新研究任务
export function updateSupplyChainResearch(id: number, data: {
  target_type?: string;
  target_name?: string;
  target_code?: string;
  status?: string;
  result_summary?: string;
}) {
  return put<{ message: string }>(`/api/v1/supply-chain/${id}`, data);
}

// 删除研究任务
export function deleteSupplyChainResearch(id: number) {
  return del<{ message: string }>(`/api/v1/supply-chain/${id}`);
}

// 执行AI挖掘
export function runSupplyChainResearch(id: number) {
  return post<{ message: string }>(`/api/v1/supply-chain/${id}/run`);
}

// 补充采集
export function supplementResearch(id: number, data: {
  content: string;
  note?: string;
}) {
  return post<{ message: string }>(`/api/v1/supply-chain/${id}/supplement`, data);
}

// 获取单条关系详情
export function getSupplyChainRelation(relationId: number) {
  return get<SupplyChainRelationDetail>(`/api/v1/supply-chain/relation/${relationId}`);
}

// 新增供应链关系
export function addSupplyChainRelation(researchId: number, data: {
  company_name: string;
  company_code?: string;
  relation_type?: string;
  relation_desc?: string;
  product_service?: string;
  cooperation_detail?: string;
  business_volume?: string;
  start_time?: string;
  confidence?: number;
  source?: string;
  source_url?: string;
  news_title?: string;
  news_date?: string;
}) {
  return post<{ id: number; message: string }>(`/api/v1/supply-chain/${researchId}/relations`, data);
}

// 更新供应链关系
export function updateSupplyChainRelation(relationId: number, data: {
  company_name?: string;
  company_code?: string;
  relation_type?: string;
  relation_desc?: string;
  product_service?: string;
  cooperation_detail?: string;
  business_volume?: string;
  start_time?: string;
  confidence?: number;
  source?: string;
  source_url?: string;
  news_title?: string;
  news_date?: string;
}) {
  return put<{ message: string }>(`/api/v1/supply-chain/relation/${relationId}`, data);
}

// 删除供应链关系
export function deleteSupplyChainRelation(relationId: number) {
  return del<{ message: string }>(`/api/v1/supply-chain/relation/${relationId}`);
}

// 获取研究任务的所有笔记
export function getSupplyChainNotes(researchId: number) {
  return get<SupplyChainNote[]>(`/api/v1/supply-chain/${researchId}/notes`);
}

// 新增笔记
export function addSupplyChainNote(researchId: number, content: string) {
  return post<{ id: number; message: string }>(`/api/v1/supply-chain/${researchId}/notes`, { content });
}

// 更新笔记
export function updateSupplyChainNote(noteId: number, content: string) {
  return put<{ message: string }>(`/api/v1/supply-chain/note/${noteId}`, { content });
}

// 删除笔记
export function deleteSupplyChainNote(noteId: number) {
  return del<{ message: string }>(`/api/v1/supply-chain/note/${noteId}`);
}
