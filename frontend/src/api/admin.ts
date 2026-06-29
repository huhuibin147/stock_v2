import { get, post } from "./request";

export interface SystemStatus {
  tables: Record<string, number>;
  db_size: number;
  db_size_human: string;
}

export interface AdminLog {
  id: number;
  action: string;
  detail: string;
  status: string;
  created_at: string;
}

export interface AdminStock {
  code: string;
  name: string;
  market: string;
  industry: string;
  concepts: string[];
  core_business: string;
  chain_id: number | null;
  is_active: number;
}

export interface AdminNews {
  id: number;
  source: string;
  source_id: string;
  title: string;
  summary: string;
  sentiment: number | null;
  importance_score: number | null;
  published_at: string | null;
  category: string;
}

export interface AdminConcept {
  id: number;
  name: string;
  category: string;
  stock_count: number;
  hot_score: number;
}

// Status
export function getSystemStatus() {
  return get<SystemStatus>("/api/v1/admin/status");
}

export function getAdminLogs(limit = 50) {
  return get<AdminLog[]>(`/api/v1/admin/logs?limit=${limit}`);
}

// Data
export function getAdminStocks(page = 1, pageSize = 20, q = "") {
  return get<{ items: AdminStock[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/stocks?page=${page}&page_size=${pageSize}&q=${encodeURIComponent(q)}`
  );
}

export function getAdminNews(page = 1, pageSize = 20) {
  return get<{ items: AdminNews[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/news?page=${page}&page_size=${pageSize}`
  );
}

export function getAdminConcepts(page = 1, pageSize = 50) {
  return get<{ items: AdminConcept[]; total: number; page: number; page_size: number }>(
    `/api/v1/admin/concepts?page=${page}&page_size=${pageSize}`
  );
}

// Actions
export function triggerImportStocks() {
  return post("/api/v1/admin/import/stocks");
}

export function triggerImportConcepts() {
  return post("/api/v1/admin/import/concepts");
}

export function triggerImportConceptStocks() {
  return post("/api/v1/admin/import/concept-stocks");
}

export function triggerCollectEastmoney() {
  return post("/api/v1/admin/collect/eastmoney");
}

export function triggerCollectTHS() {
  return post("/api/v1/admin/collect/ths");
}

export function triggerCollectSina() {
  return post("/api/v1/admin/collect/sina");
}

export function triggerCollectAll() {
  return post("/api/v1/admin/collect/all");
}
