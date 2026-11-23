import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  CheckCircle2,
  Database,
  ExternalLink,
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
  'nDCG@5': 'Ranking quality that rewards correct pages near the top, normalized to 1.0.',
  'Recall@5': 'Share of all correct pages found in the top 5.',
  'Answer-term recall':
    'Share of expected answer terms present in the top-3 retrieved text, a proxy for whether the LLM has the facts it needs.',
  Leakage: 'Share of side-panel results that come from the PDF that is already open. Must be 0.',
  'Off-topic':
    'Share of side-panel results from an unrelated subject (for example, cloud computing suggested for a biology page).',
};

const fmt = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined ? '—' : value.toFixed(digits);

const StatusChip = ({ passed, label }: { passed: boolean; label?: string }) => (
  <span
    className={`inline-flex items-center gap-phi-1 rounded-phi-sm border px-phi-2 py-phi-1 text-phi-xs font-medium ${
      passed
        ? 'border-semantic-positive/25 bg-semantic-positiveBg text-semantic-positive'
        : 'border-semantic-negative/25 bg-semantic-negativeBg text-semantic-negative'
    }`}
  >
    {passed ? (
      <CheckCircle2 className="h-3.5 w-3.5" strokeWidth={1.5} />
    ) : (
      <XCircle className="h-3.5 w-3.5" strokeWidth={1.5} />
    )}
    {label ?? (passed ? 'Pass' : 'Fail')}
  </span>
);

const StatTile = ({
  label,
  value,
  hint,
  accent = false,
}: {
  label: string;
  value: string;
  hint: string;
  accent?: boolean;
}) => (
  <div className="rounded-phi-lg border border-[rgba(25,24,22,0.09)] bg-app-surface p-phi-5 shadow-subtle">
    <div className="text-phi-xs text-ink-muted">{label}</div>
    <div
      className={`mt-phi-2 font-mono text-phi-lg font-medium leading-none tabular-nums ${
        accent ? 'text-accent-ink' : 'text-ink-primary'
      }`}
    >
      {value}
    </div>
    <div className="mt-phi-2 text-phi-xs text-ink-secondary">{hint}</div>
  </div>
);

const Section = ({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) => (
  <section className="rounded-phi-lg border border-[rgba(25,24,22,0.09)] bg-app-surface p-phi-5 shadow-subtle">
    <div className="mb-phi-5 flex flex-wrap items-start justify-between gap-phi-3">
      <div>
        <h2 className="text-phi-base font-medium text-ink-primary">{title}</h2>
        {subtitle && (
          <p className="mt-phi-1 max-w-phi-modal-lg text-phi-xs leading-phi text-ink-secondary">
            {subtitle}
          </p>
        )}
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
    className="btn-secondary h-phi-ctrl-sm gap-phi-2 px-phi-3 text-phi-xs"
  >
    {asTable ? (
      <BarChart3 className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
    ) : (
      <Table2 className="h-3.5 w-3.5 text-ink-muted" strokeWidth={1.5} />
    )}
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

  const docNames = useMemo(
    () =>
      Object.fromEntries(
        (report?.dataset.documents ?? []).map((doc) => [doc.id, doc.name.replace(/\.pdf$/i, '')])
      ),
    [report]
  );
  const pageLabel = ([doc, page]: PageRef) => `${docNames[doc] ?? doc} p.${page}`;

  const filteredQueries = useMemo(() => {
    if (!report) return [];
    return report.variants[queryVariant].queries.filter(
      (query) =>
        (queryCategory === 'all' || query.category === queryCategory) &&
        (!missesOnly || query['hit@1'] < 1)
    );
  }, [report, queryVariant, queryCategory, missesOnly]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-phi-2 bg-app-bg text-phi-sm text-ink-secondary">
        <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} /> Loading eval report
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-app-bg px-phi-5">
        <div className="w-full max-w-phi-modal-sm rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-app-surface p-phi-6 text-center shadow-card">
          <p className="font-serif text-phi-lg font-normal text-ink-primary">No eval report available</p>
          <p className="mt-phi-2 text-phi-sm text-ink-secondary">{error}</p>
          <pre className="mt-phi-5 overflow-x-auto rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-4 text-left font-mono text-phi-xs text-ink-primary">
            cd backend{'\n'}.venv/Scripts/python -m app.evals.harness
          </pre>
          <Link to="/library" className="btn-secondary mt-phi-5 h-phi-ctrl-sm text-phi-xs">
            Back to library
          </Link>
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
    RETRIEVAL_VARIANTS.map((name) => [
      name,
      { p50: variants[name].summary.latency_p50_ms, p95: variants[name].summary.latency_p95_ms },
    ])
  );
  const gateLabel = (gate: QualityGate) =>
    `${gate.variant.replace('_', ' ')} · ${gate.metric.replace('cross_doc_', '')}`;

  return (
    <div className="min-h-screen bg-app-bg text-ink-primary">
      <header className="sticky top-0 z-20 border-b border-[rgba(25,24,22,0.09)] bg-app-surface">
        <div className="mx-auto flex h-phi-bar max-w-phi-container flex-wrap items-center justify-between gap-phi-3 px-phi-4 sm:px-phi-5">
          <div className="flex items-center gap-phi-3">
            <Link
              to="/library"
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-md text-ink-secondary transition-colors duration-phi-fast hover:bg-app-raised hover:text-ink-primary"
              aria-label="Back to library"
            >
              <ArrowLeft className="h-4 w-4" strokeWidth={1.5} />
            </Link>
            <div>
              <h1 className="font-serif text-phi-md font-normal leading-none text-ink-primary">
                RAG evaluation
              </h1>
              <p className="mt-phi-1 font-mono text-phi-2xs tabular-nums text-ink-muted">
                Run {report.run_id} · {new Date(report.created_at).toLocaleString()}
                {report.git_commit ? ` · ${report.git_commit}` : ''}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-phi-3">
            <span className="rounded-phi-sm border border-[rgba(25,24,22,0.1)] bg-paper-50 px-phi-3 py-phi-1 font-mono text-phi-2xs text-ink-secondary">
              {report.mode === 'live' ? 'Live NVIDIA models' : 'Offline embedder'}
            </span>
            <StatusChip
              passed={report.passed}
              label={
                report.passed
                  ? 'All gates pass'
                  : `${gates.filter((g) => !g.passed).length} gate(s) failing`
              }
            />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-phi-container space-y-phi-5 px-phi-4 py-phi-6 sm:px-phi-5">
        {report.mode === 'offline' && (
          <p className="rounded-phi-md border border-semantic-warning/25 bg-semantic-warningBg px-phi-4 py-phi-3 text-phi-xs text-semantic-warning">
            This report used the deterministic offline embedder. It checks pipeline mechanics, not hosted model quality.
          </p>
        )}

        {/* Compact KPI Strip */}
        <div className="grid grid-cols-2 gap-phi-4 lg:grid-cols-5">
          <StatTile label="Hybrid MRR" value={fmt(hybrid.mrr)} hint="Rank of first correct page" accent />
          <StatTile
            label="Hybrid Hit@3"
            value={`${Math.round(hybrid['hit@3'] * 100)}%`}
            hint={`${hybrid.queries} labelled queries`}
          />
          <StatTile
            label="Side-panel Hit@3"
            value={`${Math.round(crossDoc['cross_doc_hit@3'] * 100)}%`}
            hint={`${crossDoc.cases} cross-PDF cases`}
          />
          <StatTile
            label="Side-panel leakage"
            value={`${Math.round(crossDoc.cross_doc_leakage * 100)}%`}
            hint="Open PDF shown as related"
          />
          <StatTile
            label="Hybrid p95"
            value={`${Math.round(hybrid.latency_p95_ms)} ms`}
            hint="Embedding + search"
          />
        </div>

        {/* Main Chart + Secondary Latency Block (61.8% / 38.2% golden split) */}
        <div className="grid gap-phi-5 lg:grid-cols-phi">
          <Section
            title="Retrieval quality by variant"
            subtitle={`${report.dataset.queries} queries over ${report.dataset.documents.length} PDFs, judged per page. Best value per row is labelled.`}
            actions={<ViewToggle asTable={scoresAsTable} onChange={setScoresAsTable} />}
          >
            <div className="mb-phi-4">
              <Legend series={[...RETRIEVAL_VARIANTS]} />
            </div>
            {scoresAsTable ? (
              <div className="overflow-x-auto">
                <table className="w-full text-phi-sm">
                  <thead className="border-b border-[rgba(25,24,22,0.09)] text-left text-phi-xs text-ink-muted">
                    <tr>
                      <th className="py-phi-2 pr-phi-4 font-medium">Metric</th>
                      {RETRIEVAL_VARIANTS.map((name) => (
                        <th key={name} className="py-phi-2 pr-phi-4 font-medium">
                          {VARIANT_LABELS[name]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[rgba(25,24,22,0.07)] font-mono text-phi-xs tabular-nums">
                    {SCORE_METRICS.map((metric) => (
                      <tr key={metric.key}>
                        <td className="py-phi-3 pr-phi-4 font-sans text-phi-sm text-ink-primary">
                          {metric.label}
                        </td>
                        {RETRIEVAL_VARIANTS.map((name) => (
                          <td key={name} className="py-phi-3 pr-phi-4 text-ink-secondary">
                            {fmt(scoreValues[name][metric.key], 3)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <GroupedMetricBars
                metrics={SCORE_METRICS}
                series={[...RETRIEVAL_VARIANTS]}
                values={scoreValues}
              />
            )}
            <p className="mt-phi-4 border-t border-[rgba(25,24,22,0.08)] pt-phi-3 text-phi-xs text-ink-muted">
              Reranker{' '}
              {variants.hybrid_rerank.reranker_applied
                ? `applied (${report.config.reranker_model})`
                : 'unavailable for this run; fell back to fused ranking'}
              . Hybrid fuses {report.config.fusion_weights.vector} × vector +{' '}
              {report.config.fusion_weights.keyword} × BM25.
            </p>
          </Section>

          <Section
            title="Retrieval latency"
            subtitle="Bar shows p50; whisker reaches p95 including query embedding."
            actions={<ViewToggle asTable={latencyAsTable} onChange={setLatencyAsTable} />}
          >
            {latencyAsTable ? (
              <table className="w-full text-phi-sm">
                <thead className="border-b border-[rgba(25,24,22,0.09)] text-left text-phi-xs text-ink-muted">
                  <tr>
                    <th className="py-phi-2 font-medium">Variant</th>
                    <th className="py-phi-2 font-medium">p50 (ms)</th>
                    <th className="py-phi-2 font-medium">p95 (ms)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(25,24,22,0.07)] font-mono text-phi-xs tabular-nums">
                  {RETRIEVAL_VARIANTS.map((name) => (
                    <tr key={name}>
                      <td className="py-phi-3 font-sans text-phi-sm text-ink-primary">
                        {VARIANT_LABELS[name]}
                      </td>
                      <td className="py-phi-3 text-ink-secondary">{fmt(latency[name].p50, 1)}</td>
                      <td className="py-phi-3 text-ink-secondary">{fmt(latency[name].p95, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <LatencyBars series={[...RETRIEVAL_VARIANTS]} latency={latency} />
            )}
          </Section>
        </div>

        {/* Quality Gates */}
        <Section
          title="Quality gates"
          subtitle="A run passes only when every gate holds across production retrieval paths."
        >
          <div className="overflow-x-auto">
            <table className="w-full text-phi-sm">
              <thead className="border-b border-[rgba(25,24,22,0.09)] text-left text-phi-xs text-ink-muted">
                <tr>
                  <th className="py-phi-2 pr-phi-4 font-medium">Gate</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">Target</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">Actual</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">Status</th>
                  <th className="py-phi-2 font-medium">Why it matters</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(25,24,22,0.07)]">
                {gates.map((gate) => (
                  <tr key={`${gate.variant}-${gate.metric}`} className="align-top">
                    <td className="py-phi-3 pr-phi-4 font-medium text-ink-primary">{gateLabel(gate)}</td>
                    <td className="py-phi-3 pr-phi-4 font-mono text-phi-xs tabular-nums text-ink-secondary">
                      {gate.op} {gate.threshold}
                    </td>
                    <td className="py-phi-3 pr-phi-4 font-mono text-phi-xs font-medium tabular-nums text-ink-primary">
                      {fmt(gate.value, gate.metric.includes('latency') ? 0 : 3)}
                    </td>
                    <td className="py-phi-3 pr-phi-4">
                      <StatusChip passed={gate.passed} />
                    </td>
                    <td className="py-phi-3 text-phi-xs text-ink-secondary">{gate.why}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* By Query Type */}
        <Section
          title="By query type (hybrid)"
          subtitle="Paraphrases have little word overlap with the source; keyword queries test exact terms and acronyms."
        >
          <div className="overflow-x-auto">
            <table className="w-full text-phi-sm">
              <thead className="border-b border-[rgba(25,24,22,0.09)] text-left text-phi-xs text-ink-muted">
                <tr>
                  <th className="py-phi-2 pr-phi-4 font-medium">Category</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">Queries</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">Hit@1</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">Hit@3</th>
                  <th className="py-phi-2 pr-phi-4 font-medium">MRR</th>
                  <th className="py-phi-2 font-medium">Answer-term recall</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(25,24,22,0.07)] font-mono text-phi-xs tabular-nums">
                {Object.entries(variants.hybrid.by_category).map(([category, summary]) => (
                  <tr key={category}>
                    <td className="py-phi-3 pr-phi-4 font-sans text-phi-sm capitalize text-ink-primary">
                      {category.replace('_', ' ')}
                    </td>
                    <td className="py-phi-3 pr-phi-4 text-ink-secondary">{summary.queries}</td>
                    <td className="py-phi-3 pr-phi-4 text-ink-secondary">{fmt(summary['hit@1'])}</td>
                    <td className="py-phi-3 pr-phi-4 text-ink-secondary">{fmt(summary['hit@3'])}</td>
                    <td className="py-phi-3 pr-phi-4 text-ink-secondary">{fmt(summary.mrr)}</td>
                    <td className="py-phi-3 text-ink-secondary">{fmt(summary.answer_term_recall)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>

        {/* Per-Query Results */}
        <Section
          title="Per-query results"
          subtitle="Correct pages are marked in green. Filter to misses only to inspect ranking errors."
          actions={
            <div className="flex flex-wrap items-center gap-phi-2 text-phi-xs">
              <select
                value={queryVariant}
                onChange={(event) => setQueryVariant(event.target.value as typeof queryVariant)}
                className="h-phi-ctrl-sm rounded-phi-sm border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-phi-xs text-ink-primary"
                aria-label="Variant"
              >
                {RETRIEVAL_VARIANTS.map((name) => (
                  <option key={name} value={name}>
                    {VARIANT_LABELS[name]}
                  </option>
                ))}
              </select>
              <select
                value={queryCategory}
                onChange={(event) => setQueryCategory(event.target.value)}
                className="h-phi-ctrl-sm rounded-phi-sm border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 text-phi-xs text-ink-primary"
                aria-label="Category"
              >
                <option value="all">All categories</option>
                {report.dataset.categories.map((category) => (
                  <option key={category} value={category}>
                    {category.replace('_', ' ')}
                  </option>
                ))}
              </select>
              <label className="inline-flex cursor-pointer items-center gap-phi-2 text-ink-secondary">
                <input
                  type="checkbox"
                  checked={missesOnly}
                  onChange={(event) => setMissesOnly(event.target.checked)}
                  className="h-3.5 w-3.5 rounded-phi-xs accent-accent"
                />
                Misses only
              </label>
            </div>
          }
        >
          <div className="mb-phi-3 flex items-center gap-phi-2 font-mono text-phi-xs tabular-nums text-ink-muted">
            <span
              className="h-2.5 w-2.5 rounded-[2px]"
              style={{ background: VARIANT_COLORS[queryVariant] }}
            />
            Showing {filteredQueries.length} of {variants[queryVariant].queries.length} queries
          </div>
          <div className="max-h-[28rem] overflow-auto scrollbar-thin">
            <table className="w-full text-phi-sm">
              <thead className="sticky top-0 border-b border-[rgba(25,24,22,0.09)] bg-app-surface text-left text-phi-xs text-ink-muted">
                <tr>
                  <th className="py-phi-2 pr-phi-3 font-medium">Query</th>
                  <th className="py-phi-2 pr-phi-3 font-medium">Retrieved (top 3)</th>
                  <th className="py-phi-2 pr-phi-3 font-medium">First hit</th>
                  <th className="py-phi-2 font-medium">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(25,24,22,0.07)]">
                {filteredQueries.map((query) => {
                  const relevant = new Set(query.relevant.map((ref) => ref.join(':')));
                  return (
                    <tr key={query.id} className="align-top">
                      <td className="py-phi-3 pr-phi-3">
                        <div className="text-ink-primary">{query.query}</div>
                        <div className="mt-phi-1 font-mono text-phi-2xs text-ink-muted">
                          {query.id} · {query.category.replace('_', ' ')}
                        </div>
                      </td>
                      <td className="py-phi-3 pr-phi-3">
                        <ol className="space-y-phi-1 font-mono text-phi-xs">
                          {query.retrieved.slice(0, 3).map((ref) => {
                            const hit = relevant.has(ref.join(':'));
                            return (
                              <li
                                key={ref.join(':')}
                                className={hit ? 'font-medium text-semantic-positive' : 'text-ink-muted'}
                              >
                                {hit ? '✓ ' : '· '}
                                {pageLabel(ref)}
                              </li>
                            );
                          })}
                        </ol>
                      </td>
                      <td className="py-phi-3 pr-phi-3 font-mono text-phi-xs tabular-nums">
                        {query.mrr > 0 ? (
                          <span
                            className={
                              query.mrr === 1
                                ? 'font-medium text-semantic-positive'
                                : 'text-semantic-warning'
                            }
                          >
                            #{Math.round(1 / query.mrr)}
                          </span>
                        ) : (
                          <span className="text-semantic-negative">
                            Not in top {report.config.top_k}
                          </span>
                        )}
                      </td>
                      <td className="py-phi-3 font-mono text-phi-xs tabular-nums text-ink-muted">
                        {Math.round(query.latency_ms)} ms
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Section>

        {/* Side Panel Cross-Doc Evaluation */}
        <Section
          title="Side panel: related content from other PDFs"
          subtitle={`Mirrors /api/recommendations: open page text is the query, open PDF is excluded, matches below ${fmt(
            crossDoc.min_score
          )} are hidden, up to 3 shown. Off-topic: ${Math.round(
            crossDoc.cross_doc_off_topic * 100
          )}% · average shown: ${fmt(crossDoc.cross_doc_avg_shown, 1)}.`}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-phi-sm">
              <thead className="border-b border-[rgba(25,24,22,0.09)] text-left text-phi-xs text-ink-muted">
                <tr>
                  <th className="py-phi-2 pr-phi-3 font-medium">Open page</th>
                  <th className="py-phi-2 pr-phi-3 font-medium">Expected</th>
                  <th className="py-phi-2 pr-phi-3 font-medium">Shown in panel</th>
                  <th className="py-phi-2 font-medium">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(25,24,22,0.07)]">
                {variants.cross_document.cases.map((item) => {
                  const relevant = new Set(item.relevant.map((ref) => ref.join(':')));
                  return (
                    <tr key={item.id} className="align-top">
                      <td className="py-phi-3 pr-phi-3 font-mono text-phi-xs text-ink-primary">
                        {pageLabel(item.source)}
                      </td>
                      <td className="py-phi-3 pr-phi-3 font-mono text-phi-xs text-ink-secondary">
                        {item.relevant.map(pageLabel).join(', ')}
                      </td>
                      <td className="py-phi-3 pr-phi-3">
                        <ol className="space-y-phi-1 font-mono text-phi-xs">
                          {item.retrieved.map((ref) => (
                            <li
                              key={ref.join(':')}
                              className={
                                relevant.has(ref.join(':'))
                                  ? 'font-medium text-semantic-positive'
                                  : 'text-ink-muted'
                              }
                            >
                              {relevant.has(ref.join(':')) ? '✓ ' : '· '}
                              {pageLabel(ref)}
                            </li>
                          ))}
                        </ol>
                      </td>
                      <td className="py-phi-3">
                        <StatusChip
                          passed={item['hit@3'] === 1 && item.leakage === 0}
                          label={item['hit@3'] === 1 ? 'Found' : 'Missed'}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Section>

        {/* Ingestion & History */}
        <div className="grid gap-phi-5 lg:grid-cols-2">
          <Section
            title="Ingestion"
            subtitle="Same chunker, embedding text, and vector metadata as production uploads."
          >
            <dl className="divide-y divide-[rgba(25,24,22,0.07)] text-phi-sm">
              {[
                ['Documents / pages', `${ingest.documents} / ${ingest.pages}`],
                ['Chunks', String(ingest.chunks)],
                ['Avg chunk size', `${Math.round(ingest.avg_chunk_chars)} chars`],
                ['Chunk size / overlap', `${ingest.chunk_size} / ${ingest.chunk_overlap}`],
                ['Embedding model', ingest.embedding_model],
                ['Dimension', String(ingest.embedding_dimension)],
                ['Embedding cost', `${ingest.embedding_ms_per_chunk} ms / chunk`],
              ].map(([term, detail]) => (
                <div key={term} className="flex items-baseline justify-between gap-phi-4 py-phi-2">
                  <dt className="text-phi-xs text-ink-muted">{term}</dt>
                  <dd className="break-all text-right font-mono text-phi-xs tabular-nums text-ink-primary">
                    {detail}
                  </dd>
                </div>
              ))}
            </dl>
          </Section>

          <Section
            title="Run history"
            subtitle="Newest first. Offline runs are not comparable with live runs."
          >
            <div className="max-h-64 overflow-auto scrollbar-thin">
              <table className="w-full text-phi-sm">
                <thead className="border-b border-[rgba(25,24,22,0.09)] text-left text-phi-xs text-ink-muted">
                  <tr>
                    <th className="py-phi-2 pr-phi-3 font-medium">Run</th>
                    <th className="py-phi-2 pr-phi-3 font-medium">Mode</th>
                    <th className="py-phi-2 pr-phi-3 font-medium">MRR</th>
                    <th className="py-phi-2 pr-phi-3 font-medium">Panel Hit@3</th>
                    <th className="py-phi-2 font-medium">Gates</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[rgba(25,24,22,0.07)] font-mono text-phi-xs tabular-nums">
                  {history.map((run) => (
                    <tr key={`${run.run_id}-${run.mode}`}>
                      <td className="py-phi-3 pr-phi-3 text-ink-secondary">
                        {new Date(run.created_at).toLocaleString()}
                      </td>
                      <td className="py-phi-3 pr-phi-3 text-ink-secondary">{run.mode}</td>
                      <td className="py-phi-3 pr-phi-3 text-ink-primary">{fmt(run.hybrid.mrr)}</td>
                      <td className="py-phi-3 pr-phi-3 text-ink-primary">
                        {fmt(run.cross_document['cross_doc_hit@3'])}
                      </td>
                      <td className="py-phi-3">
                        <StatusChip passed={Boolean(run.passed)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>
        </div>

        {/* Metric Definitions */}
        <Section title="Metric definitions">
          <dl className="grid gap-phi-4 text-phi-sm sm:grid-cols-2">
            {Object.entries(METRIC_HELP).map(([term, description]) => (
              <div key={term} className="border-l-2 border-[rgba(25,24,22,0.1)] pl-phi-3">
                <dt className="text-phi-xs font-medium text-ink-primary">{term}</dt>
                <dd className="mt-phi-1 text-phi-xs leading-phi text-ink-secondary">{description}</dd>
              </div>
            ))}
          </dl>
        </Section>

        {/* System Architecture */}
        <Section
          title="System architecture"
          subtitle="Generated from the codebase and latest evaluation run."
          actions={
            <a
              href="/architecture.svg"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-phi-2 text-phi-xs font-medium text-accent-ink hover:underline"
            >
              Open full size <ExternalLink className="h-3.5 w-3.5" strokeWidth={1.5} />
            </a>
          }
        >
          <div className="overflow-x-auto rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-[#141415] p-phi-3">
            <img
              src="/architecture.svg"
              alt="Architecture diagram of Document Intelligence Studio: React frontend, FastAPI backend, RAG pipeline, Supabase, NVIDIA and LLM services, annotated with eval metrics"
              className="min-w-[900px]"
            />
          </div>
          <p className="mt-phi-3 flex items-center gap-phi-2 text-phi-xs text-ink-muted">
            <Database className="h-3.5 w-3.5" strokeWidth={1.5} /> Regenerated automatically on every eval run.
          </p>
        </Section>
      </main>
    </div>
  );
};

export default EvalsPage;
