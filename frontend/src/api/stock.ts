import { get } from "./request";
import type { StockInfo, StockProfile, NewsItem, NewsDetail, EventItem, FinancialRecord } from "../types";

export function searchStocks(q: string, limit = 10) {
  return get<StockInfo[]>(`/api/v1/stocks/search?q=${encodeURIComponent(q)}&limit=${limit}`);
}

export function getStockProfile(code: string) {
  return get<StockProfile>(`/api/v1/stocks/${code}/profile`);
}

export function getStockNews(code: string, page = 1, pageSize = 10) {
  return get<{ items: NewsItem[]; total: number }>(
    `/api/v1/stocks/${code}/news?page=${page}&page_size=${pageSize}`
  );
}

export function getStockEvents(code: string) {
  return get<EventItem[]>(`/api/v1/stocks/${code}/events`);
}

export function getStockFinancials(code: string, limit = 8) {
  return get<FinancialRecord[]>(`/api/v1/stocks/${code}/financials?limit=${limit}`);
}

export function getHotNews(limit = 20) {
  return get<NewsItem[]>(`/api/v1/news/hot?limit=${limit}`);
}

export function getNewsDetail(id: number) {
  return get<NewsDetail>(`/api/v1/news/${id}`);
}

export interface OverviewData {
  stats: { stocks: number; news: number; concepts: number; events: number; chains: number };
  hot_stocks: { code: string; name: string; market: string; industry: string; news_count: number }[];
  hot_concepts: { name: string; stock_count: number; hot_score: number }[];
  recent_events: { event_type: string; title: string; impact: number; event_date: string; stock_codes: string[] }[];
  recent_news: NewsItem[];
  layers: { layer: number; name: string; chain_count: number; stock_count: number }[];
}

export function getOverview() {
  return get<OverviewData>("/api/v1/analysis/overview");
}
