import { useEffect, useRef, useState } from 'react';
import { VARIANT_COLORS, VARIANT_LABELS } from '../../lib/evalTheme';

const GRID = 'rgba(148, 163, 184, 0.18)';
const AXIS_TEXT = '#94a3b8';

const useWidth = <T extends HTMLElement>() => {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return [ref, width] as const;
};

type Tooltip = { x: number; y: number; title: string; lines: string[] } | null;

const TooltipBox = ({ tooltip }: { tooltip: Tooltip }) => (
  tooltip ? (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 min-w-[10rem] rounded-lg border border-slate-600 bg-slate-950/95 px-3 py-2 text-xs shadow-xl"
      style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, calc(-100% - 10px))' }}
    >
      <div className="font-medium text-white">{tooltip.title}</div>
      {tooltip.lines.map((line) => (
        <div key={line} className="text-slate-300">{line}</div>
      ))}
    </div>
  ) : null
);

export const Legend = ({ series }: { series: string[] }) => (
  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-300">
    {series.map((name) => (
      <span key={name} className="inline-flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-sm" style={{ background: VARIANT_COLORS[name] }} />
        {VARIANT_LABELS[name] ?? name}
      </span>
    ))}
  </div>
);

interface GroupedBarsProps {
  metrics: { key: string; label: string }[];
  series: string[];
  values: Record<string, Record<string, number>>; // series -> metric -> value in [0, 1]
}

/** Horizontal grouped bars on a single 0-1 axis; one band per metric. */
export const GroupedMetricBars = ({ metrics, series, values }: GroupedBarsProps) => {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tooltip, setTooltip] = useState<Tooltip>(null);
  const labelWidth = 118;
  const right = 44;
  const barHeight = 10;
  const barGap = 2; // surface gap between adjacent bars
  const bandPadding = 14;
  const bandHeight = series.length * (barHeight + barGap) - barGap + bandPadding;
  const top = 8;
  const plotWidth = width - labelWidth - right;
  const height = top + metrics.length * bandHeight + 24;
  const x = (value: number) => labelWidth + Math.max(0, Math.min(1, value)) * plotWidth;
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div ref={ref} className="relative w-full" onMouseLeave={() => setTooltip(null)}>
      <svg width={width} height={height} role="img" aria-label="Retrieval metric comparison by variant">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={top} y2={height - 22} stroke={GRID} />
            <text x={x(tick)} y={height - 6} fill={AXIS_TEXT} fontSize={11} textAnchor="middle">
              {tick.toFixed(2)}
            </text>
          </g>
        ))}
        {metrics.map((metric, metricIndex) => {
          const bandTop = top + metricIndex * bandHeight + bandPadding / 2;
          const best = Math.max(...series.map((name) => values[name]?.[metric.key] ?? 0));
          // Label one bar per row: the first to reach the best value (ties stay unlabelled).
          const labelledSeries = series.find((name) => (values[name]?.[metric.key] ?? 0) === best);
          return (
            <g key={metric.key}>
              <text
                x={labelWidth - 10}
                y={bandTop + (bandHeight - bandPadding) / 2 + 4}
                fill="#e2e8f0"
                fontSize={12}
                textAnchor="end"
              >
                {metric.label}
              </text>
              {series.map((name, seriesIndex) => {
                const value = values[name]?.[metric.key] ?? 0;
                const y = bandTop + seriesIndex * (barHeight + barGap);
                const barWidth = Math.max(0, x(value) - labelWidth);
                const radius = Math.min(4, barWidth / 2);
                const isBest = value === best;
                const showLabel = name === labelledSeries;
                return (
                  <g key={name}>
                    {/* Bar with 4px rounded data-end, square at the baseline. */}
                    <path
                      d={`M${labelWidth},${y} h${Math.max(0, barWidth - radius)} a${radius},${radius} 0 0 1 ${radius},${radius} v${barHeight - 2 * radius} a${radius},${radius} 0 0 1 ${-radius},${radius} h${-Math.max(0, barWidth - radius)} z`}
                      fill={VARIANT_COLORS[name]}
                    />
                    {showLabel && (
                      <text x={x(value) + 6} y={y + barHeight - 1} fill="#cbd5e1" fontSize={10}>
                        {value.toFixed(2)}
                      </text>
                    )}
                    {/* Hit target spans the full row, larger than the mark. */}
                    <rect
                      x={labelWidth}
                      y={y - barGap / 2}
                      width={plotWidth + right}
                      height={barHeight + barGap}
                      fill="transparent"
                      onMouseMove={() => setTooltip({
                        x: x(value),
                        y,
                        title: `${metric.label} · ${VARIANT_LABELS[name]}`,
                        lines: [`${value.toFixed(3)}${isBest ? ' (best)' : ''}`],
                      })}
                    />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      <TooltipBox tooltip={tooltip} />
    </div>
  );
};

interface LatencyBarsProps {
  series: string[];
  latency: Record<string, { p50: number; p95: number }>;
}

/** p50 as the bar, p95 as a whisker: one millisecond axis, never mixed with scores. */
export const LatencyBars = ({ series, latency }: LatencyBarsProps) => {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [tooltip, setTooltip] = useState<Tooltip>(null);
  const labelWidth = 170;
  const right = 70;
  const row = 30;
  const top = 6;
  const height = top + series.length * row + 24;
  const plotWidth = width - labelWidth - right;
  const maxValue = Math.max(1, ...series.map((name) => latency[name]?.p95 ?? 0));
  const step = maxValue > 400 ? 200 : maxValue > 100 ? 50 : 10;
  const axisMax = Math.ceil(maxValue / step) * step;
  const x = (value: number) => labelWidth + (value / axisMax) * plotWidth;
  const ticks = Array.from({ length: Math.floor(axisMax / step) + 1 }, (_, i) => i * step);

  return (
    <div ref={ref} className="relative w-full" onMouseLeave={() => setTooltip(null)}>
      <svg width={width} height={height} role="img" aria-label="Retrieval latency by variant">
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={x(tick)} x2={x(tick)} y1={top} y2={height - 22} stroke={GRID} />
            <text x={x(tick)} y={height - 6} fill={AXIS_TEXT} fontSize={11} textAnchor="middle">{tick} ms</text>
          </g>
        ))}
        {series.map((name, index) => {
          const { p50 = 0, p95 = 0 } = latency[name] ?? {};
          const y = top + index * row + 8;
          const barWidth = Math.max(0, x(p50) - labelWidth);
          const radius = Math.min(4, barWidth / 2);
          return (
            <g key={name}>
              <text x={labelWidth - 10} y={y + 9} fill="#e2e8f0" fontSize={12} textAnchor="end">
                {VARIANT_LABELS[name]}
              </text>
              <path
                d={`M${labelWidth},${y} h${Math.max(0, barWidth - radius)} a${radius},${radius} 0 0 1 ${radius},${radius} v${12 - 2 * radius} a${radius},${radius} 0 0 1 ${-radius},${radius} h${-Math.max(0, barWidth - radius)} z`}
                fill={VARIANT_COLORS[name]}
              />
              <line x1={x(p50)} x2={x(p95)} y1={y + 6} y2={y + 6} stroke="#cbd5e1" strokeWidth={2} />
              <line x1={x(p95)} x2={x(p95)} y1={y + 1} y2={y + 11} stroke="#cbd5e1" strokeWidth={2} />
              <text x={x(p95) + 6} y={y + 10} fill="#cbd5e1" fontSize={10}>p95 {Math.round(p95)}</text>
              <rect
                x={labelWidth}
                y={y - 6}
                width={plotWidth + right}
                height={row - 4}
                fill="transparent"
                onMouseMove={() => setTooltip({
                  x: x(p95),
                  y,
                  title: VARIANT_LABELS[name],
                  lines: [`p50 ${p50.toFixed(1)} ms`, `p95 ${p95.toFixed(1)} ms`],
                })}
              />
            </g>
          );
        })}
      </svg>
      <TooltipBox tooltip={tooltip} />
    </div>
  );
};
