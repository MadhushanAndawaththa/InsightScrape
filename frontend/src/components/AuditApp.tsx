import { useState, useEffect, type FormEvent } from 'react';
import { checkHealth, runAudit, fetchModels, type AuditResult, type SectionAnalysis, type ModelInfo } from '../api/audit';
import ReactMarkdown from 'react-markdown';
import {
  Search, Sun, Moon, Globe, Clock, FileText, Link2, Image, MousePointerClick,
  AlertTriangle, ChevronDown, Sparkles, Shield, BarChart3, Zap, Eye, Type,
  ExternalLink, ArrowRight, Terminal, Hash, RefreshCw, Cpu, Video, Layers,
  Code2, Activity, CheckCircle2, XCircle,
} from 'lucide-react';

/* ───────────────────────── Helpers ───────────────────────── */

const scoreColor = (s: number) =>
  s >= 8 ? 'text-emerald-500' : s >= 5 ? 'text-amber-500' : 'text-rose-500';

const scoreBg = (s: number) =>
  s >= 8
    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
    : s >= 5
      ? 'bg-amber-500/10 border-amber-500/20 text-amber-600 dark:text-amber-400'
      : 'bg-rose-500/10 border-rose-500/20 text-rose-600 dark:text-rose-400';

const priorityStyle = (p: number) => {
  if (p === 1) return 'bg-rose-500 text-white';
  if (p === 2) return 'bg-amber-500 text-white';
  return 'bg-sky-500 text-white';
};

const categoryIcon = (c: string) => {
  switch (c) {
    case 'seo': return <Search className="w-4 h-4" />;
    case 'messaging': return <Type className="w-4 h-4" />;
    case 'cta': return <MousePointerClick className="w-4 h-4" />;
    case 'content': return <FileText className="w-4 h-4" />;
    case 'ux': return <Eye className="w-4 h-4" />;
    default: return <Zap className="w-4 h-4" />;
  }
};

const formatDuration = (ms: number) =>
  ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;

/* ───────────────────── Score Ring SVG ────────────────────── */

const ScoreRing = ({ score, size = 120, label }: { score: number; size?: number; label?: string }) => {
  const r = (size - 12) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 10) * circ;
  const color = score >= 8 ? '#10b981' : score >= 5 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="currentColor" strokeWidth="6"
          className="text-gray-200 dark:text-white/10" />
        <circle cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          className="score-ring" />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-3xl font-black" style={{ color }}>{score}</span>
        <span className="text-[10px] uppercase tracking-widest text-gray-400 dark:text-gray-500 font-semibold">/10</span>
      </div>
      {label && <span className="text-xs font-medium text-gray-500 dark:text-gray-400 mt-1">{label}</span>}
    </div>
  );
};

/* ───────────────── Mini Score Bar ────────────────────────── */

const MiniBar = ({ score, label }: { score: number; label: string }) => {
  const pct = (score / 10) * 100;
  const color = score >= 8 ? 'bg-emerald-500' : score >= 5 ? 'bg-amber-500' : 'bg-rose-500';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs sm:text-sm">
        <span className="text-gray-600 dark:text-gray-400 font-medium">{label}</span>
        <span className={`font-bold ${scoreColor(score)}`}>{score}/10</span>
      </div>
      <div className="h-2 rounded-full bg-gray-200 dark:bg-white/10 overflow-hidden">
        <div className={`h-full rounded-full ${color} transition-all duration-1000 ease-out`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
};

/* ──────────────── Loading Skeleton ───────────────────────── */

const LoadingState = ({ step }: { step: number }) => {
  const steps = [
    { label: 'Fetching page content...', icon: Globe },
    { label: 'Extracting metrics...', icon: BarChart3 },
    { label: 'Running AI audit analysis...', icon: Sparkles },
    { label: 'Finalizing results...', icon: Zap },
  ];

  return (
    <div className="max-w-md mx-auto py-16 space-y-6">
      <div className="flex justify-center">
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center animate-pulse">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <div className="absolute -inset-2 rounded-2xl bg-violet-500/20 animate-ping" />
        </div>
      </div>
      <div className="space-y-3">
        {steps.map((s, i) => {
          const Icon = s.icon;
          const active = i === step;
          const done = i < step;
          return (
            <div key={i}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-300 ${
                active ? 'bg-violet-500/10 dark:bg-violet-500/20 border border-violet-500/30' :
                done ? 'opacity-60' : 'opacity-30'
              }`}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${active ? 'text-violet-500 animate-pulse' : done ? 'text-emerald-500' : 'text-gray-400'}`} />
              <span className={`text-sm font-medium ${active ? 'text-violet-700 dark:text-violet-300' : 'text-gray-500 dark:text-gray-400'}`}>{s.label}</span>
              {done && <span className="ml-auto text-emerald-500 text-xs font-bold">✓</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ═══════════════════════ MAIN APP ════════════════════════════ */

export const AuditApp = () => {
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState<'idle' | 'warming' | 'ready' | 'loading' | 'success' | 'error'>('warming');
  const [error, setError] = useState('');
  const [result, setResult] = useState<AuditResult | null>(null);
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('insightscrape-theme');
      if (saved) return saved === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });
  const [loadStep, setLoadStep] = useState(0);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState('gemini-2.5-flash-lite');

  // Theme persistence
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('insightscrape-theme', dark ? 'dark' : 'light');
  }, [dark]);

  // API warmup + fetch models
  useEffect(() => {
    let isMounted = true;
    const warmup = async () => {
      try {
        const [healthy, modelList] = await Promise.all([checkHealth(), fetchModels()]);
        if (isMounted) {
          if (modelList.length > 0) setModels(modelList);
          if (healthy) setStatus('ready');
          else setTimeout(() => { if (isMounted) setStatus('ready'); }, 2500);
        }
      } catch {
        if (isMounted) setTimeout(() => { if (isMounted) setStatus('ready'); }, 2500);
      }
    };
    warmup();
    return () => { isMounted = false; };
  }, []);
  // Simulated loading steps
  useEffect(() => {
    if (status !== 'loading') return;
    setLoadStep(0);
    const timers = [
      setTimeout(() => setLoadStep(1), 1200),
      setTimeout(() => setLoadStep(2), 3000),
      setTimeout(() => setLoadStep(3), 6000),
    ];
    return () => timers.forEach(clearTimeout);
  }, [status]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!url) return;
    setStatus('loading');
    setError('');
    setResult(null);
    try {
      const data = await runAudit(url, selectedModel);
      setResult(data);
      setStatus('success');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred during the audit');
      setStatus('error');
    }
  };

  const handleRetryWithModel = async (modelId: string) => {
    setSelectedModel(modelId);
    setStatus('loading');
    setError('');
    try {
      const data = await runAudit(url, modelId);
      setResult(data);
      setStatus('success');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred during the audit');
      setStatus('error');
    }
  };

  const hasAI = result?.analysis != null;
  const hasResults = result != null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-300">

      {/* ─── Top nav bar ────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-gray-950/80 border-b border-gray-200 dark:border-white/10">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-base tracking-tight">InsightScrape</span>
          </div>
          <div className="flex items-center gap-2">
            {result && (
              <span className="text-[11px] font-mono text-gray-400 dark:text-gray-500 hidden sm:block">
                {formatDuration(result.audit_duration_ms)}
              </span>
            )}
            <button
              onClick={() => setDark(!dark)}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
              aria-label="Toggle theme"
            >
              {dark ? <Sun className="w-5 h-5 text-amber-400" /> : <Moon className="w-5 h-5 text-gray-500" />}
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">

        {/* ─── Hero / Search ────────────────────────────────── */}
        {(!result || status !== 'success') && (
          <div className="text-center space-y-5 py-4 sm:py-8">
            <div className="space-y-2">
              <h1 className="text-2xl sm:text-4xl md:text-5xl font-black tracking-tight bg-gradient-to-r from-violet-600 to-indigo-600 dark:from-violet-400 dark:to-indigo-400 bg-clip-text text-transparent">
                AI-Powered Website Audit
              </h1>
              <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
                Enter any URL to get a deep, AI-driven analysis of SEO, content structure, accessibility, and UX.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="max-w-2xl mx-auto space-y-3">
              <div className="flex flex-col sm:flex-row gap-2 p-1.5 rounded-2xl bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10 shadow-lg shadow-gray-200/50 dark:shadow-black/20">
                <div className="flex-1 flex items-center gap-2 pl-3 sm:pl-4">
                  <Globe className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  <input
                    type="url"
                    placeholder="https://example.com"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    required
                    className="flex-1 bg-transparent outline-none text-sm py-2.5 placeholder-gray-400 dark:placeholder-gray-500 min-w-0"
                    disabled={status === 'warming' || status === 'loading'}
                  />
                </div>
                <button
                  type="submit"
                  disabled={status === 'warming' || status === 'loading'}
                  className="px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white rounded-xl font-semibold text-sm disabled:opacity-40 transition-all flex items-center justify-center gap-2 shadow-md shadow-violet-500/25"
                >
                  {status === 'warming' ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span className="hidden sm:inline">Connecting...</span>
                      <span className="sm:hidden">Wait...</span>
                    </>
                  ) : status === 'loading' ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span className="hidden sm:inline">Analyzing...</span>
                      <span className="sm:hidden">...</span>
                    </>
                  ) : (
                    <>
                      <Search className="w-3.5 h-3.5" />
                      Run Audit
                    </>
                  )}
                </button>
              </div>

              {/* Model selector */}
              {models.length > 0 && (
                <div className="flex items-center justify-center gap-2 text-xs">
                  <Cpu className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-gray-400 dark:text-gray-500">Model:</span>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-lg px-2 py-1 text-xs text-gray-700 dark:text-gray-300 outline-none focus:ring-1 focus:ring-violet-500"
                    disabled={status === 'loading'}
                  >
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} — {m.tier}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </form>
          </div>
        )}

        {/* ─── Inline URL bar when results are showing ──────── */}
        {hasResults && status === 'success' && (
          <div className="space-y-2">
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-2 p-1.5 rounded-xl bg-white dark:bg-white/5 border border-gray-200 dark:border-white/10">
              <div className="flex-1 flex items-center gap-2 pl-3">
                <Globe className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                  className="flex-1 bg-transparent outline-none text-sm py-2 placeholder-gray-400 min-w-0"
                />
              </div>
              <div className="flex gap-2">
                {models.length > 0 && (
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-white/10 rounded-lg px-2 py-2 text-xs text-gray-700 dark:text-gray-300 outline-none min-w-0"
                  >
                    {models.map((m) => (
                      <option key={m.id} value={m.id}>{m.name}</option>
                    ))}
                  </select>
                )}
                <button type="submit"
                  className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white rounded-lg font-semibold text-sm flex items-center justify-center gap-1.5 shadow-md shadow-violet-500/25 hover:from-violet-700 hover:to-indigo-700 transition-all whitespace-nowrap"
                >
                  <Search className="w-3.5 h-3.5" /> Re-Audit
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ─── Error ────────────────────────────────────────── */}
        {error && (
          <div className="flex items-start gap-3 p-4 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="text-sm break-all">{error}</div>
          </div>
        )}

        {/* ─── Loading ──────────────────────────────────────── */}
        {status === 'loading' && <LoadingState step={loadStep} />}

        {/* ═══════════════ RESULTS ════════════════════════════ */}
        {hasResults && status === 'success' && (
          <div className="space-y-6 animate-fade-up">

            {/* ── Audited URL banner ──────────────────────────── */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 min-w-0">
                <Shield className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                <span className="flex-shrink-0">Audit for</span>
                <a href={result.url} target="_blank" rel="noopener noreferrer"
                  className="text-violet-600 dark:text-violet-400 font-medium hover:underline inline-flex items-center gap-1 truncate min-w-0">
                  <span className="truncate">{result.url}</span>
                  <ExternalLink className="w-3 h-3 flex-shrink-0" />
                </a>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500 font-mono flex-shrink-0">
                <Clock className="w-3.5 h-3.5" /> {formatDuration(result.audit_duration_ms)}
              </div>
            </div>

            {/* ── AI Error Banner ─────────────────────────────── */}
            {result.ai_error && (
              <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0 space-y-2">
                    <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                      AI analysis unavailable
                    </p>
                    <p className="text-xs text-amber-700 dark:text-amber-300 break-all">{result.ai_error}</p>
                    <p className="text-xs text-amber-600 dark:text-amber-400">
                      Scraped metrics are shown below. Try a different model to get AI analysis:
                    </p>
                    {models.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {models
                          .filter((m) => m.id !== selectedModel)
                          .map((m) => (
                            <button
                              key={m.id}
                              onClick={() => handleRetryWithModel(m.id)}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-100 dark:bg-amber-500/20 text-amber-800 dark:text-amber-200 hover:bg-amber-200 dark:hover:bg-amber-500/30 transition-colors"
                            >
                              <RefreshCw className="w-3 h-3" />
                              {m.name}
                            </button>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ── Overall Score + Sub-scores (only if AI succeeded) ── */}
            {hasAI && result.analysis && (
              <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Big ring */}
                <div className="bg-white dark:bg-white/5 rounded-2xl border border-gray-200 dark:border-white/10 p-6 flex flex-col items-center justify-center relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-violet-500 to-indigo-500" />
                  <div className="relative">
                    <ScoreRing score={result.analysis.overall_score} size={140} />
                  </div>
                  <span className="mt-4 font-bold text-gray-700 dark:text-gray-300">Overall Score</span>
                </div>

                {/* Sub-score bars */}
                <div className="md:col-span-2 bg-white dark:bg-white/5 rounded-2xl border border-gray-200 dark:border-white/10 p-4 sm:p-6 space-y-3">
                  <h3 className="font-bold text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider">Category Breakdown</h3>
                  <div className="space-y-3">
                    <MiniBar score={result.analysis.structure_score} label="Structure & SEO" />
                    <MiniBar score={result.analysis.messaging_score} label="Messaging & Clarity" />
                    <MiniBar score={result.analysis.cta_score} label="Calls to Action" />
                    <MiniBar score={result.analysis.content_depth_score} label="Content Depth" />
                    <MiniBar score={result.analysis.ux_score} label="User Experience" />
                  </div>
                </div>
              </section>
            )}

            {/* ── Factual Metrics Grid ─────────────────────────── */}
            <section>
              <SectionHeader icon={BarChart3} title="Extracted Metrics" subtitle="Deterministic data — no AI involved" />

              {/* Scrape method badge */}
              <div className="flex flex-wrap items-center gap-2 mt-3 mb-1">
                <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${
                  result.metrics.scrape_method === 'playwright'
                    ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                    : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300'
                }`}>
                  {result.metrics.scrape_method === 'playwright' ? 'Full JS Rendering' : 'Static HTML'}
                </span>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  via {result.metrics.scrape_method}
                </span>
              </div>

              {/* Content quality warning */}
              {result.metrics.content_quality_warning && (
                <div className="flex items-start gap-2 p-3 mt-2 mb-3 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20">
                  <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-700 dark:text-amber-300">{result.metrics.content_quality_warning}</p>
                </div>
              )}

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-3">
                <MetricCard icon={FileText} label="Words" value={result.metrics.word_count.toLocaleString()} />
                <MetricCard icon={MousePointerClick} label="CTAs Found" value={result.metrics.cta_count} accent />
                <MetricCard icon={Link2} label="Internal Links" value={result.metrics.internal_links} />
                <MetricCard icon={ExternalLink} label="External Links" value={result.metrics.external_links} />
                <MetricCard icon={Image} label="Total Images" value={result.metrics.image_count} />
                <MetricCard icon={AlertTriangle} label="Missing Alt"
                  value={result.metrics.images_missing_alt_count}
                  warn={result.metrics.images_missing_alt_count > 0} />
                <MetricCard icon={Image} label="Decorative (alt='')"
                  value={result.metrics.images_decorative_alt_count} />
                <MetricCard icon={AlertTriangle} label="Missing Alt %"
                  value={`${result.metrics.images_missing_alt_pct}%`}
                  warn={result.metrics.images_missing_alt_pct > 0} />
              </div>

              {/* Rich Visual Media */}
              {(result.metrics.svg_count > 0 || result.metrics.has_video || result.metrics.has_canvas || result.metrics.has_css_animations || result.metrics.has_lottie || result.metrics.has_webgl_or_3d) && (
                <div className="mt-3">
                  <div className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 ml-1">Rich Visual Media</div>
                  <div className="flex flex-wrap gap-2">
                    {result.metrics.svg_count > 0 && <MediaBadge label={`${result.metrics.svg_count} SVGs`} icon={Layers} />}
                    {result.metrics.has_video && <MediaBadge label="Video" icon={Video} />}
                    {result.metrics.has_canvas && <MediaBadge label="Canvas" icon={Code2} />}
                    {result.metrics.has_css_animations && <MediaBadge label="CSS Animations" icon={Activity} />}
                    {result.metrics.has_lottie && <MediaBadge label="Lottie" icon={Sparkles} />}
                    {result.metrics.has_webgl_or_3d && <MediaBadge label="WebGL / 3D" icon={Layers} />}
                  </div>
                </div>
              )}

              {/* Meta info */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-4">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">Meta Title</div>
                    {result.metrics.meta_title_length != null && (
                      <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full ${
                        result.metrics.meta_title_length >= 50 && result.metrics.meta_title_length <= 60
                          ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                          : result.metrics.meta_title_length > 60
                            ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300'
                            : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300'
                      }`}>
                        {result.metrics.meta_title_length} chars
                      </span>
                    )}
                  </div>
                  <div className="text-sm font-medium truncate">{result.metrics.meta_title || <span className="text-rose-500">Missing</span>}</div>
                </div>
                <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-4">
                  <div className="flex items-center justify-between mb-1">
                    <div className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider">Meta Description</div>
                    {result.metrics.meta_description_length != null && (
                      <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full ${
                        result.metrics.meta_description_length >= 120 && result.metrics.meta_description_length <= 160
                          ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                          : result.metrics.meta_description_length > 160
                            ? 'bg-rose-100 dark:bg-rose-500/20 text-rose-700 dark:text-rose-300'
                            : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300'
                      }`}>
                        {result.metrics.meta_description_length} chars
                      </span>
                    )}
                  </div>
                  <div className="text-sm font-medium line-clamp-2">{result.metrics.meta_description || <span className="text-rose-500">Missing</span>}</div>
                </div>
              </div>

              {/* Technical SEO Signals */}
              <div className="mt-3">
                <div className="text-xs font-medium text-gray-400 dark:text-gray-500 uppercase tracking-wider mb-2 ml-1">Technical SEO Signals</div>
                <div className="flex flex-wrap gap-2">
                  <SEOSignalBadge label="Viewport" present={result.metrics.has_viewport_meta} />
                  <SEOSignalBadge label="Canonical" present={result.metrics.has_canonical} />
                  <SEOSignalBadge label="Open Graph" present={result.metrics.has_open_graph} />
                  <SEOSignalBadge label="Twitter Card" present={result.metrics.has_twitter_card} />
                  {result.metrics.structured_data_types.length > 0 && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-300">
                      <CheckCircle2 className="w-3 h-3" /> Schema: {result.metrics.structured_data_types.join(', ')}
                    </span>
                  )}
                </div>
              </div>

              {/* Heading hierarchy */}
              {result.metrics.heading_hierarchy.length > 0 && (
                <details className="mt-3 group">
                  <summary className="flex items-center gap-2 cursor-pointer text-sm font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
                    <Hash className="w-4 h-4" />
                    Heading Hierarchy ({result.metrics.heading_hierarchy.length} headings)
                    <ChevronDown className="w-3.5 h-3.5 transition-transform group-open:rotate-180" />
                  </summary>
                  <div className="mt-2 bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-4 space-y-1.5 max-h-64 overflow-y-auto">
                    {result.metrics.heading_hierarchy.map(([tag, text], i) => {
                      const indent = parseInt(tag.replace('H', '')) - 1;
                      return (
                        <div key={i} className="flex items-baseline gap-2 text-sm" style={{ paddingLeft: indent * 16 }}>
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 flex-shrink-0">
                            {tag}
                          </span>
                          <span className="text-gray-600 dark:text-gray-400 truncate">{text}</span>
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}
            </section>

            {/* ── AI Analysis Sections (only if AI succeeded) ─── */}
            {hasAI && result.analysis && (
              <section>
                <SectionHeader
                  icon={Sparkles}
                  title="AI-Generated Analysis"
                  subtitle={`Powered by ${result.prompt_logs?.[0]?.model || 'Gemini'}`}
                  badge="AI"
                />
                <div className="mt-4 space-y-4">
                  <AnalysisCard label="Structure & SEO" icon={Search} analysis={result.analysis.structure_analysis} />
                  <AnalysisCard label="Messaging" icon={Type} analysis={result.analysis.messaging_analysis} />
                  <AnalysisCard label="Calls to Action" icon={MousePointerClick} analysis={result.analysis.cta_analysis} />
                  <AnalysisCard label="Content Depth" icon={FileText} analysis={result.analysis.content_depth_analysis} />
                  <AnalysisCard label="User Experience" icon={Eye} analysis={result.analysis.ux_analysis} />
                </div>
              </section>
            )}

            {/* ── Recommendations (only if available) ──────────── */}
            {result.recommendations.length > 0 && (
              <section>
                <SectionHeader icon={Zap} title="Prioritized Recommendations" subtitle="Actionable fixes grounded in metrics" />
                <div className="mt-4 space-y-3">
                  {result.recommendations.map((rec, i) => (
                    <div key={i}
                      className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 p-4 hover:shadow-md dark:hover:shadow-black/20 transition-shadow"
                    >
                      <div className="flex items-start gap-3">
                        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm ${priorityStyle(rec.priority)}`}>
                          P{rec.priority}
                        </div>
                        <div className="flex-1 min-w-0 space-y-2">
                          <div className="flex items-start gap-2 flex-wrap">
                            <h3 className="font-bold text-sm">{rec.title}</h3>
                            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-300 capitalize">
                              {categoryIcon(rec.category)} {rec.category}
                            </span>
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">{rec.description}</p>
                          <div className="flex flex-col sm:flex-row gap-2 text-xs">
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-amber-700 dark:text-amber-300 font-medium">
                              <BarChart3 className="w-3 h-3" /> {rec.grounded_metric}
                            </span>
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-50 dark:bg-sky-500/10 border border-sky-200 dark:border-sky-500/20 text-sky-700 dark:text-sky-300 font-medium">
                              <ArrowRight className="w-3 h-3" /> {rec.action}
                            </span>
                          </div>
                          {rec.expected_impact && (
                            <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                              Expected Impact: {rec.expected_impact}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* ── Transparency Panel (only if prompt logs exist) ─ */}
            {result.prompt_logs.length > 0 && (
              <section>
                <SectionHeader icon={Terminal} title="Prompt Logs & Reasoning Trace" subtitle="Full AI transparency — see the exact prompts and raw model responses" />
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1 ml-10 mb-3">
                  These logs show exactly how the AI analysis was orchestrated — the system prompts, structured inputs, and raw outputs.
                </p>
                <div className="mt-2 rounded-2xl overflow-hidden border border-gray-800 dark:border-white/10 bg-gray-900 dark:bg-black/40">
                  {result.prompt_logs.map((log, i) => (
                    <details key={i} className="group border-b border-gray-800 dark:border-white/5 last:border-0">
                      <summary className="flex justify-between items-center cursor-pointer list-none p-3 sm:p-4 hover:bg-white/5 transition-colors select-none">
                        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                          <span className="w-6 h-6 rounded bg-violet-500/20 flex items-center justify-center text-violet-400 font-mono text-xs font-bold flex-shrink-0">
                            {i + 1}
                          </span>
                          <span className="text-blue-400 font-mono text-xs sm:text-sm font-medium truncate">{log.stage}</span>
                          {log.token_usage && (
                            <span className="text-[10px] font-mono text-gray-500 hidden sm:inline-block flex-shrink-0">
                              {log.token_usage.total_token_count?.toLocaleString()} tokens
                            </span>
                          )}
                        </div>
                        <ChevronDown className="w-4 h-4 text-gray-500 transition-transform group-open:rotate-180 flex-shrink-0" />
                      </summary>
                      <div className="px-3 sm:px-4 pb-4 space-y-3 text-xs font-mono overflow-x-auto">
                        <div className="rounded-lg bg-black/50 p-3 space-y-1">
                          <div className="text-gray-500 text-[10px] uppercase tracking-widest">System Prompt</div>
                          <div className="text-emerald-400/90 whitespace-pre-wrap leading-relaxed break-all">{log.system_prompt}</div>
                        </div>
                        <div className="rounded-lg bg-black/50 p-3 space-y-1">
                          <div className="text-gray-500 text-[10px] uppercase tracking-widest">User Prompt → {log.model}</div>
                          <ExpandablePrompt text={log.user_prompt} />
                        </div>
                        <div className="rounded-lg bg-black/50 p-3 space-y-1">
                          <div className="text-gray-500 text-[10px] uppercase tracking-widest">Raw JSON Output</div>
                          <div className="text-sky-300/90 whitespace-pre-wrap leading-relaxed break-all">{log.raw_response}</div>
                        </div>
                      </div>
                    </details>
                  ))}
                </div>
              </section>
            )}

          </div>
        )}
      </main>

      {/* ─── Footer ─────────────────────────────────────────── */}
      <footer className="border-t border-gray-200 dark:border-white/5 mt-12 py-6 text-center text-xs text-gray-400 dark:text-gray-600">
        Built with FastAPI, React, Tailwind CSS and Gemini AI
      </footer>
    </div>
  );
};

/* ═══════════════════ SUB-COMPONENTS ═════════════════════════ */

const ExpandablePrompt = ({ text }: { text: string }) => {
  const [expanded, setExpanded] = useState(false);
  const PREVIEW_LEN = 1500;
  const isLong = text.length > PREVIEW_LEN;

  return (
    <div className="text-amber-300/90 whitespace-pre-wrap leading-relaxed break-all">
      {isLong && !expanded ? text.substring(0, PREVIEW_LEN) : text}
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="block mt-2 text-[11px] font-sans font-semibold text-violet-400 hover:text-violet-300 transition-colors"
        >
          {expanded ? '▲ Collapse' : `▼ Show full prompt (${text.length.toLocaleString()} chars)`}
        </button>
      )}
    </div>
  );
};

const SectionHeader = ({ icon: Icon, title, subtitle, badge }: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  badge?: string;
}) => (
  <div className="flex items-start gap-3">
    <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-br from-violet-500/10 to-indigo-500/10 dark:from-violet-500/20 dark:to-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
      <Icon className="w-4 h-4 text-violet-600 dark:text-violet-400" />
    </div>
    <div>
      <div className="flex items-center gap-2">
        <h2 className="text-lg sm:text-xl font-bold">{title}</h2>
        {badge && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-500/20 text-violet-700 dark:text-violet-300 uppercase tracking-wider">
            {badge}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
    </div>
  </div>
);

const MetricCard = ({ icon: Icon, label, value, warn, accent }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  warn?: boolean;
  accent?: boolean;
}) => (
  <div className={`p-3.5 sm:p-4 rounded-xl border transition-colors ${
    warn
      ? 'bg-rose-50 dark:bg-rose-500/5 border-rose-200 dark:border-rose-500/20'
      : accent
        ? 'bg-violet-50 dark:bg-violet-500/5 border-violet-200 dark:border-violet-500/20'
        : 'bg-white dark:bg-white/5 border-gray-200 dark:border-white/10'
  }`}>
    <div className="flex items-center gap-1.5 mb-1.5 sm:mb-2">
      <Icon className={`w-3.5 h-3.5 ${warn ? 'text-rose-500' : accent ? 'text-violet-500' : 'text-gray-400 dark:text-gray-500'}`} />
      <span className="text-[11px] sm:text-xs font-medium text-gray-500 dark:text-gray-400">{label}</span>
    </div>
    <div className={`text-xl sm:text-2xl font-bold ${warn ? 'text-rose-600 dark:text-rose-400' : accent ? 'text-violet-600 dark:text-violet-400' : ''}`}>
      {value}
    </div>
  </div>
);

const AnalysisCard = ({ label, icon: Icon, analysis }: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  analysis: SectionAnalysis;
}) => (
  <div className="bg-white dark:bg-white/5 rounded-xl border border-gray-200 dark:border-white/10 overflow-hidden">
    <div className="flex items-center justify-between p-4 pb-3">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-gray-400 dark:text-gray-500" />
        <h3 className="font-bold text-sm sm:text-base">{label}</h3>
      </div>
      <span className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${scoreBg(analysis.score)}`}>
        {analysis.score}/10
      </span>
    </div>
    <div className="px-4 pb-4 space-y-3">
      <div className="prose prose-sm max-w-none text-gray-600 dark:text-gray-400 text-[13px] sm:text-sm leading-relaxed">
        <ReactMarkdown>{analysis.findings}</ReactMarkdown>
      </div>
      <div className="text-xs bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5 rounded-lg p-3">
        <span className="font-semibold text-gray-500 dark:text-gray-400">Evidence: </span>
        <span className="text-gray-600 dark:text-gray-400">{analysis.evidence}</span>
      </div>
    </div>
  </div>
);

const MediaBadge = ({ label, icon: Icon }: {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}) => (
  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/20 text-violet-700 dark:text-violet-300">
    <Icon className="w-3 h-3" /> {label}
  </span>
);

const SEOSignalBadge = ({ label, present }: { label: string; present: boolean }) => (
  <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border ${
    present
      ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20 text-emerald-700 dark:text-emerald-300'
      : 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20 text-rose-700 dark:text-rose-300'
  }`}>
    {present ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />} {label}
  </span>
);
