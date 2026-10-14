import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Database,
  ExternalLink,
  Gauge,
  Loader2,
  Table2,
  BarChart3,
  XCircle,
} from 'lucide-react';
import { getEvalHistory, getLatestEvalReport } from '../lib/api';
import type { EvalHistoryEntry, EvalReport, PageRef, QualityGate } from '../lib/evalTypes';
import { RETRIEVAL_VARIANTS, VARIANT_COLORS, VARIANT_LABELS } from '../lib/evalTheme';
import { GroupedMetricBars, LatencyBars, Legend } from '../components/evals/EvalCharts';

const SCORE_METRICS = [
  { key: 'hit@1', label: 'Hit@1' },
  { key: 'hit@3', label: 'Hit@3' },
  { key: 'mrr', label: 'MRR' },
  { key: 'ndcg@5', label: 'nDCG@5' },
  { key: 'recall@5', label: 'Recall@5' },
  { key: 'answer_term_recall', label: 'Answer-term recall' },
];

const METRIC_HELP: Record<string, string> = {
  'Hit@k': 'Share of queries with a correct page in the top k results.',
  MRR: 'Mean reciprocal rank: 1.0 means the correct page is always ranked first.',
  'nDCG@5': 'Ranking quality that rewards correct pages near the top, normalised to 1.0.',
  'Recall@5': 'Share of all correct pages (some queries have two) found in the top 5.',
  'Answer-term recall': 'Share of expected answer terms present in the top-3 retrieved text, a proxy for whether the LLM has the facts it needs.',
  Leakage: 'Share of side-panel results that come from the PDF that is already open. Must be 0.',
  'Off-topic': 'Share of side-panel results from an unrelated subject (e.g. a cloud-computing PDF suggested for a biology page).',
};

const fmt = (value: number | null | undefined, digits = 2) => (
  value === null || value === undefined ? '—' : value.toFixed(digits)
);

const StatusChip = ({ passed, label }: { passed: boolean; label?: string }) => (
  <span
    className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
      passed
        ? 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200'
        : 'border-rose-400/40 bg-rose-400/10 text-rose-200'
    }`}
  >
    {passed ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
    {label ?? (passed ? 'Pass' : 'Fail')}
  </span>
);

const StatTile = ({ label, value, hint }: { label: string; value: string; hint: string }) => (
  <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
    <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
    <div className="mt-1 text-3xl font-semibold tabular-nums text-white">{value}</div>
    <div className="mt-1 text-xs text-slate-400">{hint}</div>
  </div>
);

const Section = ({ title, subtitle, actions, children }: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) => (
  <section className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        {subtitle && <p className="mt-1 max-w-3xl text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions}
    </div>
    {children}
  </section>
);

const ViewToggle = ({ asTable, onChange }: { asTable: boolean; onChange: (value: boolean) => void }) => (
  <button
    type="button"
    onClick={() => onChange(!asTable)}
    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-600 px-2.5 py-1 text-xs text-slate-300 transition hover:border-slate-400 hover:text-white"
  >
    {asTable ? <BarChart3 className="h-3.5 w-3.5" /> : <Table2 className="h-3.5 w-3.5" />}
    {asTable ? 'Show chart' : 'Show table'}
  </button>
);

const EvalsPage = () => {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [history, setHistory] = useState<EvalHistoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [scoresAsTable, setScoresAsTable] = useState(false);
  const [latencyAsTable, setLatencyAsTable] = useState(false);
  const [queryVariant, setQueryVariant] = useState<(typeof RETRIEVAL_VARIANTS)[number]>('hybrid');
  const [queryCategory, setQueryCategory] = useState('all');
  const [missesOnly, setMissesOnly] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getLatestEvalReport(), getEvalHistory().catch(() => [])])
      .then(([latest, runs]) => {
        if (cancelled) return;
        setReport(latest);
        setHistory(runs);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load the eval report.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const docNames = useMemo(() => Object.fromEntries(
    (report?.dataset.documents ?? []).map((doc) => [doc.id, doc.name.replace(/\.pdf$/i, '')])
  ), [report]);
  const pageLabel = ([doc, page]: PageRef) => `${docNames[doc] ?? doc} p${page}`;

  const filteredQueries = useMemo(() => {
    if (!report) return [];
    return report.variants[queryVariant].queries.filter((query) => (
      (queryCategory === 'all' || query.category === queryCategory)
      && (!missesOnly || query['hit@1'] < 1)
    ));
  }, [report, queryVariant, queryCategory, missesOnly]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-2 bg-slate-950 text-slate-300">
        <Loader2 className="h-5 w-5 animate-spin" /> Loading eval report…
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
        <div className="max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 text-center">
          <p className="text-lg text-white">No eval report available</p>
          <p className="mt-2 text-sm text-slate-400">{error}</p>
          <pre className="mt-4 rounded-lg bg-slate-950 p-3 text-left text-xs text-slate-300">cd backend{'\n'}.venv/Scripts/python -m app.evals.harness</pre>
          <Link to="/library" className="mt-4 inline-block text-sm text-cyan-300 hover:text-cyan-200">Back to library</Link>
        </div>
      </div>
    );
  }

  const { variants, gates, ingest } = report;
  const hybrid = variants.hybrid.summary;
  const crossDoc = variants.cross_document.summary;
  const scoreValues = Object.fromEntries(
    RETRIEVAL_VARIANTS.map((name) => [name, variants[name].summary as unknown as Record<string, number>])
  );
  const latency = Object.fromEntries(
    RETRIEVAL_VARIANTS.map((name) => [name, { p50: variants[name].summary.latency_p50_ms, p95: variants[name].summary.latency_p95_ms }])
  );
  const gateLabel = (gate: QualityGate) => `${gate.variant.replace('_', ' ')} · ${gate.metric.replace('cross_doc_', '')}`;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-950 to-indigo-950 text-slate-200">
      <header className="sticky top-0 z-20 border-b border-slate-700 bg-slate-900/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Link to="/library" className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Back to library">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <Gauge className="h-5 w-5 text-cyan-300" />
            <div>
              <h1 className="text-xl font-semibold text-white">RAG evaluation</h1>
              <p className="text-xs text-slate-400">
                Run {report.run_id} · {new Date(report.created_at).toLocaleString()}
                {report.git_commit ? ` · ${report.git_commit}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`rounded-full border px-2.5 py-0.5 text-xs ${report.mode === 'live' ? 'border-cyan-400/40 text-cyan-200' : 'border-amber-400/40 text-amber-200'}`}>
              {report.mode === 'live' ? 'Live NVIDIA models' : 'Offline embedder'}
            </span>
            <StatusChip passed={report.passed} label={report.passed ? 'All gates pass' : `${gates.filter((g) => !g.passed).length} gate(s) failing`} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        {report.mode === 'offline' && (
          <p className="rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            This report used the deterministic offline embedder. It checks pipeline mechanics, not NVIDIA model quality.
          </p>
        )}

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <StatTile label="Hybrid MRR" value={fmt(hybrid.mrr)} hint="Rank of first correct page" />
          <StatTile label="Hybrid Hit@3" value={`${Math.round(hybrid['hit@3'] * 100)}%`} hint={`${hybrid.queries} labelled queries`} />
          <StatTile label="Side-panel Hit@3" value={`${Math.round(crossDoc['cross_doc_hit@3'] * 100)}%`} hint={`${crossDoc.cases} cross-PDF cases`} />
          <StatTile label="Side-panel leakage" value={`${Math.round(crossDoc.cross_doc_leakage * 100)}%`} hint="Open PDF shown as related" />
          <StatTile label="Hybrid p95" value={`${Math.round(hybrid.latency_p95_ms)} ms`} hint="Embedding + search" />
        </div>

        <Section
          title="Retrieval quality by variant"
          subtitle={`${report.dataset.queries} queries over ${report.dataset.documents.length} PDFs, relevance judged per page. Best value in each row is labelled; hover any bar for its value.`}
          actions={<ViewToggle asTable={scoresAsTable} onChange={setScoresAsTable} />}
        >
          <div className="mb-3"><Legend series={[...RETRIEVAL_VARIANTS]} /></div>
          {scoresAsTable ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-2 pr-4">Metric</th>
                    {RETRIEVAL_VARIANTS.map((name) => <th key={name} className="py-2 pr-4">{VARIANT_LABELS[name]}</th>)}
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {SCORE_METRICS.map((metric) => (
                    <tr key={metric.key} className="border-t border-slate-800">
                      <td className="py-2 pr-4 text-slate-300">{metric.label}</td>
                      {RETRIEVAL_VARIANTS.map((name) => <td key={name} className="py-2 pr-4">{fmt(scoreValues[name][metric.key], 3)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <GroupedMetricBars metrics={SCORE_METRICS} series={[...RETRIEVAL_VARIANTS]} values={scoreValues} />
          )}
          <p className="mt-3 text-xs text-slate-400">
            Reranker {variants.hybrid_rerank.reranker_applied ? `applied (${report.config.reranker_model})` : 'unavailable for this run; that variant fell back to fused ranking'}.
            Hybrid fuses {report.config.fusion_weights.vector} × vector similarity + {report.config.fusion_weights.keyword} × BM25.
          </p>
        </Section>

        <Section
          title="Retrieval latency"
          subtitle="Bar is p50; the whisker reaches p95. Includes the hosted query-embedding call, so it reflects real page-turn cost."
          actions={<ViewToggle asTable={latencyAsTable} onChange={setLatencyAsTable} />}
        >
          {latencyAsTable ? (
            <table className="w-full text-sm tabular-nums">
              <thead className="text-left text-xs uppercase text-slate-400">
                <tr><th className="py-2">Variant</th><th className="py-2">p50 (ms)</th><th className="py-2">p95 (ms)</th></tr>
              </thead>
              <tbody>
                {RETRIEVAL_VARIANTS.map((name) => (
                  <tr key={name} className="border-t border-slate-800">
                    <td className="py-2">{VARIANT_LABELS[name]}</td>
                    <td className="py-2">{fmt(latency[name].p50, 1)}</td>
                    <td className="py-2">{fmt(latency[name].p95, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <LatencyBars series={[...RETRIEVAL_VARIANTS]} latency={latency} />
          )}
        </Section>

        <Section title="Quality gates" subtitle="A run passes only if every gate holds. Gates guard the paths the app actually uses.">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-400">
                <tr><th className="py-2 pr-4">Gate</th><th className="py-2 pr-4">Target</th><th className="py-2 pr-4">Actual</th><th className="py-2 pr-4">Status</th><th className="py-2">Why it matters</th></tr>
              </thead>
              <tbody>
                {gates.map((gate) => (
                  <tr key={`${gate.variant}-${gate.metric}`} className="border-t border-slate-800 align-top">
                    <td className="py-2 pr-4 text-slate-200">{gateLabel(gate)}</td>
                    <td className="py-2 pr-4 tabular-nums text-slate-300">{gate.op} {gate.threshold}</td>
                    <td className="py-2 pr-4 tabular-nums text-white">{fmt(gate.value, gate.metric.includes('latency') ? 0 : 3)}</td>
                    <td className="py-2 pr-4"><StatusChip passed={gate.passed} /></td>
                    <td className="py-2 text-xs text-slate-400">{gate.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section title="By query type (hybrid)" subtitle="Paraphrases have little word overlap with the source; keyword queries test exact terms and acronyms.">
          <div className="overflow-x-auto">
            <table className="w-full text-sm tabular-nums">
              <thead className="text-left text-xs uppercase text-slate-400">
                <tr><th className="py-2 pr-4">Category</th><th className="py-2 pr-4">Queries</th><th className="py-2 pr-4">Hit@1</th><th className="py-2 pr-4">Hit@3</th><th className="py-2 pr-4">MRR</th><th className="py-2">Answer-term recall</th></tr>
              </thead>
              <tbody>
                {Object.entries(variants.hybrid.by_category).map(([category, summary]) => (
                  <tr key={category} className="border-t border-slate-800">
                    <td className="py-2 pr-4 capitalize text-slate-200">{category.replace('_', ' ')}</td>
                    <td className="py-2 pr-4">{summary.queries}</td>
                    <td className="py-2 pr-4">{fmt(summary['hit@1'])}</td>
                    <td className="py-2 pr-4">{fmt(summary['hit@3'])}</td>
                    <td className="py-2 pr-4">{fmt(summary.mrr)}</td>
                    <td className="py-2">{fmt(summary.answer_term_recall)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        <Section
          title="Per-query results"
          subtitle="Correct pages are highlighted in the retrieved list. Use “misses only” to see where ranking goes wrong."
          actions={(
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <select
                value={queryVariant}
                onChange={(event) => setQueryVariant(event.target.value as typeof queryVariant)}
                className="rounded-lg border border-slate-600 bg-slate-900 px-2 py-1 text-slate-200"
                aria-label="Variant"
              >
                {RETRIEVAL_VARIANTS.map((name) => <option key={name} value={name}>{VARIANT_LABELS[name]}</option>)}
              </select>
              <select
                value={queryCategory}
                onChange={(event) => setQueryCategory(event.target.value)}
                className="rounded-lg border border-slate-600 bg-slate-900 px-2 py-1 text-slate-200"
                aria-label="Category"
              >
                <option value="all">All categories</option>
                {report.dataset.categories.map((category) => <option key={category} value={category}>{category.replace('_', ' ')}</option>)}
              </select>
              <label className="inline-flex items-center gap-1.5 text-slate-300">
                <input type="checkbox" checked={missesOnly} onChange={(event) => setMissesOnly(event.target.checked)} />
                Misses only
              </label>
            </div>
          )}
        >
          <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: VARIANT_COLORS[queryVariant] }} />
            Showing {filteredQueries.length} of {variants[queryVariant].queries.length} queries
          </div>
          <div className="max-h-[28rem] overflow-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-900 text-left text-xs uppercase text-slate-400">
                <tr><th className="py-2 pr-3">Query</th><th className="py-2 pr-3">Retrieved (top 3)</th><th className="py-2 pr-3">Rank of first hit</th><th className="py-2">Latency</th></tr>
              </thead>
              <tbody>
                {filteredQueries.map((query) => {
                  const relevant = new Set(query.relevant.map((ref) => ref.join(':')));
                  return (
                    <tr key={query.id} className="border-t border-slate-800 align-top">
                      <td className="py-2 pr-3">
                        <div className="text-slate-100">{query.query}</div>
                        <div className="text-xs text-slate-500">{query.id} · {query.category.replace('_', ' ')}</div>
                      </td>
                      <td className="py-2 pr-3">
                        <ol className="space-y-0.5 text-xs">
                          {query.retrieved.slice(0, 3).map((ref) => {
                            const hit = relevant.has(ref.join(':'));
                            return (
                              <li key={ref.join(':')} className={hit ? 'text-emerald-200' : 'text-slate-400'}>
                                {hit ? '✓ ' : '· '}{pageLabel(ref)}
                              </li>
                            );
                          })}
                        </ol>
                      </td>
                      <td className="py-2 pr-3 tabular-nums">
                        {query.mrr > 0 ? (
                          <span className={query.mrr === 1 ? 'text-emerald-200' : 'text-amber-200'}>#{Math.round(1 / query.mrr)}</span>
                        ) : (
                          <span className="text-rose-200">not in top {report.config.top_k}</span>
                        )}
                      </td>
                      <td className="py-2 tabular-nums text-slate-400">{Math.round(query.latency_ms)} ms</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Section>

        <Section
          title="Side panel: related content from other PDFs"
          subtitle={`Mirrors /api/recommendations: the open page's text is the query, the open PDF is excluded, matches scoring below ${fmt(crossDoc.min_score)} are hidden, and up to 3 are shown. Off-topic results: ${Math.round(crossDoc.cross_doc_off_topic * 100)}% · average matches shown: ${fmt(crossDoc.cross_doc_avg_shown, 1)}.`}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-400">
                <tr><th className="py-2 pr-3">Open page</th><th className="py-2 pr-3">Expected</th><th className="py-2 pr-3">Shown in panel</th><th className="py-2">Result</th></tr>
              </thead>
              <tbody>
                {variants.cross_document.cases.map((item) => {
                  const relevant = new Set(item.relevant.map((ref) => ref.join(':')));
                  return (
                    <tr key={item.id} className="border-t border-slate-800 align-top">
                      <td className="py-2 pr-3 text-slate-200">{pageLabel(item.source)}</td>
                      <td className="py-2 pr-3 text-xs text-slate-300">{item.relevant.map(pageLabel).join(', ')}</td>
                      <td className="py-2 pr-3">
                        <ol className="space-y-0.5 text-xs">
                          {item.retrieved.map((ref) => (
                            <li key={ref.join(':')} className={relevant.has(ref.join(':')) ? 'text-emerald-200' : 'text-slate-400'}>
                              {relevant.has(ref.join(':')) ? '✓ ' : '· '}{pageLabel(ref)}
                            </li>
                          ))}
                        </ol>
                      </td>
                      <td className="py-2"><StatusChip passed={item['hit@3'] === 1 && item.leakage === 0} label={item['hit@3'] === 1 ? 'Found' : 'Missed'} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Section>

        <div className="grid gap-6 lg:grid-cols-2">
          <Section title="Ingestion" subtitle="Same chunker, embedding text and vector metadata as production uploads.">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              {[
                ['Documents / pages', `${ingest.documents} / ${ingest.pages}`],
                ['Chunks', String(ingest.chunks)],
                ['Avg chunk size', `${Math.round(ingest.avg_chunk_chars)} chars`],
                ['Chunk size / overlap', `${ingest.chunk_size} / ${ingest.chunk_overlap}`],
                ['Embedding model', ingest.embedding_model],
                ['Dimension', String(ingest.embedding_dimension)],
                ['Embedding cost', `${ingest.embedding_ms_per_chunk} ms / chunk`],
              ].map(([term, detail]) => (
                <div key={term} className="contents">
                  <dt className="text-slate-400">{term}</dt>
                  <dd className="break-all text-slate-100">{detail}</dd>
                </div>
              ))}
            </dl>
          </Section>

          <Section title="Run history" subtitle="Newest first. Offline runs are not comparable with live runs.">
            <div className="max-h-64 overflow-auto">
              <table className="w-full text-sm tabular-nums">
                <thead className="text-left text-xs uppercase text-slate-400">
                  <tr><th className="py-2 pr-3">Run</th><th className="py-2 pr-3">Mode</th><th className="py-2 pr-3">MRR</th><th className="py-2 pr-3">Panel Hit@3</th><th className="py-2">Gates</th></tr>
                </thead>
                <tbody>
                  {history.map((run) => (
                    <tr key={`${run.run_id}-${run.mode}`} className="border-t border-slate-800">
                      <td className="py-2 pr-3 text-xs text-slate-300">{new Date(run.created_at).toLocaleString()}</td>
                      <td className="py-2 pr-3 text-xs">{run.mode}</td>
                      <td className="py-2 pr-3">{fmt(run.hybrid.mrr)}</td>
                      <td className="py-2 pr-3">{fmt(run.cross_document['cross_doc_hit@3'])}</td>
                      <td className="py-2"><StatusChip passed={Boolean(run.passed)} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </div>

        <Section title="Metric definitions">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            {Object.entries(METRIC_HELP).map(([term, description]) => (
              <div key={term}>
                <dt className="font-medium text-slate-100">{term}</dt>
                <dd className="text-slate-400">{description}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section
          title="System architecture"
          subtitle="Generated from the code and this eval report; metrics shown are from the run above."
          actions={(
            <a href="/architecture.svg" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-xs text-cyan-300 hover:text-cyan-200">
              Open full size <ExternalLink className="h-3.5 w-3.5" />
            </a>
          )}
        >
          <div className="overflow-x-auto rounded-xl bg-slate-950 p-2">
            <img src="/architecture.svg" alt="Architecture diagram of the AI PDF reader: React frontend, FastAPI backend, RAG pipeline, Supabase, NVIDIA and LLM services, annotated with eval metrics" className="min-w-[900px]" />
          </div>
          <p className="mt-2 flex items-center gap-1.5 text-xs text-slate-500">
            <Database className="h-3.5 w-3.5" /> Regenerated automatically on every eval run.
          </p>
        </Section>
      </main>
    </div>
  );
};

export default EvalsPage;
