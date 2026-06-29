export interface StockInfo {
  code: string;
  name: string;
  market: string;
  industry?: string;
  concepts: string[];
  core_business?: string;
}

export interface ChainPosition {
  layer?: number;
  layer_name?: string;
  position?: string;
  upstream: { code: string; name: string; relation: string }[];
  downstream: { code: string; name: string; relation: string }[];
}

export interface NewsItem {
  id: number;
  title: string;
  summary: string;
  sentiment?: number;
  published_at?: string;
  source?: string;
  url?: string;
}

export interface EventItem {
  event_type: string;
  event_subtype?: string;
  title: string;
  impact?: number;
  event_date?: string;
}

export interface SentimentSummary {
  positive: number;
  neutral: number;
  negative: number;
  trend: string;
}

export interface StockProfile {
  stock: StockInfo;
  chain: ChainPosition;
  recent_news: NewsItem[];
  recent_events: EventItem[];
  sentiment_7d: SentimentSummary;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface HotStock {
  code: string;
  name: string;
  market: string;
  industry: string;
  news_count: number;
}

export interface HotConcept {
  name: string;
  stock_count: number;
  hot_score: number;
}

export interface LayerSummary {
  layer: number;
  name: string;
  chain_count: number;
  stock_count: number;
}

export interface OverviewData {
  stats: { stocks: number; news: number; concepts: number; events: number; chains: number };
  hot_stocks: HotStock[];
  hot_concepts: HotConcept[];
  recent_events: EventItem[];
  recent_news: NewsItem[];
  layers: LayerSummary[];
}
