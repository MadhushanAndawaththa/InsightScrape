export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface ModelInfo {
  id: string;
  name: string;
  tier: string;
}

export interface AuditResult {
  url: string;
  metrics: PageMetrics;
  analysis: SEOAnalysis | null;
  recommendations: Recommendation[];
  prompt_logs: PromptLog[];
  audit_duration_ms: number;
  ai_error: string | null;
}

export interface PageMetrics {
  word_count: number;
  headings_count: Record<string, number>;
  heading_hierarchy: [string, string][];
  cta_count: number;
  internal_links: number;
  external_links: number;
  image_count: number;
  images_missing_alt_count: number;
  images_decorative_alt_count: number;
  images_missing_alt_pct: number;
  meta_title?: string;
  meta_description?: string;
  scrape_method: string;
  content_quality_warning?: string;
}

export interface SectionAnalysis {
  score: number;
  findings: string;
  evidence: string;
}

export interface SEOAnalysis {
  structure_score: number;
  messaging_score: number;
  cta_score: number;
  content_depth_score: number;
  ux_score: number;
  overall_score: number;
  structure_analysis: SectionAnalysis;
  messaging_analysis: SectionAnalysis;
  cta_analysis: SectionAnalysis;
  content_depth_analysis: SectionAnalysis;
  ux_analysis: SectionAnalysis;
}

export interface Recommendation {
  priority: number;
  category: "seo" | "messaging" | "cta" | "content" | "ux";
  title: string;
  description: string;
  grounded_metric: string;
  action: string;
  expected_impact: string;
}

export interface PromptLog {
  stage: string;
  system_prompt: string;
  user_prompt: string;
  raw_response: string;
  parsed_response: any;
  timestamp: string;
  model: string;
  token_usage?: Record<string, number>;
}

export const runAudit = async (url: string, model?: string): Promise<AuditResult> => {
  const res = await fetch(`${API_URL}/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, model }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Audit failed');
  }

  return res.json();
};

export const fetchModels = async (): Promise<ModelInfo[]> => {
  try {
    const res = await fetch(`${API_URL}/models`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.models || [];
  } catch {
    return [];
  }
};

export const checkHealth = async (): Promise<boolean> => {
  try {
    const res = await fetch(`${API_URL.replace('/api', '')}/health`);
    return res.ok;
  } catch (e) {
    return false;
  }
};
