export interface StockInfo {
  code: string;
  name: string;
  market: string;
  industry?: string;
  concepts: string[];
  core_business?: string;
  pe_ttm?: number | null;
  pb?: number | null;
  market_cap?: number | null;
  dividend_yield?: number | null;
  turnover_amount?: number | null;
  last_price?: number | null;
  pct_change?: number | null;
  volume?: number | null;
}

export interface KlineRecord {
  trade_date: string;
  open: number | null;
  close: number | null;
  high: number | null;
  low: number | null;
  volume: number | null;
  turnover: number | null;
  amplitude: number | null;
  pct_change: number | null;
  change_amount: number | null;
  turnover_rate: number | null;
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

export interface NewsDetail {
  id: number;
  title: string;
  content: string;
  summary: string;
  key_points: string[] | null;
  sentiment: number | null;
  sentiment_score: number | null;
  published_at: string | null;
  source: string | null;
  url: string | null;
  entities: { type: string; code: string; name: string }[] | null;
  events: { type: string; subtype: string; impact: number }[] | null;
  tags: string[] | null;
  category: string | null;
  importance_score: number | null;
  stocks: { code: string; name: string }[];
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

export interface CompanyProfile {
  company_name: string | null;
  english_name: string | null;
  legal_rep: string | null;
  reg_capital: string | null;
  found_date: string | null;
  list_date: string | null;
  website: string | null;
  email: string | null;
  phone: string | null;
  reg_address: string | null;
  office_address: string | null;
  business_scope: string | null;
  introduction: string | null;
}

export interface StockProfile {
  stock: StockInfo;
  chain: ChainPosition;
  company: CompanyProfile | null;
  recent_news: NewsItem[];
  recent_events: EventItem[];
  sentiment_7d: SentimentSummary;
  concepts: string[];
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
  turnover_amount: number | null;
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

export interface FinancialRecord {
  report_date: string;
  net_profit: number | null;
  net_profit_yoy: number | null;
  revenue: number | null;
  revenue_yoy: number | null;
  eps: number | null;
  bps: number | null;
  roe: number | null;
  net_margin: number | null;
  equity_ratio: number | null;
  ocf_ps: number | null;
}

export interface OverviewData {
  stats: { stocks: number; news: number; concepts: number; events: number; chains: number; supply_chain: number; supply_chain_relations: number };
  hot_stocks: HotStock[];
  hot_concepts: HotConcept[];
  recent_events: EventItem[];
  recent_news: NewsItem[];
  layers: LayerSummary[];
}

// 供应链挖掘相关类型
export interface SupplyChainResearch {
  id: number;
  target_type: 'company' | 'industry';
  target_name: string;
  target_code?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  result_summary?: string;
  search_sources?: SearchSource[];
  created_at: string;
  updated_at: string;
  relations?: SupplyChainRelation[];
}

export interface SearchSource {
  title: string;
  url: string;
  source: string;
}

export interface SupplyChainRelation {
  id: number;
  company_name: string;
  company_code?: string;
  relation_type: string;  // 支持多种格式：upstream/downstream/partner, supplier/customer, 中文
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
}

export interface SupplyChainRelationDetail extends SupplyChainRelation {
  research_id: number;
  research: {
    target_type: string;
    target_name: string;
    target_code?: string;
  };
}

export interface SupplyChainStats {
  total: number;
  completed: number;
  relations: number;
}

export interface SupplyChainNote {
  id: number;
  research_id: number;
  content: string;
  created_at: string;
  updated_at: string;
}
