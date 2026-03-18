import React, { useState, useEffect } from 'react';
import { checkHealth, runAudit, AuditResult, SectionAnalysis } from '../api/audit';
import ReactMarkdown from 'react-markdown';

export const AuditApp = () => {
    const [url, setUrl] = useState('');
    const [status, setStatus] = useState<'idle' | 'warming' | 'ready' | 'loading' | 'success' | 'error'>('warming');
    const [error, setError] = useState('');
    const [result, setResult] = useState<AuditResult | null>(null);

    useEffect(() => {
        let isMounted = true;
        const warmup = async () => {
            let healthy = false;
            try {
               healthy = await checkHealth();
            } catch (e) {
               console.warn(e);
            }
            if (isMounted) {
                if (healthy) setStatus('ready');
                else {
                    setTimeout(async () => {
                        if (isMounted) setStatus('ready');
                    }, 2500); // Give up warming and let user try
                }
            }
        };
        warmup();
        return () => { isMounted = false; };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!url) return;
        setStatus('loading');
        setError('');
        setResult(null);

        try {
            const data = await runAudit(url);
            setResult(data);
            setStatus('success');
        } catch (err: any) {
            setError(err.message || 'An error occurred during the audit');
            setStatus('error');
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans text-gray-900 text-left">
            <div className="max-w-5xl mx-auto space-y-8">
                <header className="text-center space-y-4">
                    <h1 className="text-4xl font-bold text-gray-900">InsightScrape</h1>
                    <p className="text-lg text-gray-600">AI-Powered Website Audit Tool</p>
                </header>

                <form onSubmit={handleSubmit} className="flex gap-4 max-w-2xl mx-auto">
                    <input
                        type="url"
                        placeholder="https://example.com"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        required
                        className="flex-1 px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                        disabled={status === 'warming' || status === 'loading'}
                    />
                    <button
                        type="submit"
                        disabled={status === 'warming' || status === 'loading'}
                        className="px-8 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
                    >
                        {status === 'warming' ? 'Warming API...' : status === 'loading' ? 'Auditing...' : 'Audit Page'}
                    </button>
                </form>

                {error && (
                    <div className="p-4 bg-red-50 text-red-700 rounded-lg border border-red-200">
                        {error}
                    </div>
                )}

                {status === 'loading' && (
                    <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                        <p className="mt-4 text-gray-600">Fetching page and analyzing with Gemini 2.0 Flash...</p>
                    </div>
                )}

                {result && status === 'success' && (
                    <div className="space-y-12">
                        {/* Factual Metrics */}
                        <section>
                            <h2 className="text-2xl font-bold mb-4">Extracted Factual Metrics</h2>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <MetricCard label="Word Count" value={result.metrics.word_count} />
                                <MetricCard label="CTAs Found" value={result.metrics.cta_count} />
                                <MetricCard label="Internal Links" value={result.metrics.internal_links} />
                                <MetricCard label="External Links" value={result.metrics.external_links} />
                                <MetricCard label="Total Images" value={result.metrics.image_count} />
                                <MetricCard 
                                    label="Missing Alt Text" 
                                    value={result.metrics.images_missing_alt_count} 
                                    highlight={result.metrics.images_missing_alt_count > 0 ? 'red' : 'green'} 
                                />
                                <MetricCard 
                                    label="Decorative Images" 
                                    value={result.metrics.images_decorative_alt_count} 
                                    subtext="(Empty alt tag)"
                                />
                                <MetricCard 
                                    label="Missing Alt %" 
                                    value={`${result.metrics.images_missing_alt_pct}%`} 
                                    highlight={result.metrics.images_missing_alt_pct > 0 ? 'red' : 'green'} 
                                />
                            </div>
                        </section>

                        {/* AI Insights Panel */}
                        <section>
                            <div className="flex items-center gap-2 mb-4">
                                <h2 className="text-2xl font-bold">AI-Generated Analysis</h2>
                                <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded font-medium border border-purple-200">
                                    Gemini 2.0 Flash
                                </span>
                            </div>
                            
                            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                                <div className="p-6 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                                    <h3 className="font-bold text-gray-800">Overall Score</h3>
                                    <div className={`text-2xl font-bold ${result.analysis.overall_score >= 8 ? 'text-green-600' : result.analysis.overall_score >= 5 ? 'text-yellow-600' : 'text-red-600'}`}>
                                        {result.analysis.overall_score} / 10
                                    </div>
                                </div>
                                <div className="divide-y divide-gray-100">
                                    <AnalysisRow label="Structure" analysis={result.analysis.structure_analysis} />
                                    <AnalysisRow label="Messaging" analysis={result.analysis.messaging_analysis} />
                                    <AnalysisRow label="CTAs" analysis={result.analysis.cta_analysis} />
                                    <AnalysisRow label="Content Depth" analysis={result.analysis.content_depth_analysis} />
                                    <AnalysisRow label="UX" analysis={result.analysis.ux_analysis} />
                                </div>
                            </div>
                        </section>

                        {/* Recommendations */}
                        <section>
                            <h2 className="text-2xl font-bold mb-4">Prioritized Recommendations</h2>
                            <div className="space-y-4">
                                {result.recommendations.map((rec, i) => (
                                    <div key={i} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 flex gap-4">
                                        <div className="flex-shrink-0">
                                            <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full font-bold text-sm ${rec.priority === 1 ? 'bg-red-100 text-red-700' : rec.priority === 2 ? 'bg-orange-100 text-orange-700' : 'bg-blue-100 text-blue-700'}`}>
                                                {rec.priority}
                                            </span>
                                        </div>
                                        <div className="space-y-2">
                                            <h3 className="font-bold text-lg">{rec.title}</h3>
                                            <p className="text-gray-600">{rec.description}</p>
                                            <div className="inline-flex items-center gap-2 text-sm bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200">
                                                <span className="font-medium text-gray-500">Metric Evidence:</span>
                                                <span className="text-gray-700">{rec.grounded_metric}</span>
                                            </div>
                                            <div className="text-sm font-medium text-blue-700 mt-2">
                                                Action: {rec.action}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        {/* Transparency Panel */}
                        <section className="bg-gray-900 text-gray-300 rounded-xl overflow-hidden mt-12">
                            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                                <h2 className="text-xl font-mono text-gray-100 flex items-center gap-2">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-blue-400">
                                        <path d="M4 6H20M4 12H20M4 18H20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                    </svg>
                                    AI Reasoning Trace
                                </h2>
                                <span className="text-xs tracking-widest uppercase font-mono">Transparency Layer</span>
                            </div>
                            <div className="p-0">
                                {result.prompt_logs.map((log, i) => (
                                    <details key={i} className="group border-b border-gray-800 last:border-0" open={i===0}>
                                        <summary className="flex justify-between items-center font-medium cursor-pointer list-none p-4 hover:bg-gray-800 transition-colors">
                                            <span className="text-blue-400 font-mono">{log.stage}</span>
                                            <span className="transition group-open:rotate-180">
                                                <svg fill="none" height="24" shapeRendering="geometricPrecision" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" viewBox="0 0 24 24" width="24"><path d="M6 9l6 6 6-6"></path></svg>
                                            </span>
                                        </summary>
                                        <div className="p-4 text-sm font-mono bg-gray-950 overflow-x-auto border-t border-gray-800">
                                            <div className="mb-4">
                                                <div className="text-gray-500 mb-1">// SYSTEM PROMPT</div>
                                                <div className="text-green-400 whitespace-pre-wrap">{log.system_prompt}</div>
                                            </div>
                                            <div className="mb-4">
                                                <div className="text-gray-500 mb-1">// USER PROMPT sent to {log.model}</div>
                                                <div className="text-yellow-300 whitespace-pre-wrap">{log.user_prompt.substring(0, 1000)}{log.user_prompt.length > 1000 ? '\n\n...[TRUNCATED IN UI]...' : ''}</div>
                                            </div>
                                            <div>
                                                <div className="text-gray-500 mb-1">// RAW OUTPUT JSON</div>
                                                <div className="text-blue-300 whitespace-pre-wrap">{log.raw_response}</div>
                                            </div>
                                        </div>
                                    </details>
                                ))}
                            </div>
                        </section>

                    </div>
                )}
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, subtext, highlight }: { label: string, value: string | number, subtext?: string, highlight?: 'red'|'green' }) => (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-200">
        <div className="text-sm text-gray-500 font-medium">{label}</div>
        <div className={`text-2xl font-bold mt-1 ${highlight === 'red' ? 'text-red-600' : highlight === 'green' ? 'text-green-600' : 'text-gray-900'}`}>
            {value}
        </div>
        {subtext && <div className="text-xs text-gray-400 mt-1">{subtext}</div>}
    </div>
);

const AnalysisRow = ({ label, analysis }: { label: string, analysis: SectionAnalysis }) => (
    <div className="p-6 md:flex gap-6 items-start">
        <div className="md:w-1/4 mb-4 md:mb-0">
            <div className="font-bold text-gray-800">{label}</div>
            <div className="mt-2 flex items-center gap-2">
                <span className={`px-2 py-1 rounded text-sm font-bold ${analysis.score >= 8 ? 'bg-green-100 text-green-800' : analysis.score >= 5 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'}`}>
                    {analysis.score} / 10
                </span>
            </div>
        </div>
        <div className="md:w-3/4 space-y-3">
            <div className="prose prose-sm max-w-none text-gray-700">
                <ReactMarkdown>{analysis.findings}</ReactMarkdown>
            </div>
            <div className="text-sm bg-gray-50 p-3 rounded-lg border border-gray-200">
                <span className="font-semibold text-gray-700">Evidence:</span> {analysis.evidence}
            </div>
        </div>
    </div>
);
